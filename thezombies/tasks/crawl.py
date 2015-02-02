from __future__ import absolute_import
from django.db import transaction, DatabaseError
from django_atomic_celery import task

from contextlib import closing

try:
    import simplejson as json
except ImportError:
    import json

from .validation import get_schema_prefix, ijson
from .urls import inspect_url, remove_url_fragments, open_streaming_response
from .utils import logger, ResultDict, COUNTDOWN_MODULO
from thezombies.models import (Probe, Audit)


@task
def inspect_catalog_dataset(taskarg):
    """Inspect a dataset (json object) from a data catalog (json array) and
    check any included accessURLs, distributions or webServices

    :param taskarg: Dictionary containing the json object to inspect,
                    an audit id, agency_id and catalog_url
    """

    def make_task(field, dataset, orig_task):
        url = dataset.get(field, None)
        if url:
            task_dict = ResultDict(orig_task)
            task_dict['url'] = remove_url_fragments(url)
            task_dict['url_type'] = field
            return task_dict
        return None

    def taskargs_from_dataset(dataset, url_fields, taskarg, dataset_name='dataset'):
        """Look at under particular keys in a dataset object for URLs to examine"""
        tasks = []
        collected_urls = set()
        for field in url_fields:
            if field in dataset:
                task_dict = make_task(field, dataset, taskarg)
                if task_dict:
                    url = task_dict.get('url', None)
                    if url not in collected_urls:
                        collected_urls.add(url)
                        tasks.append(task_dict)
                else:
                    logger.error('Unable to make a task dictionary to pass to inspect_url')
            else:
                logger.info("No '{0}' in {1}.".format(field, dataset_name))
        return tasks

    def remove_duplicate_url_tasks(url_tasks, url_set):
        """Reduce a set of url_tasks so there is only one task per url in url_set"""
        unique_tasks = []
        for taskarg in url_tasks:
            urlarg = taskarg.get('url', None)
            if urlarg in url_set:
                unique_tasks.append(taskarg)
                url_set.discard(urlarg)
            if len(url_set) == 0:
                break
        return unique_tasks

    dataset = taskarg.pop('dataset', None)  # Pop dataset since we store it in JSON Probe
    audit_id = taskarg.get('audit_id', None)
    # Create JSON probe and store dataset in probe.initial
    probe = None
    try:
        with transaction.atomic():
            probe = Probe.objects.create(probe_type=Probe.JSON_PROBE, initial=dataset,
                                         previous_id=taskarg.get('prev_probe_id', None), audit_id=audit_id)
            taskarg['prev_probe_id'] = probe.id
    except DatabaseError as e:
        logger.exception(e)

    dataset_title = dataset.get('title', 'No title provided.')
    all_task_args = []
    if dataset and isinstance(dataset, dict):
        # Look for relevant URLs on top-level of object
        url_fields = ('accessURL', 'webService', 'accessUrl')
        all_task_args.extend(taskargs_from_dataset(dataset, url_fields, taskarg))
        # Look for relevant URLs in optional 'distribution' subobject
        if 'distribution' in dataset:
            distribution = dataset.get('distribution', None)
            if distribution:
                # Sometimes the distribution value is a JSON string (hasn't been reconstituted)
                if not isinstance(distribution, list):
                    logger.warn('distribution value not a list, attempting to reconstitute')
                    distribution = json.loads(distribution)
                for d in distribution:
                    logger.info('Checking distribution list')
                    if isinstance(d, dict):
                        all_task_args.extend(taskargs_from_dataset(d, url_fields, taskarg, 'd'))
                    else:
                        logger.warn('distribution item in dataset appears to be a "{0}", not a dictionary'.format(type(d)))
            else:
                logger.warn('No distribution in dataset')
        # If we've made a list of task args, we can spin off unique tasks to inspect those URLs
        if all_task_args:
            # Make a set of the distinct URLS (there can be repeats)
            unique_urls = set([x.get('url') for x in all_task_args if x and x.get('url', False)])
            unique_tasks = remove_duplicate_url_tasks(all_task_args, unique_urls.copy())
            # Add some stats to our probe
            probe.result['urls'] = list(unique_urls)
            probe.result['total_url_count'] = len(all_task_args)
            probe.result['unique_url_count'] = len(unique_urls)
            # Set up and run a group of chunks of inspect_url tasks
            wrapped_args_tasks = [(t,) for t in unique_tasks]
            dataset_url_taskgrp = inspect_url.chunks(wrapped_args_tasks, 4).group()
            dataset_url_taskgrp.skew(start=1, stop=10)()
        else:
            error_message = "No urls found for catalog dataset titled '{0}'".format(dataset_title)
            logger.warning(error_message)
            if audit_id:
                with transaction.atomic():
                    audit = Audit.objects.get(id=audit_id)
                    audit.messages.append(error_message)
                    audit.save()
            probe.errors.append(error_message)

        # Save the probe at the end
        with transaction.atomic():
            probe.save()

    else:
        logger.warn('No valid dataset passed to inspect_catalog_dataset')


@task
def crawl_agency_catalog(agency_id, catalog_url, schema='DATASET_1.0'):
    """Create an audit to track the crawl of a data catalog url and
    spawns tasks to inspect individual objects in the catalog

    :param agency_id: Database id of the agency whose catalog should be searched
    :param catalog_url: The url of the catalog to search. Generally accessible on agency.data_json_url
    """

    returnval = ResultDict({'agency_id': agency_id, 'catalog_url': catalog_url, 'schema': schema})
    audit = probe = tasks = None
    dataset_path = get_schema_prefix(schema)
    try:
        with transaction.atomic():
            audit = Audit.objects.create(agency_id=agency_id, audit_type=Audit.DATA_CATALOG_CRAWL)
            returnval['audit_id'] = audit.id

    except DatabaseError as e:
        logger.exception(e)

    if not dataset_path:
        logger.warn('Unable to load dataset_path for {0}'.format(schema))

    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.GENERIC_PROBE,
                                     initial={'agency_id': agency_id,
                                              'catalog_url': catalog_url},
                                     audit_id=returnval.get('audit_id', None))
        returnval['prev_probe_id'] = probe.id

    try:
        with closing(open_streaming_response('GET', catalog_url)) as resp:
            # Use the schema dataset_prefix to get an iterator for the items to be validated.
            logger.info('Streaming {url} for schema {schema}'.format(url=catalog_url, schema=schema))
            objects = ijson.items(resp.raw, dataset_path or '')

            default_args = {'agency_id': agency_id,
                            'audit_id': returnval.get('audit_id', None),
                            'catalog_url': catalog_url,
                            'prev_probe_id': returnval.get('prev_probe_id', None)}

            # Iterate over object stream to spawn inspection tasks
            tasks = []
            for num, obj in enumerate(objects):
                args = default_args.copy()
                args['dataset'] = obj
                logger.info('Searching dataset #{num} in  `{url}` for URLS'.format(url=catalog_url, num=num))
                task = inspect_catalog_dataset.apply_async(args=(args,), countdown=(num % COUNTDOWN_MODULO))
                tasks.append(task)

    except Exception as e:
        logger.exception(e)

    return tasks

from __future__ import absolute_import
from itertools import islice
from django.conf import settings
from django.db import transaction, DatabaseError
from django_atomic_celery import task
import ujson
from jsonschema import Draft4Validator

from .urls import request_url, get_or_create_inspection
from .json import parse_json, json
from .utils import logger, ResultDict
from thezombies.models import (Probe, Audit, URLInspection)

SCHEMA_ERROR_LIMIT = 100
SCHEMA_PATH = getattr(settings, 'DATA_CATALOG_SCHEMA_PATH', None)
CATALOG_SCHEMA = ujson.load(open(SCHEMA_PATH, 'r')) if SCHEMA_PATH else None

catalog_validator = Draft4Validator(CATALOG_SCHEMA)


@task
def inspect_data_catalog_item_url(taskarg):
    """Task to check an accessURL from a data catalog,
    using a HEAD request. Tracks and returns errors.

    :param taskarg: A dictionary containing a url, and optionally a audit_id
    """
    returnval = ResultDict(taskarg)
    url = taskarg.get('url', None)
    url_type = taskarg.get('url_type', None)
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('prev_probe_id', None)
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.URL_PROBE,
                                     initial={'url': url, 'url_type': url_type},
                                     previous_id=prev_probe_id, audit_id=audit_id)
    if url:
        result = request_url(url, 'HEAD')
        response = result.pop('response', None)
        returnval.errors.extend(result.errors)
        probe.errors.extend(result.errors)
        with transaction.atomic():
            if response is not None:
                inspection = URLInspection.objects.create_from_response(response, save_content=False)
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.probe = probe
                inspection.save()
                returnval['inspection_id'] = inspection.id
            else:
                timeout = result.get('timeout', False)
                probe.result['timeout'] = timeout
                inspection = URLInspection.objects.create(requested_url=url, timeout=timeout)
                inspection.probe = probe
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.save()
                returnval['inspection_id'] = inspection.id
            probe.result.update(result)
            probe.result['initial_url'] = url
            probe.result['inspection_id'] = returnval['inspection_id']
            probe.save()

    return returnval


@task
def validate_json_catalog(taskarg):
    """
    Validate json data against the DATA_CATALOG_SCHEMA
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('probe_id', None)
    inspection_id = taskarg.get('inspection_id', None)
    probe = None
    returnval = ResultDict(taskarg)
    if audit_id:
        logger.info('Validating JSON catalog for audit {0}'.format(audit_id))
    else:
        logger.warning(u'validate_json_catalog running without an audit_id')
    prev_probe = None
    try:
        with transaction.atomic():
            prev_probe = Probe.objects.get(id=prev_probe_id)
    except DatabaseError as e:
        returnval.add_error(e)
        returnval['success'] = False
        logger.error('Error fetching previous JSON probe in validate_json_catalog')

    if prev_probe:
        try:
            with transaction.atomic():
                probe = Probe.objects.create(probe_type=Probe.VALIDATION_PROBE,
                                             initial={'inspection_id': inspection_id},
                                             previous_id=prev_probe_id, audit_id=audit_id)
        except DatabaseError as e:
            returnval.add_error(e)
            logger.error('Error creating JSON probe in validate_json_catalog')
        if probe:
            returnval['probe_id'] = probe.id
        is_valid = False
        jsondata = prev_probe.result.get('json', None)
        if jsondata and CATALOG_SCHEMA:
            is_valid = catalog_validator.is_valid(jsondata)
            if not is_valid:
                # Save up to SCHEMA_ERROR_LIMIT errors from schema validation
                error_iter = islice(catalog_validator.iter_errors(jsondata), SCHEMA_ERROR_LIMIT)
                for e in error_iter:
                    returnval.add_error(e)
        probe.result['is_valid_data_catalog'] = is_valid
        with transaction.atomic():
            probe.errors.extend(returnval.errors)
            probe.save()
            logger.info('Updated JSON probe in validate_json_catalog')

        returnval['audit_type'] = Audit.DATA_CATALOG_VALIDATION
    return returnval


@task
def inspect_data_catalog_item(taskarg):
    """Inspect an item (json object) in a data catalog (json array) and
    check any included accessURLs, distributions or webServices

    :param taskarg: Dictionary containing the json object to inspect,
                    an audit id, agency_id and catalog_url
    """

    def make_task(field, item, orig_task):
        url = item.get(field, None)
        if url:
            task_dict = ResultDict(orig_task)
            task_dict['url'] = url
            task_dict['url_type'] = field
            return task_dict
        return None

    def taskargs_from_item(item, url_fields, taskarg, item_name='item'):
        tasks = []
        collected_urls = set()
        for field in url_fields:
            if field in item:
                task_dict = make_task(field, item, taskarg)
                if task_dict:
                    url = task_dict.get('url', None)
                    if url not in collected_urls:
                        collected_urls.add(url)
                        tasks.append(task_dict)
                else:
                    logger.error('Unable to make a task dictionary to pass to inspect_data_catalog_item_url')
            else:
                logger.info("No '{0}' in {1}.".format(field, item_name))
        return tasks

    item = taskarg.get('item', None)
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('prev_probe_id', None)
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.JSON_PROBE, initial=item,
                                     previous_id=prev_probe_id, audit_id=audit_id)
    taskarg['prev_probe_id'] = probe.id
    item_title = item.get('title', 'No title provided.')
    all_task_args = []
    if item and isinstance(item, dict):
        url_fields = ('accessURL', 'webService', 'accessUrl')
        all_task_args.extend(taskargs_from_item(item, url_fields, taskarg))
        if 'distribution' in item:
            distribution = item.get('distribution', None)
            if distribution:
                if not isinstance(distribution, list):
                    distribution = json.loads(distribution)
                for d in distribution:
                    logger.info('Checking distribution list')
                    if isinstance(d, dict):
                        all_task_args.extend(taskargs_from_item(d, url_fields, taskarg, 'd'))
                    else:
                        logger.warn('distribution item is a "{0}", not a dictionary'.format(type(d)))
            else:
                logger.warn('No distribution in item')
        if len(all_task_args) > 0:
            unique_urls = set([x.get('url') for x in all_task_args if x and x.get('url', False)])
            probe.result['urls'] = list(unique_urls)
            unique_tasks = []
            for taskarg in all_task_args:
                urlarg = taskarg.get('url', None)
                if urlarg in unique_urls:
                    unique_tasks.append(taskarg)
                    unique_urls.discard(urlarg)
                if len(unique_urls) == 0:
                    break
            probe.result['total_url_count'] = len(all_task_args)
            probe.result['unique_url_count'] = len(unique_urls)
            wrapped_args_tasks = [(t,) for t in unique_tasks]
            item_url_grp = inspect_data_catalog_item_url.chunks(wrapped_args_tasks, 4).group()
            item_url_grp.skew(start=1, stop=10)()
        else:
            with transaction.atomic():
                error_message = "No urls found for catalog item titled '{0}'".format(item_title)
                if audit_id:
                    audit = Audit.objects.get(id=audit_id)
                    audit.messages.append(error_message)
                    audit.save()
            probe.errors.append(error_message)
        with transaction.atomic():
            probe.save()

    else:
        logger.warn('No valid item passed to inspect_data_catalog_item')


@task
def create_data_crawl_audit(agency_id, catalog_url):
    """Create an audit to track the crawl of a data catalog url and
    spawns tasks to inspect individual objects in the catalog

    :param agency_id: Database id of the agency whose catalog should be searched
    :param catalog_url: The url of the catalog to search. Generally accessible on agency.data_json_url
    """
    fetcher = get_or_create_inspection(catalog_url, with_content=True)
    inspection_id = fetcher.get('inspection_id')
    inspection = URLInspection.objects.get(id=inspection_id)
    parse_args = {'content': inspection.content.string()}
    parse_args['encoding'] = inspection.encoding if inspection.encoding else inspection.apparent_encoding
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.GENERIC_PROBE,
                                     initial={'agency_id': agency_id,
                                              'catalog_url': catalog_url,
                                              'inspection_id': inspection_id})
    prev_probe_id = probe.id
    result_dict = parse_json(parse_args)
    jsondata = result_dict.get('json', None)
    parse_errors = result_dict.get('parse_errors', False)
    errors = result_dict.get('errors', [])
    returnval = ResultDict({'agency_id': agency_id, 'catalog_url': catalog_url, 'prev_probe_id': prev_probe_id})
    audit_id = None
    with transaction.atomic():
        audit = Audit.objects.create(agency_id=agency_id, audit_type=Audit.DATA_CATALOG_CRAWL)
        audit_id = audit.id
        probe.audit = audit
        probe.errors.extend(errors)
        probe.result['json_errors'] = True if parse_errors else False
        probe.result['is_json'] = True if jsondata else False
        if jsondata:
            catalog_length = len(jsondata)
            audit.messages.append("Data catalog contains {0} items".format(catalog_length))
            probe.result['catalog_length'] = catalog_length
        else:
            probe.errors.append("No valid json at '{0}'".format(catalog_url))
        audit.save()
        probe.save()
    returnval['audit_id'] = audit_id
    if jsondata:
        wrapped_args_tasks = []
        for item in jsondata:
            taskarg = {'agency_id': agency_id, 'audit_id': audit_id,
                       'catalog_url': catalog_url, 'item': item,
                       'prev_probe_id': prev_probe_id}
            wrapped_args_tasks.append((taskarg,))
        taskgroup = inspect_data_catalog_item.chunks(wrapped_args_tasks, 4).group()
        taskgroup.skew(start=1, stop=10)()
    else:
        # Audit some error or something
        with transaction.atomic():
            audit.messages.append("Unable to load json data from '{0}'. Cannot find urls for datasets")
    return returnval

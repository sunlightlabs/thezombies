from __future__ import absolute_import
from itertools import islice
from django.conf import settings
from django.db import transaction
from celery import shared_task
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


@shared_task(ignore_result=True, rate_limit='10/s')
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
        response = result.get('response', None)
        returnval.errors.extend(result.errors)
        probe.errors.extend(result.errors)
        if response is not None:
            with transaction.atomic():
                inspection = URLInspection.objects.create_from_response(response, save_content=False)
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.probe = probe
                inspection.save()
                probe.save()
                returnval['inspection_id'] = inspection.id
        else:
            with transaction.atomic():
                inspection = URLInspection.objects.create(requested_url=url)
                inspection.probe = probe
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.save()
                probe.save()
                returnval['inspection_id'] = inspection.id

    return returnval


@shared_task
def validate_json_catalog(taskarg):
    """
    Validate jsondata against the DATA_CATALOG_SCHEMA
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('probe_id', None)
    inspection_id = taskarg.get('inspection_id', None)
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.VALIDATION_PROBE,
                                     initial={'inspection_id': inspection_id},
                                     previous_id=prev_probe_id, audit_id=audit_id)
    returnval = ResultDict(taskarg)
    if probe:
        returnval['probe_id'] = probe.id
    is_valid = False
    jsondata = taskarg.get('json', None)
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
    returnval['audit_type'] = Audit.DATA_CATALOG_VALIDATION
    return returnval


@shared_task
def inspect_data_catalog_item(taskarg):
    """Inspect an item (json object) in a data catalog (json array) and
    check any included accessURLs, distributions or webServices

    :param taskarg: Dictionary containing the json object to inspect,
                    an audit id, agency_id and catalog_url
    """
    # I don't think tasks work properly in an inner function...
    def make_task(field, item, orig_task):
        url = item.get(field, None)
        if url:
            task_dict = ResultDict(orig_task)
            task_dict['url'] = url
            task_dict['url_type'] = field
            return task_dict
        return None

    def find_tasks(item, url_fields, taskarg, item_name='item'):
        tasks = []
        for field in url_fields:
            if field in item:
                task_dict = make_task(field, item, taskarg)
                if task_dict:
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
    tasks_args = []
    if item and isinstance(item, dict):
        url_fields = ('accessURL', 'webService')
        tasks_args.extend(find_tasks(item, url_fields, taskarg))
        if 'distribution' in item:
            distribution = item.get('distribution', None)
            if distribution:
                if not isinstance(distribution, list):
                    distribution = json.loads(distribution)
                for d in distribution:
                    logger.info('Checking distribution list')
                    if isinstance(d, dict):
                        tasks_args.extend(find_tasks(d, url_fields, taskarg, 'd'))
                    else:
                        logger.warn('distribution item is a "{0}", not a dictionary'.format(type(d)))
            else:
                logger.warn('No distribution in item')
        num_tasks = len(tasks_args)
        probe.result['tasks_generated'] = num_tasks
        if num_tasks > 0:
            tasks_urls = [x.get('url') for x in tasks_args if x and x.get('url', False)]
            probe.result['tasks'] = tasks_urls
            wrapped_args_tasks = [(t,) for t in tasks_args]
            item_url_grp = inspect_data_catalog_item_url.chunks(wrapped_args_tasks, 4).group()
            item_url_grp.skew(start=1, stop=10)()
            # for t in tasks_args:
            #     inspect_data_catalog_item_url.delay(t, {'countdown': 1})
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


@shared_task
def create_data_crawl_audit(agency_id, catalog_url):
    """Create an audit to track the crawl of a data catalog url and
    spawns tasks to inspect individual objects in the catalog

    :param agency_id: Database id of the agency whose catalog should be searched
    :param catalog_url: The url of the catalog to search. Generally accessible on agency.data_json_url
    """
    fetcher = get_or_create_inspection(catalog_url)
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
    returnval = ResultDict({'agency_id': agency_id, 'catalog_url': catalog_url, 'prev_probe_id': prev_probe_id})
    audit_id = None
    with transaction.atomic():
        audit = Audit.objects.create(agency_id=agency_id, audit_type=Audit.DATA_CATALOG_CRAWL)
        audit_id = audit.id
        probe.audit = audit
        if jsondata:
            catalog_length = len(jsondata)
            audit.messages.append("Data catalog contains {0} items".format(catalog_length))
            audit.save()
            probe.result['catalog_length'] = catalog_length
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

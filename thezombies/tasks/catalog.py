from __future__ import absolute_import
from itertools import islice
from django.conf import settings
from django.db import transaction
from celery import shared_task
import ujson
from jsonschema import Draft4Validator

from .urls import request_url, get_or_create_inspection
from .json import parse_json
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
    urlType = taskarg.get('urlType', None)
    item_info = taskarg.get('item_info', {})
    if urlType:
        item_info['urlType'] = urlType
    logger.info(item_info)
    audit_id = taskarg.get('audit_id', None)
    if url:
        result = request_url(url, 'HEAD')
        response = result.get('response', None)
        returnval.errors.extend(result.errors)
        if response is not None:
            with transaction.atomic():
                resp_obj = URLInspection.objects.create_from_response(response, save_content=False)
                resp_obj.info.update(item_info)
                resp_obj.errors = result.errors
                if audit_id:
                    resp_obj.audit_id = audit_id
                resp_obj.save()
                returnval['inspection_id'] = resp_obj.id
        else:
            with transaction.atomic():
                resp_obj = URLInspection.objects.create(requested_url=url, errors=result.errors, info=item_info)
                if audit_id:
                    resp_obj.audit_id = audit_id
                resp_obj.save()
                returnval['inspection_id'] = resp_obj.id

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
    prev_probe = Probe.objects.get(id=prev_probe_id)
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.VALIDATION_PROBE,
                                     initial={'inspection_id': inspection_id},
                                     previous_id=prev_probe_id, audit_id=audit_id)
    returnval = ResultDict(taskarg)
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
            task_dict['urlType'] = field
            return task_dict
        return None

    def find_tasks(item, url_fields, taskarg):
        tasks = []
        for field in url_fields:
            if field in item:
                    task_dict = make_task(field, item, taskarg)
                    if task_dict:
                        tasks.append(task_dict)
                    else:
                        logger.error('Unable to make a task dictionary to pass to inspect_data_catalog_item_url')
            else:
                logger.warn("No '{0}' in item.".format(field))
        return tasks

    item = taskarg.get('item', None)
    audit_id = taskarg.get('audit_id', None)
    meta_fields = ('title', 'accessLevel', 'publisher', 'modified')
    taskarg['item_info'] = {key: item.get(key, None) for key in meta_fields}
    item_title = item.get('title', 'No title provided.')
    task_args = []
    if item:
        url_fields = ('accessURL', 'webService')
        task_args.extend(find_tasks(item, url_fields, taskarg))
        if 'distribution' in item:
            distribution = item.get('distribution', None)
            if distribution:
                for d in distribution:
                    logger.info('Checking distribution list')
                    task_args.extend(find_tasks(d, url_fields, taskarg))
            else:
                logger.warn('No distribution in item')

        if len(task_args) > 0:
            for t in task_args:
                inspect_data_catalog_item_url.delay(t)
        else:
            if audit_id:
                with transaction.atomic():
                    audit = Audit.objects.get(id=audit_id)
                    audit.messages.append("No urls found for catalog item titled '{0}'".format(item_title))
                    audit.save()
    else:
        logger.warn('No item passed to inspect_data_catalog_item')


@shared_task
def create_data_crawl_audit(agency_id, catalog_url):
    """Create a audit to track the crawl of a data catalog url and
    spawns tasks to inspect individual objects in the catalog

    :param agency_id: Database id of the agency whose catalog should be searched
    :param catalog_url: The url of the catalog to search. Generally accessible on agency.data_json_url
    """
    fetcher = get_or_create_inspection(catalog_url)
    inspection_id = fetcher.get('inspection_id')
    inspection = URLInspection.objects.get(id=inspection_id)

    parse_args = {'content': inspection.content.string()}
    parse_args['encoding'] = inspection.encoding if inspection.encoding else inspection.apparent_encoding
    result_dict = parse_json(parse_args)
    jsondata = result_dict.get('json', None)
    returnval = ResultDict({'agency_id': agency_id, 'catalog_url': catalog_url})
    audit_id = None
    with transaction.atomic():
        audit = Audit.objects.create(agency_id=agency_id, audit_type=Audit.DATA_CATALOG_CRAWL)
        audit_id = audit.id
        if jsondata:
            catalog_length = len(jsondata)
            audit.messages.append("Data catalog contains {0} items".format(catalog_length))
            audit.save()
    returnval['audit_id'] = audit_id
    if jsondata:
        for item in jsondata:
            taskarg = {'agency_id': agency_id, 'audit_id': audit_id, 'catalog_url': catalog_url, 'item': item}
            inspect_data_catalog_item.delay(taskarg)
    else:
        # Audit some error or something
        with transaction.atomic():
            audit.messages.append("Unable to load json data from '{0}'. Cannot find urls for datasets")
    return returnval

from __future__ import absolute_import
import json
import os
from UserDict import UserDict

from jsonschema import validate, ValidationError
import requests
from cachecontrol import CacheControl
from celery import shared_task, chord, chain, group
from celery.utils.log import get_task_logger

from django.conf import settings
from django.db import transaction, DatabaseError
import requests
from thezombies.models import Report, RequestsResponse, Agency

session = CacheControl(requests.Session(), cache_etags=False)
logger = get_task_logger(__name__)

SCHEMA_PATH = getattr(settings, 'DATA_CATALOG_SCHEMA_PATH', None)
catalog_schema = json.load(open(SCHEMA_PATH, 'r')) if SCHEMA_PATH else None

class ReturnValue(UserDict):
    """Provides a dict-like object with an errors attribute"""
    def __init__(self, data={}, errors={}):
        UserDict.__init__(self, data)
        self._errors = errors
        self.data['errors'] = self._errors

    def add_error(self, error):
        """Provide an error object, ReturnValue will store the class and value of that error"""
        if error:
            error_name = error.__class__.__name__
            self._errors[error_name] = str(error)
            self.data['errors'].update(self._errors)

@shared_task
def fetch_url(url):
    resp = error = None
    returnval = ReturnValue()
    try:
        resp = session.get(url)
    except requests.exceptions.HTTPError as e:
        error = str(e)
    returnval['response'] = resp
    returnval.add_error(error)
    return returnval

@shared_task
def find_access_urls(json_obj):
    pass

@shared_task
def report_for_agency_url(agency_id, url):
    """
    Task to save a basic report given an agency_id and a url.
    """
    result = fetch_url((url))
    resp_data = result.get('response', None)
    report_id = response_id = None
    report_info = {}
    response = None
    with transaction.atomic():
        if resp_data:
            response = RequestsResponse.objects.create_from_response(resp_data)
            report = Report.objects.create(agency_id=agency_id, url=response.requested_url, info={})
        else:
            report = Report.objects.create(agency_id=agency_id, info={})
        report.save()
        report_id = report.id
        if response:
            report.responses.add(response)
            response.save()
            response_id = response.id
    returnval = ReturnValue({
            'report_id': report_id,
            'report_info': report_info,
            'response_id': response_id
            })
    return returnval

@shared_task
def parse_json(taskarg):
    """
    Task to parse json from content
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    content = taskarg.get('content', None)
    apparent_encoding = taskarg.get('apparent_encoding', None)
    jsondata = error = None
    returnval = ReturnValue()
    if content is None:
        returnval.add_error(Exception('No content to parse'))
    try:
        jsondata = json.loads(content)
    except Exception as e:
        returnval.add_error(e)
        if apparent_encoding:
            content_str = content.decode(apparent_encoding, 'replace')
            try:
                jsondata = json.loads(content_str, encoding=apparent_encoding)
            except Exception as e:
                returnval.add_error(e)
    returnval.update({ 'json': jsondata })
    return returnval

@shared_task
def parse_json_from_response_with_report(taskarg):
    """
    Task to follow a report_for_agency_url task
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    report_id = taskarg.get('report_id', None)
    response_id = taskarg.get('response_id', None)
    report_info = taskarg.get('report_info', {})
    returnval = ReturnValue(taskarg)
    response = RequestsResponse.objects.get(id=response_id)
    response_content = str(response.content)
    result_dict = parse_json({'content':response_content, 'apparent_encoding':response.apparent_encoding})
    jsondata = result_dict.get('json', None)
    if jsondata:
         returnval['json'] = jsondata
    report_info['is_valid_json'] = True if jsondata else False
    errors = result_dict.get('errors', None)
    if errors:
        returnval['errors'].update(errors)
    returnval['report_info'] = report_info
    return returnval

@shared_task
def validate_json_catalog(taskarg):
    """
    Validate jsondata against the DATA_CATALOG_SCHEMA
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    jsondata = taskarg.get('jsondata', None)
    report_id = taskarg.get('report_id', None)
    response_id = taskarg.get('response_id', None)
    report_info = taskarg.get('report_info', {})
    returnval = ReturnValue(taskarg)
    is_valid = False
    if jsondata and catalog_schema:
        try:
            validate(jsondata, catalog_schema)
            is_valid = True
        except ValidationError as e:
            is_valid = False
            returnval.add_error(e)
    report_info['is_valid_data_catalog'] = is_valid
    returnval['report_info'] = report_info
    return returnval

@shared_task
def save_report_info(taskarg):
    report_id = taskarg.get('report_id', None)
    report_info = taskarg.get('report_info', {})
    errors = taskarg.get('errors', None) # Move errors into report_info
    if errors:
        report_info['errors'] = errors
    report_info.pop('content', None) # Let's not save content in our report
    report_info.pop('json', None) # Let's not save json in our report
    logger.info("Saving report info {0}".format(repr(report_info)))
    if report_info and report_id:
        try:
            with transaction.atomic():
                report = Report.objects.get(id=report_id)
                if not report.info:
                    report.info = {}
                report.info.update(report_info)
                report.save()
                return True
        except DatabaseError as e:
            raise e
    return False

@shared_task
def crawl_json_catalog_urls():
    agencies = Agency.objects.all()
    groupchain = group([chain(
                    report_for_agency_url.s(agency.id, agency.data_json_url),
                    parse_json_from_response_with_report.s(),
                    validate_json_catalog.s(),
                    save_report_info.s()
                ) for agency in agencies])
    return groupchain()


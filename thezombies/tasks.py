from __future__ import absolute_import
from itertools import islice

try:
    import simplejson as json
except ImportError:
    import json
import ujson

from jsonschema import Draft4Validator, ValidationError
import requests
from cachecontrol import CacheControl
from celery import shared_task, chord, chain, group
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from django.conf import settings
from django.db import transaction, DatabaseError
import requests
from requests.exceptions import (MissingSchema, InvalidSchema, InvalidURL)
from requests.packages.urllib3.exceptions import ProtocolError

from thezombies.models import (Report, URLResponse, Agency)

session = CacheControl(requests.Session(), cache_etags=False)
logger = get_task_logger(__name__)

SCHEMA_ERROR_LIMIT = 100
SCHEMA_PATH = getattr(settings, 'DATA_CATALOG_SCHEMA_PATH', None)
catalog_schema = json.load(open(SCHEMA_PATH, 'r')) if SCHEMA_PATH else None
validator = Draft4Validator(catalog_schema)

class ResultDict(dict):
    """
        Provides a dict-like object with an errors list.
        Vulnerable to overwriting errors using .update(), so don't do that.
    """
    def __init__(self, data=None, errors=None):
        super(ResultDict, self).__init__()
        self._errors = errors if errors else []
        if data:
            self.update(data)
            if not errors and hasattr(data, 'errors'):
                self._errors.extend(data.errors)
        self['errors'] = self._errors

    def add_error(self, error):
        """Provide an error object, ResultDict will store the class and value of that error"""
        if error:
            error_name = error.__class__.__name__
            error_message = getattr(error, 'message', str(error))
            if isinstance(error, ValidationError):
                error_message = '{} >>\n {}'.format(error.message, error.schema)
            error_str = '{0}: {1}'.format(error_name, error_message)
            self._errors.append(error_str)
            self['errors'] = self._errors

    @property
    def errors(self):
        return self._errors

@shared_task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    logger.warn('Task {0} raised exception: {1!r}\n{2!r}'.format(uuid, exc, result.traceback))

@shared_task
def check_and_correct_url(url, method='GET'):
    """Check a url for issues, record exceptions, and attempt to correct the url.

    :param url: URL to check and correct
    :param method: http method to use, as a string. Default is 'GET'
    """
    returnval = ResultDict({'initial_url': url})
    req = requests.Request(method.upper(), url)
    try:
        preq = req.prepare()
    except MissingSchema as e:
        returnval.add_error(e)
        new_url = 'http://{}'.format(req.url)
        req.url = new_url
        try:
            preq = req.prepare()
            returnval['corrected_url'] = preq.url
        except Exception as e:
            returnval.add_error(e)
    except Exception as e:
        returnval.add_error(e)

    return returnval

@shared_task
def request_url(url, method='GET'):
    """Task to request a url, a GET request by default. Tracks and returns errors.

    :param url: URL to request
    :param method: http method to use, as a string. Default is 'GET'
    """
    resp = None
    checker_result = check_and_correct_url(url)
    valid_url = checker_result.get('corrected_url', url)
    returnval = ResultDict(checker_result)
    try:
        resp = session.request(method.upper(), valid_url, allow_redirects=True)
    except Exception as e:
        returnval.add_error(e)
    # a non-None requests.Response will evaluate to False if it carries an HTTPError value
    if resp is not None:
        try:
            resp.raise_for_status()
        except Exception as e:
            returnval.add_error(e)
    returnval['response'] = resp
    return returnval

@shared_task
def find_data_access_urls(agency_id, catalog_url):
    latest_date = URLResponse.objects.datetimes('created_at', 'minute').latest()
    recent_responses = URLResponse.objects.filter(requested_url=catalog_url, created_at__day=latest_date.day)
    response = None
    if recent_responses.count() > 0:
        response = recent_responses.latest()
    else:
        logger.info('No stored response, fetch url')
        fetch_val = request_url(catalog_url)
        resp_data = fetch_val.get('response', None)
        response = URLResponse.objects.create_from_response(resp_data)
    result_dict = parse_json({'content':response.content.string(), 'encoding':response.encoding})
    jsondata = result_dict.get('json', None)
    returnval = ResultDict({'agency_id': agency_id, 'catalog_url':catalog_url})
    access_urls = set()
    if jsondata:
        for item in jsondata:
            isPublic = item.get('accessLevel', None) == 'public'
            hasAccessURL = 'accessURL' in item
            hasDistribution = 'distribution' in item
            if hasDistribution:
                distribution = item.get('distribution', [])
                for d in distribution:
                    if 'accessURL' in d:
                        access_urls.add(d.get('accessURL'))
            elif hasAccessURL:
                access_urls.add(item.get('accessURL'))
    else:
        # Report some error or something
        report.message = "Unable to load json data from '{0}'. Cannot find accessURLs for datasets"
    returnval['access_urls'] = access_urls
    return returnval

@shared_task
def report_on_data_access_urls(taskarg):
    agency_id = taskarg.get('agency_id', None)
    catalog_url = taskarg.get('catalog_url', None)
    access_urls = taskarg.get('access_urls', [])
    returnval = ResultDict(taskarg)
    if agency_id:
        report = Report.objects.create(agency_id=agency_id)
        returnval['report_id'] = report.id
        response_ids = []
        if len(access_urls) > 0:
            for url in access_urls:
                result = request_url(url, 'HEAD')
                response = result.get('response', None)
                if result.errors:
                    returnval.errors.extend(result.errors)
                if response is not None:
                    resp_obj = URLResponse.objects.create_from_response(response, save_content=False)
                    report.responses.add(resp_obj)
                    resp_obj.save()
                    response_ids.append(resp_obj.id)
                else:
                    logger.error("Error fetching and saving '{0}'!".format(url))
        else:
            report.message = "No dataset accessURLs were found for {0}".format(catalog_url)
        report.save()
        return returnval
    else:
        raise Exception('An agency id is required to create a report on data accessURLs.')

@shared_task
def crawl_agency_datasets(agency_id):
    """Task that crawl the datasets from an agency data catalog.
    Chains find_data_access_urls and report_on_data_access_urls tasks.

    :param agency_id: Database id of the agency whose catalog should be crawled.

    """
    agency = Agency.objects.get(id=agency_id)
    taskchain = chain(
                    find_data_access_urls.subtask((agency.id, agency.data_json_url),
                                                  options={'link_error':error_handler.s()}),
                    report_on_data_access_urls.s()
                )
    return taskchain()

@shared_task
def report_for_agency_url(agency_id, url):
    """Task to save a basic report given an agency_id and a url.

    :param agency_id: Database id of the agency to create a report for.
    :param url: URL to report on.

    """
    result = request_url((url))
    returnval = ResultDict(result)
    resp_data = result.get('response', None)
    report_id = response_id = None
    response_info = {}
    response = None
    with transaction.atomic():
        if resp_data is not None:
            response = URLResponse.objects.create_from_response(resp_data)
            report = Report.objects.create(agency_id=agency_id, url=response.requested_url)
        else:
            report = Report.objects.create(agency_id=agency_id)
        report.save()
        returnval['report_id'] = report.id
        if response:
            response.errors.extend(returnval.errors)
            report.responses.add(response)
            response.save()
            returnval['response_id'] = response.id
    if not resp_data.ok:
        # If the response is not okay, raise an error so we can handle that as an error
        resp_data.raise_for_status()
    returnval['response_info'] = response_info
    return returnval

@shared_task
def parse_json(taskarg):
    """
    Task to parse json from content

    :param taskarg: ResultDict or regular dict containing values for keys 'content and optionally 'encoding'.
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    content = taskarg.get('content', None)
    encoding = taskarg.get('encoding', 'iso-8859-1')
    jsondata = None
    parse_errors = False
    returnval = ResultDict()
    if content is None:
        returnval.add_error(Exception('No content to parse'))
    else:
        try:
            jsondata = json.loads(content, encoding=encoding)
        except Exception as e:
            parse_errors = True
            returnval.add_error(e)
            content_str = content.decode(encoding, 'replace')
            try:
                jsondata = ujson.loads(content_str)
            except Exception as e:
                parse_errors = True
                returnval.add_error(e)
    returnval.update({ 'json': jsondata, 'parse_errors': parse_errors })
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
    response_info = taskarg.get('response_info', {})
    returnval = ResultDict(taskarg)
    response = URLResponse.objects.get(id=response_id)
    response_content = response.content.string()
    encoding = response.encoding if response.encoding else response.apparent_encoding
    result_dict = parse_json({'content':response_content, 'encoding':encoding})
    jsondata = result_dict.get('json', None)
    parse_errors = result_dict.get('parse_errors', False)
    if jsondata:
         returnval['json'] = jsondata
    response_info['json_errors'] = True if parse_errors else False
    response_info['is_json'] = True if jsondata else False
    errors = result_dict.get('errors', None)
    if errors:
        returnval.errors.extend(errors)
    returnval.get('response_info', {}).update(response_info)
    return returnval

@shared_task
def validate_json_catalog(taskarg):
    """
    Validate jsondata against the DATA_CATALOG_SCHEMA
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    jsondata = taskarg.get('json', None)
    response_info = taskarg.get('response_info', {})
    returnval = ResultDict(taskarg)
    is_valid = False
    if jsondata and catalog_schema:
        is_valid = validator.is_valid(jsondata)
        if not is_valid:
            # Save up to SCHEMA_ERROR_LIMIT errors from schema validation
            error_iter = islice(validator.iter_errors(jsondata), SCHEMA_ERROR_LIMIT)
            for e in error_iter:
                returnval.add_error(e)
    response_info['is_valid_data_catalog'] = is_valid
    returnval.get('response_info', {}).update(response_info)
    return returnval

@shared_task
def save_response_info(taskarg):
    report_id = taskarg.get('report_id', None)
    response_id = taskarg.get('response_id', None)
    response_info = taskarg.get('response_info', {})
    returnval = ResultDict(taskarg)
    response_info.pop('content', None) # Let's not save content in our report
    response_info.pop('json', None) # Let's not save json in our report
    logger.info("Saving report info {0}".format(repr(response_info)))
    returnval['saved'] = False
    if response_info:
        if report_id:
            try:
                with transaction.atomic():
                    report = Report.objects.get(id=report_id)
                    report.save()
                    if response_id:
                        response = URLResponse.objects.get(id=response_id)
                        response.info.update(response_info)
                        if len(returnval.errors):
                            response.errors.extend(returnval.errors)
                        response.save()
                    returnval['saved'] = True
            except DatabaseError as e:
                raise e

@shared_task
def crawl_json_catalog_urls():
    agencies = Agency.objects.all()
    groupchain = group([chain(
                    report_for_agency_url.subtask((agency.id, agency.data_json_url),
                                                  options={'link_error':error_handler.s()}),
                    parse_json_from_response_with_report.s(),
                    validate_json_catalog.s(),
                    save_response_info.s()
                ) for agency in agencies])
    return groupchain()


from __future__ import absolute_import
import json
import os

from jsonschema import validate, ValidationError
import requests
from cachecontrol import CacheControl
from celery import shared_task, chord, chain, group
from celery.utils.log import get_task_logger

from django.conf import settings
import requests
from thezombies.models import ReportOnResponse, RequestsResponse, Agency

session = CacheControl(requests.Session(), cache_etags=False)
logger = get_task_logger(__name__)

SCHEMA_PATH = getattr(settings, 'DATA_CATALOG_SCHEMA_PATH', None)
catalog_schema = json.load(open(SCHEMA_PATH, 'r')) if SCHEMA_PATH else None

@shared_task
def fetch_url(url):
    resp = session.get(url)
    return resp

@shared_task
def find_access_urls(json_obj):
    pass

@shared_task
def save_report_for_response(args):
    """Returns a tuple containing a Report and a RequestsResponse object"""
    obj = args
    if isinstance(args, list) and len(args) == 1:
        obj = args[0]
    reporter = ReportOnResponse(obj)
    report, response = reporter.generate()
    try:
        report.save()
        report.responses.add(response)
        response.save()
        return (report, response)
    except Exception, e:
        raise e

@shared_task
def report_on_url(url):
    return chain(fetch_url.s(url), save_report_for_response.s())()

@shared_task
def parse_json_from_response(response):
    jsondata = None
    if response is None:
        raise Exception('No response given')
    is_requests_response = isinstance(response, requests.Response)
    content = response.content if is_requests_response else response.content.read()
    try:
        jsondata = response.json()
    except Exception as e:
        content_str = content.decode(response.apparent_encoding, 'replace')
        try:
            jsondata = json.loads(content_str)
        except Exception as e:
            raise e
    return jsondata

@shared_task
def parse_json_from_response_with_report(args_tuple):
    report, response = args_tuple
    jsondata = parse_json_from_response(response)
    return (jsondata, report, response)

@shared_task
def validate_json_catalog(args_tuple):
    jsondata, report, response = args_tuple
    is_valid = False
    if catalog_schema and jsondata:
        try:
            validate(jsondata, catalog_schema)
            is_valid = True
        except ValidationError as e:
            is_valid =  False
    else:
        raise IOError('Unable to load json schema')
    report.content_valid = True
    if not report.info:
        report.info = {}
    report.info['is_valid_json'] = is_valid
    report.save()
    return is_valid


@shared_task
def crawl_json_catalog_urls():
    agencies = Agency.objects.all()
    groupchain = group([chain(
                    fetch_url.s(agency.data_json_url),
                    save_report_for_response.s(),
                    parse_json_from_response_with_report.s(),
                    validate_json_catalog.s()
                ) for agency in agencies])
    return groupchain()

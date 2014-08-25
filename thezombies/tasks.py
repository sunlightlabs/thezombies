from __future__ import absolute_import
import json

from jsonschema import validate
import requests
from cachecontrol import CacheControl
from celery import shared_task, chord
from celery.utils.log import get_task_logger

from thezombies.models import ReportOnResponse

session = CacheControl(requests.Session(), cache_etags=False)
logger = get_task_logger(__name__)

@shared_task
def fetch_url(url):
    resp = session.get(url)
    return resp

@shared_task
def parse_json(response):
    obj = None
    if response is None:
        raise Exception('Empty response')
    try:
        obj = response.json()
    except Exception as e:
        content_str = response.content.decode(response.apparent_encoding)
        try:
            obj = json.loads(content_str)
        except Exception as e:
            raise e
    return obj

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
    return fetch_url.apply_async((url,), link=save_report_for_response.s())


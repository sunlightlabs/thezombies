from __future__ import absolute_import
import json

from jsonschema import validate
import requests
from cachecontrol import CacheControl
from celery import shared_task
from celery.utils.log import get_task_logger

from thezombies.models import ReportableResponse

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
def generate_report_for_response(args):
    logger.info("Got this as an arg {}".format(repr(args)))
    logger.info("It has type {}".format(type(args)))
    obj = args
    if isinstance(args, list) and len(args) == 1:
        obj = args[0]
    reporter = ReportableResponse(obj)
    report = reporter.generate_report()
    return report

@shared_task
def save_report_for_response(args):
    logger.info("Got this as an arg {}".format(repr(args)))
    logger.info("It has type {}".format(type(args)))
    obj = args
    if isinstance(args, list) and len(args) == 1:
        obj = args[0]
    report = None
    try:
        report = generate_report_for_response(obj)
        try:
            report.save()
        except Exception as e:
            return e
    except Exception as e:
        return e
    return report



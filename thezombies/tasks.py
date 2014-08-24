import json

from jsonschema import validate
import requests
from cachecontrol import CacheControl
from flask.ext.sqlalchemy import SQLAlchemy
from celery.utils.log import get_task_logger

from thezombies.factory import create_celery_app
from thezombies.models import ReportableResponse

db = SQLAlchemy()
celery = create_celery_app()

session = CacheControl(requests.Session(), cache_etags=False)
logger = get_task_logger(__name__)

@celery.task
def fetch_url(url):
    resp = session.get(url)
    return resp

@celery.task
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

@celery.task
def find_access_urls(json_obj):
    pass

@celery.task
def generate_report_for_response(args):
    logger.info("Got this as an arg {}".format(repr(args)))
    logger.info("It has type {}".format(type(args)))
    obj = args
    if isinstance(args, list) and len(args) == 1:
        obj = args[0]
    reporter = ReportableResponse(obj)
    report = reporter.generate_report()
    return report

@celery.task
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
            db.session.add(report)
            db.session.commit()
        except Exception as e:
            return e
    except Exception as e:
        return e
    return report



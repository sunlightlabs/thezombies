import os
import json

from jsonschema import validate

from rq import Connection, Queue
from rq.job import Job
from redis import Redis

import requests
from cachecontrol import CacheControl

session = CacheControl(requests.Session(), cache_etags=False)
q = Queue(connection=Redis())


def fetch_url(url):
    resp = session.get(url)
    return resp

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

def parse_json_from_job(job_id):
    j = Job.fetch(job_id)
    if j.is_finished:
        return parse_json(j.result)

def validate_json_from_job(job_id, schema_obj):
    j = Job.fetch(job_id)
    if j.is_finished:
        try:
            validate(j.result, schema_obj)
            return True
        except Exception as e:
            raise e

def find_access_urls(json_obj):
    pass

def generate_report(report_info, report_dir):
    for task in report_info.get('tasks'):
        task_id = task.get('id')
        if task_id:
            j = Job.fetch(task_id)
            task['is_finished'] = j.is_finished
            task['is_failed'] = j.is_failed
    agency_info = report_info.get('agency')
    agency_name = agency_info.get('Agency').strip().lower()
    report_name = os.path.join(os.path.abspath(report_dir), '{}.json'.format(agency_name))
    json.dump(report_info, open(report_name, 'w'))
    return report_info



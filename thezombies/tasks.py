import json

from rq.job import Job

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

session = CacheControl(requests.Session(), cache=FileCache('.webcache'), cache_etags=False)

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
        parse_json(j.result)

def validate_json_against_schema(json, schema):
    pass
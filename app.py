#!/usr/bin/env python

import csv
import re
import os

from rq import Connection, Queue
from redis import Redis

from thezombies import (AuditableRequest, AuditableResponse)
from thezombies.utils import is_valid_url
from thezombies.tasks import fetch_url, parse_json_from_job

IMPORTANT_HEADERS = ('Agency', '/data' '/data.json', 'JSON Error?')

TIMEOUT_SECS = 300

q = Queue(connection=Redis())

def main():
    reader = csv.DictReader(open('open_data_data_inventory_audit.csv', 'r'))
    audit_objects = list(reader)

    valid_data_urls = [x.get('/data.json') for x in audit_objects if is_valid_url(x.get('/data.json'))]
    print("{} valid urls out of {} objects".format(len(valid_data_urls), len(audit_objects)))

    jobs = []
    for url in valid_data_urls:
        fetcher = q.enqueue(fetch_url, url, timeout=TIMEOUT_SECS)
        parser = q.enqueue(parse_json_from_job, fetcher.id, depends_on=fetcher)
        jobs.append(parser)


if __name__ == '__main__':
    main()
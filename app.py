#!/usr/bin/env python

import csv
import os
import json

from rq import Connection, Queue
from redis import Redis

from thezombies import (AuditableRequest, AuditableResponse)
from thezombies.utils import is_valid_url
from thezombies.tasks import fetch_url, parse_json_from_job, validate_json_from_job, generate_report

IMPORTANT_HEADERS = ('Agency', '/data' '/data.json', 'JSON Error?')

TIMEOUT_SECS = 300

CATALOG_SCHEMA = json.load(open(os.path.abspath('./schema/1_0_final/catalog.json'), 'r'))

REPORT_PATH = os.path.abspath('.')

q = Queue(connection=Redis())

def main():
    reader = csv.DictReader(open('open_data_data_inventory_audit.csv', 'r'))
    audit_objects = list(reader)

    auditable_agencies = [x for x in audit_objects if is_valid_url(x.get('/data.json'))]
    print("{} valid urls out of {} objects".format(len(auditable_agencies), len(audit_objects)))

    for agency in auditable_agencies:
        report_info = {
            'agency': agency
        }
        report_info['url'] = agency.get('/data.json')
        tasks = []

        fetcher = q.enqueue(fetch_url, report_info['url'], timeout=TIMEOUT_SECS)
        tasks.append({'id': fetcher.id, 'name': 'fetcher'})

        parser = q.enqueue(parse_json_from_job, fetcher.id, depends_on=fetcher, timeout=TIMEOUT_SECS)
        tasks.append({'id': parser.id, 'name': 'parser'})

        validator = q.enqueue(validate_json_from_job, parser.id, CATALOG_SCHEMA, depends_on=parser)
        tasks.append({'id': validator.id, 'name': 'validator'})

        report_info['tasks'] = tasks
        reporter = q.enqueue(generate_report, report_info, REPORT_PATH, depends_on=validator)


if __name__ == '__main__':
    main()
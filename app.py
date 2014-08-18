#!/usr/bin/env python

import csv
import os
import json

from rq import Connection, Queue
from redis import Redis

from thezombies import (AuditableRequest, AuditableResponse)
from thezombies.utils import is_valid_url
from thezombies.tasks import fetch_url, parse_json_from_job, validate_json_from_job

IMPORTANT_HEADERS = ('Agency', '/data' '/data.json', 'JSON Error?')

TIMEOUT_SECS = 300

CATALOG_SCHEMA = json.load(open(os.path.abspath('./schema/1_0_final/catalog.json'), 'r'))

q = Queue(connection=Redis())

def main():
    reader = csv.DictReader(open('open_data_data_inventory_audit.csv', 'r'))
    audit_objects = list(reader)

    auditable_agencies = [x for x in audit_objects if is_valid_url(x.get('/data.json'))]
    print("{} valid urls out of {} objects".format(len(auditable_agencies), len(audit_objects)))

    for agency in auditable_agencies:
        url = agency.get('/data.json')
        fetcher = q.enqueue(fetch_url, url, timeout=TIMEOUT_SECS)
        parser = q.enqueue(parse_json_from_job, fetcher.id, depends_on=fetcher, timeout=TIMEOUT_SECS)
        validator = q.enqueue(validate_json_from_job, parser.id, CATALOG_SCHEMA, depends_on=parser)


if __name__ == '__main__':
    main()
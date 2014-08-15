#!/usr/bin/env python

import csv
import re
import json
import os
import hashlib

from thezombies import (AuditableRequest, AuditableResponse)
from thezombies.utils import is_valid_url

from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession

session = FuturesSession(executor=ThreadPoolExecutor(max_workers=10))

IMPORTANT_HEADERS = ('Agency', '/data' '/data.json', 'JSON Error?')

TMP_SAVE = os.path.abspath('./tmp')

class NotFoundError(Exception):
    """ Raised when passing an search fails"""
    pass

# def find_object_with_url(url, objects):
#     def url_in_values(item):
#         return url in item.values()
#     results = list(filter(url_in_values, objects))
#     if len(results) is 1:
#         return results[0]
#     else:
#         raise NotFoundError

# def get_url_hash(url):
#     return hashlib.sha1(url.encode('utf-8')).hexdigest()


def main():
    reader = csv.DictReader(open('open_data_data_inventory_audit.csv', 'r'))
    audit_objects = list(reader)

    futures = []
    for item in audit_objects[4:7]:
        data_json_url = item.get('/data.json')
        if is_valid_url(data_json_url):
            f = session.get(data_json_url)
            futures.append(f)

    for f in futures:
        resp = AuditableResponse(f.result())
        print(resp.audit())




if __name__ == '__main__':
    main()
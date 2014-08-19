import json
import os.path

FILE_DIR = os.path.abspath(os.path.dirname(__file__))
AGENCY_JSON_PATH = os.path.join(FILE_DIR, 'agencies.json')

agencies_json = json.load(open(AGENCY_JSON_PATH, 'r'))
agencies = sorted(agencies_json, key=lambda x: x.get('agency'))
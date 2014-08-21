import json
import os.path

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from .utils import slugify

FILE_DIR = os.path.abspath(os.path.dirname(__file__))
AGENCY_JSON_PATH = os.path.join(FILE_DIR, 'fixtures/agencies.json')

agencies_json = json.load(open(AGENCY_JSON_PATH, 'r'))

class Agency(object):
    """Describes an agency"""
    def __init__(self, raw):
        super(Agency, self).__init__()
        self.name = raw.get('agency', None)
        self.agency_type = raw.get('agency_type', None)
        self.url = raw.get('url', None)
        self._slug = slugify(self.name)
        self._data_json_url = urljoin(self.url, 'data.json')
        self._data_page_url = urljoin(self.url, 'data')
        self._digitalstrategy_json_url = urljoin(self.url, 'digitalstrategy.json')

    @property
    def slug(self):
        return self._slug

    @property
    def data_json_url(self):
        return self._data_json_url

    @property
    def data_page_url(self):
        return self._data_page_url

    @property
    def digitalstrategy_json_url(self):
        return self._digitalstrategy_json_url



agencies = [Agency(x) for x in agencies_json]
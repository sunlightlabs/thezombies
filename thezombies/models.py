import json
import os.path

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql

db = SQLAlchemy()

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from .utils import slugify


class Agency(db.Model):
    """Describes an agency"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    agency_type = db.Column(db.String(40))
    slug = db.Column(db.String(120), unique=True)
    url = db.Column(db.String(255), unique=True)

    def __init__(self, raw):
        super(Agency, self).__init__()
        self.name = raw.get('agency', None).strip()
        self.agency_type = raw.get('agency_type', None)
        self.url = raw.get('url', None)
        self.slug = slugify(self.name)

    @property
    def data_json_url(self):
        return urljoin(self.url, 'data.json')

    @property
    def data_page_url(self):
        return urljoin(self.url, 'data')

    @property
    def digitalstrategy_json_url(self):
        return urljoin(self.url, 'digitalstrategy.json')

    def __repr__(self):
        return '<Agency %r>' % self.name


def load_agencies_from_json():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    agency_json_path = os.path.join(file_dir, 'fixtures/agencies.json')
    agencies_json = json.load(open(agency_json_path, 'r'))

    return [Agency(x) for x in agencies_json]
import json
import os.path
from datetime import datetime
import pytz

from requests import Request, Response

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import HSTORE

db = SQLAlchemy()

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse

from .utils import slugify


class Report(db.Model):
    """A Report on agency, usually concerning data at a url"""
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    created_at = db.Column(db.DateTime(timezone=True))
    url = db.Column(db.String(200))
    message = db.Column(db.Text)
    data = db.Column(MutableDict.as_mutable(HSTORE))

    def __init__(self, url=None):
        super(Report, self).__init__()
        self.created_at = datetime.now(pytz.utc)
        self.data = MutableDict()
        if url:
            self.url = url

    def __repr__(self):
        return '<Report {0}>'.format(self.url)


class Agency(db.Model):
    """Describes an agency"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    agency_type = db.Column(db.String(40))
    slug = db.Column(db.String(120), unique=True)
    url = db.Column(db.String(200), unique=True)
    reports = db.relationship('Report', backref='agency', lazy='dynamic')

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
        return '<Agency {0}>'.format(self.name)

class ReportableResponse(object):
    """docstring for ReportableResponse"""
    def __init__(self, obj):
        super(ReportableResponse, self).__init__()
        if isinstance(obj, Response):
            self.response = obj
        else:
            raise TypeError('Object must be a requests.Response instance')

    def generate_report(self):

        def build_extra_data(resp):
            base_attrs = ('encoding', 'apparent_encoding', 'status_code')
            data_obj = {}
            data_obj['headers'] = dict(resp.headers)
            for attr in base_attrs:
                value = getattr(resp, attr, None)
                data_obj[attr] = value
            url_history = [] if (len(resp.history)) else None
            for r in resp.history:
                url_history.append(r.url)
            data_obj['history.urls'] = url_history
            return data_obj

        report = Report()
        report.url = self.response.url
        urlparts = urlparse(report.url)
        like_qs = '%{0}%'.format(urlparts.netloc)
        agency = Agency.query.filter(Agency.url.like(like_qs)).first()
        if agency:
            report.agency = agency
        data = build_extra_data(self.response)
        report.data.update(data)

        return report


def load_agencies_from_json():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    agency_json_path = os.path.join(file_dir, 'fixtures/agencies.json')
    agencies_json = json.load(open(agency_json_path, 'r'))

    return [Agency(x) for x in agencies_json]
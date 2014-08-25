import json

from requests import Request, Response

from django.db import models
from django_hstore import hstore
from django.utils.text import slugify

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse


class Report(models.Model):
    """A Report on agency, usually concerning data at a url"""
    agency = models.ForeignKey('Agency')
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(max_length=200)
    message = models.TextField(blank=True)
    data = hstore.DictionaryField()
    objects = hstore.HStoreManager()

    def __repr__(self):
        return '<Report: {0}>'.format(self.url)

    def __str__(self):
        return self.__repr__()


class Agency(models.Model):
    """Describes an agency"""
    name = models.CharField(max_length=100, unique=True)
    agency_type = models.CharField(max_length=40)
    slug = models.SlugField(max_length=120, unique=True)
    url = models.URLField(max_length=200, unique=True)

    class Meta:
        verbose_name_plural = "agencies"
        ordering = ('agency_type', 'name')


    def save(self, *args, **kwargs):
        if self.slug is None or self.slug == '':
            self.slug = slugify(self.name)
        super(Blog, self).save(*args, **kwargs) # Call the "real" save() method.

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
        return '<Agency: {0}>'.format(self.name)

    def __str__(self):
        return self.__repr__()


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
        agency = Agency.objects.get(url__contains=urlparts.netloc)
        if agency:
            report.agency = agency
        data = build_extra_data(self.response)
        report.data = data

        return report


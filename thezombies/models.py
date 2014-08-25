import json
import uuid

from requests import Request, Response

from django.db import models
from django.core.files.base import ContentFile
from django_hstore import hstore
from django.utils.text import slugify

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse


class Report(models.Model):
    """A Report on agency, usually concerning data at a url"""
    agency = models.ForeignKey('Agency', related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)
    url = models.URLField(blank=True, null=True)

    def __repr__(self):
        return '<Report: {0}>'.format(self.url if self.url else self.id)

    def __str__(self):
        return self.__repr__()

    class Meta:
        get_latest_by = 'created_at'

class RequestsResponse(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    requested_url = models.URLField()
    encoding = models.CharField(max_length=40, blank=True, null=True)
    apparent_encoding = models.CharField(max_length=40, blank=True, null=True)
    content = models.FileField(upload_to='responses', blank=True, null=True)
    content_type = models.CharField(max_length=40, blank=True, null=True)
    content_length = models.PositiveIntegerField(blank=True, null=True)
    status_code = models.IntegerField(max_length=3)
    reason = models.CharField(max_length=80, help_text='Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".')
    headers = hstore.DictionaryField()
    content_valid = models.NullBooleanField()
    report = models.ForeignKey('Report', related_name='responses', null=True, blank=True)

    objects = hstore.HStoreManager()

    @classmethod
    def create_from_response(cls, resp):
        if isinstance(resp, Response):
            obj = cls(url=resp.url, status_code=resp.status_code,
                encoding=resp.encoding, reason=resp.reason)
            obj.requested_url= resp.history[0].url if len(resp.history) > 0 else resp.request.url
            obj.headers = dict(resp.headers)
            obj.apparent_encoding = resp.apparent_encoding
            content_length = resp.headers.get('content-length', None)
            if content_length:
                obj.content_length = int(content_length)
            if obj.content_length and obj.content_length > 0:
                file_id = uuid.uuid4().hex
                content_file = ContentFile(resp.content)
                obj.content.save(file_id, content_file)
            obj.content_type = resp.headers.get('content-type', None)
            return obj
        else:
            raise TypeError('create_from_response expects a requests.Response object')

    class Meta:
        verbose_name = 'Requests Response'
        verbose_name_plural = 'Requests Responses'
        get_latest_by = 'created_at'

    def __repr__(self):
        return '<RequestsResponse: {0}>'.format(self.url)

    def __str__(self):
        return self.__repr__()


class Agency(models.Model):
    """Describes an agency"""
    name = models.CharField(max_length=100, unique=True)
    agency_type = models.CharField(max_length=40)
    slug = models.SlugField(max_length=120, unique=True)
    url = models.URLField(unique=True)

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
        return self.name


class ReportOnResponse(object):
    """docstring for ReportOnResponse"""
    def __init__(self, obj):
        super(ReportOnResponse, self).__init__()
        if isinstance(obj, Response):
            self.response = obj
        else:
            raise TypeError('Object must be a requests.Response instance')

    def generate(self):
        """Returns a tuple containing a Report and a RequestsResponse object"""
        response_obj = RequestsResponse.create_from_response(self.response)
        report = Report(url=response_obj.requested_url)
        urlparts = urlparse(response_obj.requested_url)
        agency = Agency.objects.get(url__contains=urlparts.netloc)
        if agency:
            report.agency = agency

        return (report, response_obj)


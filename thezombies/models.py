from requests import Request, Response

from django.db import models
from django_hstore import hstore
from djorm_pgarray.fields import TextArrayField
from django.utils.text import slugify

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse

class Report(models.Model):
    """A Report on agency, usually concerning data at a url"""
    agency = models.ForeignKey('Agency', related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True)
    url = models.URLField(blank=True, null=True)
    info = hstore.DictionaryField(blank=True, null=True, default={})
    errors = TextArrayField(blank=True, null=True, default=[])

    objects = hstore.HStoreManager()

    def __repr__(self):
        return '<Report: {0}>'.format(self.url if self.url else self.id)

    def __str__(self):
        return self.__repr__()

    class Meta:
        get_latest_by = 'created_at'
        ordering =  ('-created_at',)

class URLResponseManager(hstore.HStoreManager):

    def create_from_response(self, resp):
        """
        Create a URLResponse object from a requests.Response
        """
        if isinstance(resp, Response):
            content_type = resp.headers.get('content-type', None)
            content = ResponseContent(binary=resp.content, content_type=content_type)
            content.save()
            obj = self.create(content=content, url=resp.url, status_code=resp.status_code,
                encoding=resp.encoding, reason=resp.reason)
            obj.requested_url= resp.history[0].url if len(resp.history) > 0 else resp.request.url
            obj.headers = dict(resp.headers)
            # TODO: defer detection of apparent encoding. A task, perhaps
            obj.apparent_encoding = resp.apparent_encoding
            return obj
        else:
            raise TypeError('create_from_response expects a requests.Response object')

class ResponseContent(models.Model):
    binary = models.BinaryField(blank=True, null=True)
    content_type = models.CharField(max_length=40, blank=True, null=True)
    length = models.IntegerField(blank=True, editable=False)

    class Meta:
        verbose_name = 'ResponseContent'
        verbose_name_plural = 'ResponsesContents'

    def save(self, *args, **kwargs):
        self.length = len(self.binary) if self.binary else 0
        super(ResponseContent, self).save(*args, **kwargs)

    def string(self):
        return str(self.binary)

    def __repr__(self):
        return '<ResponseContent: {0 bytes>'.format(self.length)

    def __str__(self):
        return self.__repr__()

class URLResponse(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    requested_url = models.URLField()
    encoding = models.CharField(max_length=40, blank=True, null=True)
    apparent_encoding = models.CharField(max_length=40, blank=True, null=True)
    content = models.OneToOneField(ResponseContent, related_name='content_for', editable=False)
    status_code = models.IntegerField(max_length=3)
    reason = models.CharField(max_length=80, help_text='Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".')
    headers = hstore.DictionaryField()
    report = models.ForeignKey('Report', related_name='responses', null=True, blank=True)

    objects = URLResponseManager()

    class Meta:
        verbose_name = 'Requests Response'
        verbose_name_plural = 'Requests Responses'
        get_latest_by = 'created_at'

    def __repr__(self):
        return '<URLResponse: {0}>'.format(self.url)

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

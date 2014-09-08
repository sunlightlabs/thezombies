from requests import Request, Response

from django.db import models
from django_hstore import hstore
from djorm_pgarray.fields import TextArrayField
from django.utils.text import slugify
from django.core.urlresolvers import reverse

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urlparse import urljoin, urlparse

def list_default():
    return []

def dictionary_default():
    return {}

class Report(models.Model):
    """A Report on agency, usually concerning data at a url"""

    GENERIC_REPORT = 'RPT'
    DATA_CATALOG_VALIDATION = 'DCV'
    DATA_CATALOG_CRAWL = 'DCC'

    REPORT_TYPE_CHOICES = (
        (GENERIC_REPORT, 'Generic Report'),
        (DATA_CATALOG_VALIDATION, 'Data Catalog Validation'),
        (DATA_CATALOG_CRAWL, 'Data Catalog Crawl'),
    )

    report_type = models.CharField(max_length=3,
                                    choices=REPORT_TYPE_CHOICES, default=GENERIC_REPORT)
    agency = models.ForeignKey('Agency', related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text='You can record basic (unformatted text) notes here.')
    messages = TextArrayField(blank=True, null=True, default=list_default, editable=False,
        help_text='Stores messages generated when report was run.')
    errors = TextArrayField(blank=True, null=True, default=list_default,
        help_text='Stores errors that occurred during the tasks that triggered the report. May overlap with errors on responses')
    url = models.URLField(blank=True, null=True)

    def __repr__(self):
        return '<Report: {0}>'.format(self.url if self.url else self.id)

    def __str__(self):
        return '{report_type} for {identifier}'.format(report_type=self.get_report_type_display(),
                                                    identifier=self.url if self.url else self.agency)

    class Meta:
        get_latest_by = 'created_at'
        ordering =  ('-created_at',)

    def get_absolute_url(self):
        return reverse('report-detail', kwargs={'pk': str(self.pk)})

    def inspections_failure_count(self):
        return self.inspections.filter(status_code__gte=400).count()

    def inspections_404_count(self):
        return self.inspections.filter(status_code=404).count()

    def inspections_html_count(self):
        return self.inspections.filter(headers__contains={'content-type':'text/html'}).count()

    def inspections_total_count(self):
        return self.inspections.count()


class URLInspectionManager(hstore.HStoreManager):

    def create_from_response(self, resp, save_content=True):
        """
        Create a URLInspection object from a requests.Response
        """
        if isinstance(resp, Response):
            content_type = resp.headers.get('content-type', None)
            if save_content:
                content = ResponseContent(binary=resp.content, content_type=content_type)
                content.save()
            obj = self.create(content=content if save_content else None, url=resp.url, status_code=resp.status_code,
                encoding=resp.encoding, reason=resp.reason)
            obj.requested_url= resp.history[0].url if len(resp.history) > 0 else resp.request.url
            obj.headers = dict(resp.headers)
            # TODO: defer detection of apparent encoding. A task, perhaps
            if save_content:
                obj.apparent_encoding = resp.apparent_encoding
            for n, hist in enumerate(resp.history):
                histobj = self.create(requested_url=hist.request.url, url=hist.url,
                                      status_code=hist.status_code, encoding=resp.encoding, parent=obj)
                histobj.headers = dict(hist.headers)
                histobj.save()
                obj.history[str(n)] = histobj

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
        return '<ResponseContent: {0} bytes>'.format(self.length)

    def __str__(self):
        return self.__repr__()

class URLInspection(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.TextField(blank=True, null=True) # We may get (and want to store) really long or invalid urls, so...
    requested_url = models.TextField() # We may get (and want to store) really long or invalid urls, so...
    encoding = models.CharField(max_length=40, blank=True, null=True)
    apparent_encoding = models.CharField(max_length=40, blank=True, null=True)
    content = models.OneToOneField(ResponseContent, null=True, related_name='content_for', editable=False)
    history = hstore.ReferencesField(blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)
    status_code = models.IntegerField(max_length=3, blank=True, null=True)
    reason = models.CharField(blank=True, null=True, max_length=80, help_text='Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".')
    headers = hstore.DictionaryField(default=dictionary_default)
    info = hstore.DictionaryField(blank=True, null=True, default=dictionary_default)
    errors = TextArrayField(blank=True, null=True, default=list_default)
    report = models.ForeignKey('Report', related_name='inspections', null=True, blank=True)

    objects = URLInspectionManager()

    class Meta:
        verbose_name = 'URL Inspection'
        verbose_name_plural = 'URL Inspections'
        get_latest_by = 'created_at'

    def __repr__(self):
        return '<URLInspection: {0} : {1}>'.format(self.requested_url, self.status_code)

    def __str__(self):
        return self.__repr__()

    @property
    def content_type(self):
        if self.content:
            return self.content.content_type
        else:
            content_type = 'Unknown'
            if self.headers:
                content_type = self.headers.get('content-type', 'Unknown')
            return content_type


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

    def get_absolute_url(self):
        return reverse('agency-detail', kwargs={'slug': self.slug})



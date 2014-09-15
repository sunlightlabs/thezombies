from requests import Response

from django.db import models
from django_hstore import hstore
from djorm_pgarray.fields import TextArrayField
from django.utils.text import slugify
from django.core.urlresolvers import reverse

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


def list_default():
    return []


def dictionary_default():
    return {}


class Probe(models.Model):
    """A component of an Audit that takes some initial data and
    stores a result of some tasks performed on that data
    """

    GENERIC_PROBE = 0
    URL_PROBE = 1
    JSON_PROBE = 2
    VALIDATION_PROBE = 3

    PROBE_TYPE_CHOICES = (
        (GENERIC_PROBE, 'Generic Probe'),
        (URL_PROBE, 'URL Probe'),
        (JSON_PROBE, 'JSON Probe'),
        (VALIDATION_PROBE, 'Validation Probe'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    probe_type = models.PositiveSmallIntegerField(choices=PROBE_TYPE_CHOICES, default=GENERIC_PROBE)
    previous = models.ForeignKey('self', related_name='next', blank=True, null=True, on_delete=models.SET_NULL)
    initial = hstore.DictionaryField(blank=True, null=True, default=dictionary_default)
    result = hstore.DictionaryField(blank=True, null=True, default=dictionary_default)
    errors = TextArrayField(blank=True, null=True, default=list_default)
    audit = models.ForeignKey('Audit', null=True, blank=True)

    objects = hstore.HStoreManager()

    def __repr__(self):
        return '<{0}: {1}>'.format(self.get_probe_type_display(), self.id)

    def __str__(self):
        return self.__repr__()

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def error_count(self):
        return len(self.errors)


class Audit(models.Model):
    """An audit on agency, made up of auditables"""

    GENERIC_AUDIT = u'ADT'
    DATA_CATALOG_VALIDATION = u'DCV'
    DATA_CATALOG_CRAWL = u'DCC'

    AUDIT_TYPE_CHOICES = (
        (GENERIC_AUDIT, u'Generic Audit'),
        (DATA_CATALOG_VALIDATION, u'Data Catalog Validation'),
        (DATA_CATALOG_CRAWL, u'Data Catalog Crawl'),
    )

    audit_type = models.CharField(max_length=3,
                                  choices=AUDIT_TYPE_CHOICES, default=GENERIC_AUDIT)
    agency = models.ForeignKey('Agency')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text='You can record basic (unformatted text) notes here.')
    messages = TextArrayField(blank=True, null=True, default=list_default, editable=False,
                              help_text='Stores messages generated when audit was run.')

    def __repr__(self):
        return '<Audit: {0}>'.format(self.id)

    def __str__(self):
        return '{audit_type} for {identifier}'.format(audit_type=self.get_audit_type_display(),
                                                      identifier=self.agency)

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def get_absolute_url(self):
        return reverse('audit-detail', kwargs={'pk': str(self.pk)})

    @property
    def url_inspections(self):
        return URLInspection.objects.filter(probe__in=self.probe_set.all())

    def url_inspections_count(self):
        return self.url_inspections.count()

    def url_inspections_failure_count(self):
        return self.url_inspections.filter(status_code__gte=400).count()

    def url_inspections_404_count(self):
        return self.url_inspections.filter(status_code=404).count()

    def url_inspections_html_count(self):
        return self.url_inspections.filter(content__content_type__contains='text/html').count()

    def url_inspections_ftp_count(self):
        return self.url_inspections.filter(requested_url__startswith='ftp').count()

    def error_list(self):
        error_list = []
        for probe in self.probe_set.filter(errors__len__gt=0).only('errors'):
            error_list.extend(probe.errors)
        return error_list

    def error_count(self):
        return len(self.error_list())


class URLInspectionManager(hstore.HStoreManager):

    def create_from_response(self, resp, save_content=True):
        """
        Create a URLInspection object from a requests.Response
        """
        if isinstance(resp, Response):
            content_type = resp.headers.get('content-type', None)
            content = ResponseContent.objects.create(content_type=content_type)
            if save_content:
                content.binary = resp.content
                content.save()
            obj = self.create(content=content, url=resp.url, status_code=resp.status_code,
                              encoding=resp.encoding, reason=resp.reason)
            obj.requested_url = resp.history[0].url if len(resp.history) > 0 else resp.request.url
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
    content_type = models.CharField(max_length=120, blank=True, null=True)
    length = models.IntegerField(blank=True, null=True, editable=False)

    class Meta:
        verbose_name = 'ResponseContent'
        verbose_name_plural = 'ResponsesContents'

    def save(self, *args, **kwargs):
        self.length = len(self.binary) if self.binary else None
        super(ResponseContent, self).save(*args, **kwargs)

    def string(self):
        return str(self.binary)

    def __repr__(self):
        return '<ResponseContent: {0} bytes>'.format(self.length)

    def __str__(self):
        return self.__repr__()


class URLInspection(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.TextField(blank=True, null=True)  # We may get (and want to store) really long or invalid urls, so...
    requested_url = models.TextField()  # We may get (and want to store) really long or invalid urls, so...
    encoding = models.CharField(max_length=120, blank=True, null=True)
    apparent_encoding = models.CharField(max_length=120, blank=True, null=True)
    content = models.OneToOneField(ResponseContent, null=True, related_name='content_for', editable=False)
    history = hstore.ReferencesField(blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)
    status_code = models.IntegerField(max_length=3, blank=True, null=True)
    reason = models.CharField(blank=True, null=True, max_length=80, help_text='Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".')
    headers = hstore.DictionaryField(default=dictionary_default)
    timeout = models.BooleanField(default=False)
    probe = models.ForeignKey('Probe', null=True, blank=True, related_name='url_inspections')

    objects = URLInspectionManager()

    class Meta:
        verbose_name = 'URL Inspection'
        verbose_name_plural = 'URL Inspections'
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

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

    CABINET = 'C'
    INDEPENDENT = 'I'
    SUBAGENCY = 'S'
    OTHER = 'O'

    AGENCY_TYPE_CHOICES = (
        (CABINET, 'Cabinet'),
        (INDEPENDENT, 'Independent'),
        (SUBAGENCY, 'Sub-Agency'),
        (OTHER, 'Other/Unknown'),
    )

    name = models.CharField(max_length=100, unique=True)
    agency_type = models.CharField(max_length=1, choices=AGENCY_TYPE_CHOICES, default=OTHER)
    slug = models.SlugField(max_length=120, unique=True)
    url = models.URLField(unique=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = "agencies"
        ordering = ('agency_type', 'name')

    def save(self, *args, **kwargs):
        if self.slug is None or self.slug == '':
            self.slug = slugify(self.name)
        super(Agency, self).save(*args, **kwargs)

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

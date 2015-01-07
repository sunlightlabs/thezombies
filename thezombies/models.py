from requests import Response
from attrdict import AttrDict

from django.db import models
from django.db.models import Q
from django_hstore import hstore
from django_hstore.query import HStoreQuerySet
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


http_urls_q = Q(requested_url__startswith='http')
ftp_urls_q = Q(requested_url__startswith='ftp')


class URLInspectionQuerySet(HStoreQuerySet):

    def requested_urls_distinct(self):
        return self.order_by('requested_url', '-created_at').distinct('requested_url')

    def all_errors(self):
        """Status codes (400 and up)"""
        return self.filter(status_code__gte=400)

    def server_errors(self):
        """Status codes in the 500 range"""
        return self.filter(status_code__gte=500)

    def client_errors(self):
        """Status codes in the 400 range"""
        return self.filter(status_code__gte=400, status_code__lt=500)

    def not_found(self):
        return self.filter(status_code=404)

    def html_content(self):
        return self.filter(content__content_type__contains='text/html')

    def initial_urls(self):
        """Return URLs that aren't part of a redirect of some sort"""
        return self.filter(parent__isnull=True)

    def initial_urls_distinct(self):
        """Return URLs that aren't part of a redirect of some sort"""
        return self.filter(parent__isnull=True).requested_urls_distinct()

    def ftp_urls(self):
        return self.filter(ftp_urls_q).order_by('requested_url')

    def ftp_urls_distinct(self):
        return self.ftp_urls().requested_urls_distinct()

    def http_urls(self):
        return self.filter(http_urls_q).order_by('requested_url')

    def http_urls_distinct(self):
        return self.http_urls().requested_urls_distinct()

    def suspicious_urls(self):
        return self.exclude(http_urls_q | ftp_urls_q).order_by('requested_url')

    def suspicious_urls_distinct(self):
        return self.suspicious_urls().requested_urls_distinct()

    def responses_sans_content_type(self):
        return self.filter(parent__isnull=True, status_code__isnull=False).filter(content__content_type__isnull=True, status_code__lt=300)

    def sans_responses(self):
        return self.filter(status_code__isnull=True).order_by('requested_url')

    def sans_responses_distinct(self):
        return self.sans_responses().requested_urls_distinct()


class URLInspectionManager(hstore.HStoreManager):

    def get_queryset(self):
        return URLInspectionQuerySet(self.model, using=self._db)

    def create_from_response(self, resp, save_content=True):
        """
        Create a URLInspection object from a requests.Response or dictionary made from a requests.Response
        """
        if isinstance(resp, Response) or isinstance(resp, AttrDict):
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
            # if save_content:
            #     obj.apparent_encoding = resp.apparent_encoding
            for n, hist in enumerate(resp.history):
                histobj = self.create(requested_url=hist.request.url, url=hist.url,
                                      status_code=hist.status_code, encoding=hist.encoding, parent=obj)
                histobj.headers = dict(hist.headers)
                histobj.save()
                obj.history[str(n)] = histobj

            return obj
        else:
            raise TypeError(u'create_from_response expects a requests.Response object or a compatible dictionary')


class ProbeQuerySet(HStoreQuerySet):

    def json_probes(self):
        return self.filter(probe_type=Probe.JSON_PROBE)

    def principal_json_probes(self):
        """Provides JSON probes that aren't linked to any previous json probes"""
        return self.json_probes().filter(previous__isnull=False)

    def json_probes_sans_urls(self):
        json_probes_public = self.principal_json_probes().filter(initial__contains={u'accessLevel': u'public'})
        has_distribution_q = Q(initial__contains=['distribution'])
        has_accessURL_q = Q(initial__contains=['accessURL'])
        has_accessURL_badkey_q = Q(initial__contains=['accessUrl'])
        has_webservice_q = Q(initial__contains=['webService'])
        return json_probes_public.exclude(has_distribution_q | has_accessURL_q | has_accessURL_badkey_q | has_webservice_q)

    def url_probes(self):
        return self.filter(probe_type=Probe.URL_PROBE)

    def url_probes_invalid_url(self):
        return self.url_probes().filter(result__contains={'valid_url': 'false'})

    def validation_probes(self):
        return self.filter(probe_type=Probe.VALIDATION_PROBE)


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

    objects = ProbeQuerySet.as_manager()

    def __repr__(self):
        return '<{0}: {1}>'.format(self.get_probe_type_display(), self.id)

    def __str__(self):
        return self.__repr__()

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def error_count(self):
        return len(self.errors)

    def get_absolute_url(self):
        return reverse('probe-detail', kwargs={'pk': str(self.pk)})


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
        return u'<Audit({audit_type}): {identifier}>'.format(identifier=self.id,
                                                             audit_type=self.get_audit_type_display())

    def __str__(self):
        return u'{audit_type} for {identifier}'.format(audit_type=self.get_audit_type_display(),
                                                       identifier=self.agency)

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def get_absolute_url(self):
        return reverse('audit-detail', kwargs={'pk': str(self.pk)})

    # @property
    # def url_inspections(self):
    #     return URLInspection.objects.filter(probe__in=self.probe_set.all())

    def error_list(self):
        error_list = []
        for probe in self.probe_set.filter(errors__len__gt=0).only('errors'):
            error_list.extend(probe.errors)
        return error_list

    def error_count(self):
        return len(self.error_list())


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
        return u'<ResponseContent: {0} bytes>'.format(self.length)

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

    objects = URLInspectionManager.from_queryset(URLInspectionQuerySet)()

    class Meta:
        verbose_name = 'URL Inspection'
        verbose_name_plural = 'URL Inspections'
        get_latest_by = 'created_at'
        ordering = ('-created_at', 'requested_url')

    def __repr__(self):
        return '<URLInspection: {0} : {1}>'.format(self.requested_url, self.status_code)

    def __str__(self):
        return self.__repr__()


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
        return u'<Agency: {0}>'.format(self.name)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('agency-detail', kwargs={'slug': self.slug})

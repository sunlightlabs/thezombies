from django.shortcuts import get_object_or_404
from django.http import Http404
from django.views.generic import ListView, DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.base import RedirectView
from django.views.generic.dates import DayArchiveView, MonthArchiveView, YearArchiveView

from thezombies.models import (Agency, Audit, Probe, URLInspection)


class HomeView(RedirectView):
    url = '/audits/'
    pattern_name = 'audit-list'


class AgencyList(ListView):
    model = Agency
    template_name = 'agency_list.html'


class AgencyView(DetailView):
    model = Agency
    template_name = 'agency_detail.html'


class AuditDayArchiveView(DayArchiveView):
    queryset = Audit.objects.all()
    allow_empty = True
    paginate_by = 50
    date_field = "created_at"
    month_format = "%m"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditMonthArchiveView(MonthArchiveView):
    queryset = Audit.objects.all()
    allow_empty = True
    paginate_by = 50
    date_field = "created_at"
    month_format = "%m"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditYearArchiveView(YearArchiveView):
    queryset = Audit.objects.all()
    allow_empty = True
    paginate_by = 50
    date_field = "created_at"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditListView(ListView):
    model = Audit
    paginate_by = 50
    template_name = 'audits_list.html'

    def get_queryset(self, **kwargs):
        audit_filter_kwargs = {}
        self.audit_type_string = self.kwargs.get('audit_type', None)
        if self.audit_type_string:
            if self.audit_type_string == 'generic':
                audit_filter_kwargs['audit_type'] = Audit.GENERIC_AUDIT
            elif self.audit_type_string == 'validation':
                audit_filter_kwargs['audit_type'] = Audit.DATA_CATALOG_VALIDATION
            elif self.audit_type_string == 'crawl':
                audit_filter_kwargs['audit_type'] = Audit.DATA_CATALOG_CRAWL
            else:
                raise Http404
        self.audit_list = Audit.objects.filter(**audit_filter_kwargs).prefetch_related('agency')
        return self.audit_list

    def get_context_data(self, **kwargs):
        context = super(AuditListView, self).get_context_data(**kwargs)
        context['audit_type'] = self.audit_type_string
        return context


AUDIT_TYPE_TEMPLATES = (
    (Audit.GENERIC_AUDIT, 'audit_detail.html'),
    (Audit.DATA_CATALOG_CRAWL, 'audit_crawl_detail.html'),
    (Audit.DATA_CATALOG_VALIDATION, 'audit_validation_detail.html'),
)


class AuditView(SingleObjectMixin, ListView):
    paginate_by = 20
    template_name = 'audit_detail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Audit.objects.all())
        return super(AuditView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AuditView, self).get_context_data(**kwargs)
        context['audit'] = self.object
        return context

    def get_queryset(self):
        url_inspections = URLInspection.objects.filter(probe__in=self.object.probe_set.all())
        # url_inspections.prefetch_related('content__content_type').defer('content__binary')
        # url_inspections.defer('probe__initial', 'probe__result')
        return url_inspections

    def get_template_names(self):
        template_names = super(AuditView, self).get_template_names()
        template_choices = dict(AUDIT_TYPE_TEMPLATES)
        template_addition = template_choices.get(self.object.audit_type, None) if self.object else None
        if template_addition:
            template_names.insert(0, template_addition)
        return template_names


class AuditURLList(ListView):
    paginate_by = 50
    template_name = 'audit_url_list.html'

    def get_queryset(self):
        self.audit = get_object_or_404(Audit, pk=self.kwargs.get('pk'))
        # probe_set = self.audit.probe_set.all()
        # probe_set.only('content__content_type', 'probe__errors', 'info')
        url_inspections = URLInspection.objects.filter(probe__in=probe_set)
        return url_inspections

    def get_context_data(self, **kwargs):
        context = super(AuditURLList, self).get_context_data(**kwargs)
        context['audit'] = self.audit
        return context


class ProbeView(DetailView):
    model = Probe
    template_name = "probe_detail.html"

from django.shortcuts import get_object_or_404, get_list_or_404
from django.views.generic import ListView, DetailView
from django.views.generic.dates import DayArchiveView, MonthArchiveView, YearArchiveView

from thezombies.models import (Agency, Audit)


class AgencyList(ListView):
    model = Agency
    template_name = 'agency_list.html'


class AgencyView(DetailView):
    model = Agency
    template_name = 'agency_detail.html'


class AuditList(ListView):
    model = Audit
    paginate_by = 50
    template_name = 'audits_list.html'


class AuditDayArchiveView(DayArchiveView):
    queryset = Audit.objects.all()
    date_field = "created_at"
    month_format = "%m"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditMonthArchiveView(MonthArchiveView):
    queryset = Audit.objects.all()
    date_field = "created_at"
    month_format = "%m"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditYearArchiveView(YearArchiveView):
    queryset = Audit.objects.all()
    date_field = "created_at"
    make_object_list = True
    template_name = 'audits_list.html'


class AuditOfTypeList(ListView):
    model = Audit
    paginate_by = 50
    template_name = 'audits_list.html'

    def get_queryset(self, **kwargs):
        audit_type_str = self.kwargs.get('audit_type', None)
        audit_type = None
        if audit_type_str == 'generic':
            audit_type = Audit.GENERIC_AUDIT
        elif audit_type_str == 'validation':
            audit_type = Audit.DATA_CATALOG_VALIDATION
        elif audit_type_str == 'crawl':
            audit_type = Audit.DATA_CATALOG_CRAWL
        self.audit_list = get_list_or_404(Audit, audit_type=audit_type)
        self.audit_type_string = audit_type_str
        return self.audit_list

    def get_context_data(self, **kwargs):
        context = super(AuditOfTypeList, self).get_context_data(**kwargs)
        context['audit_type'] = self.audit_type_string
        return context


class AuditView(DetailView):
    model = Audit
    template_name = 'audit_detail.html'


class AuditURLList(ListView):
    paginate_by = 50
    template_name = 'audit_url_list.html'

    def get_queryset(self):
        self.audit = get_object_or_404(Audit, pk=self.kwargs.get('pk'))
        return self.audit.url_inspections

    def get_context_data(self, **kwargs):
        context = super(AuditURLList, self).get_context_data(**kwargs)
        context['audit'] = self.audit
        return context

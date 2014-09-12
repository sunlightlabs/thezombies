from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

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

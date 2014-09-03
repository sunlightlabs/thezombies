from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

from thezombies.models import (Agency, Report, URLResponse)


class AgencyList(ListView):
    model = Agency
    context_object_name = 'agencies'
    template_name = 'agency_list.html'

class AgencyView(DetailView):
    model = Agency
    context_object_name = 'agency'
    template_name = 'agency_detail.html'

class ReportList(ListView):
    model = Report
    context_object_name = 'reports'
    paginate_by = 50
    template_name = 'reports_list.html'

class ReportView(DetailView):
    model = Report
    context_object_name = 'report'
    template_name = 'report_detail.html'

class ReportURLList(ListView):
    context_object_name = 'responses'
    paginate_by = 50
    template_name = 'report_url_list.html'

    def get_queryset(self):
        self.report = get_object_or_404(Report, pk=self.kwargs.get('pk'))
        return URLResponse.objects.filter(report=self.report)

    def get_context_data(self, **kwargs):
        context = super(ReportURLList, self).get_context_data(**kwargs)
        context['report'] = self.report
        return context

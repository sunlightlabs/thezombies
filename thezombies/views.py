from django.views.generic import ListView, DetailView

from thezombies.models import (Agency, Report)


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

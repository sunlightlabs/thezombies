from django.conf.urls import patterns, include, url
from django.contrib import admin

from thezombies.views import (AgencyList, AgencyView, ReportList, ReportView)

urlpatterns = patterns('',
    # Examples:
    url(r'^$', AgencyList.as_view(), name='agency-list'),
    url(r'^agency/(?P<slug>[\w\-]+)$', AgencyView.as_view(), name='agency-detail'),
    url(r'^reports/$', ReportList.as_view(), name='reports-list'),
    url(r'^reports/(?P<pk>\d+)$', ReportView.as_view(), name='report-detail'),

    url(r'^admin/', include(admin.site.urls)),
)

from django.conf.urls import patterns, include, url
from django.contrib import admin

from thezombies.views import (AgencyList, AgencyView, ReportList, ReportView, ReportURLList)

urlpatterns = patterns('',
    # Examples:
    url(r'^$', AgencyList.as_view(), name='agency-list'),
    url(r'^agency/(?P<slug>[\w\-]+)/$', AgencyView.as_view(), name='agency-detail'),
    url(r'^reports/$', ReportList.as_view(), name='reports-list'),
    url(r'^reports/(?P<pk>\d+)/$', ReportView.as_view(), name='report-detail'),
    url(r'^reports/(?P<pk>\d+)/urls$', ReportURLList.as_view(), name='report-url-list'),

    url(r'^admin/', include(admin.site.urls)),
)

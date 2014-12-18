from django.conf.urls import patterns, include, url
from django.contrib import admin

from thezombies.views import (HomeView, AgencyList, AgencyView, AuditListView, AuditView, AuditURLList,
                              AuditDayArchiveView, AuditMonthArchiveView, AuditYearArchiveView, ProbeView)

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^agency/$', AgencyList.as_view(), name='agency-list'),
    url(r'^agency/(?P<slug>[\w\-]+)/$', AgencyView.as_view(), name='agency-detail'),
    url(r'^audits/$', AuditListView.as_view(), name='audits-list'),
    url(r'^audits/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d+)/$', AuditDayArchiveView.as_view(), name='audits-list-day'),
    url(r'^audits/(?P<year>\d{4})/(?P<month>\d{2})/$', AuditMonthArchiveView.as_view(), name='audits-list-month'),
    url(r'^audits/(?P<year>\d{4})/$', AuditYearArchiveView.as_view(), name='audits-list-year'),
    url(r'^audits/(?P<pk>\d+)/$', AuditView.as_view(), name='audit-detail'),
    url(r'^audits/(?P<pk>\d+)/urls/$', AuditURLList.as_view(), name='audit-url-list'),
    url(r'^audits/(?P<audit_type>\w+)/$', AuditListView.as_view(), name='audits-list-filtered'),
    url(r'^probes/(?P<pk>\d+)/$', ProbeView.as_view(), name='probe-detail'),

    url(r'^admin/', include(admin.site.urls)),
)

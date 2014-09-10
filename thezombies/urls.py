from django.conf.urls import patterns, include, url
from django.contrib import admin

from thezombies.views import (AgencyList, AgencyView, AuditList, AuditView, AuditURLList)

urlpatterns = patterns('',
    url(r'^$', AgencyList.as_view(), name='agency-list'),
    url(r'^agency/(?P<slug>[\w\-]+)/$', AgencyView.as_view(), name='agency-detail'),
    url(r'^audits/$', AuditList.as_view(), name='audits-list'),
    url(r'^audits/(?P<pk>\d+)/$', AuditView.as_view(), name='audit-detail'),
    url(r'^audits/(?P<pk>\d+)/urls/$', AuditURLList.as_view(), name='audit-url-list'),

    url(r'^admin/', include(admin.site.urls)),
)

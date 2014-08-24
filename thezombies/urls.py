from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'thezombies.views.home', name='home'),
    url(r'^agency/(?P<slug>[\w\-]+)$', 'thezombies.views.agency', name='agency'),

    url(r'^admin/', include(admin.site.urls)),
)

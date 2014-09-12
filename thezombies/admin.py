from django.contrib import admin
from thezombies.models import (Agency, Audit, URLInspection, Probe)


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url', 'parent')
    list_filter = ('agency_type',)


class ProbeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'probe_type', 'previous', 'created_at')
    list_filter = ('probe_type',)


class AuditAdmin(admin.ModelAdmin):
    list_display = ('agency', 'audit_type', 'created_at')
    list_filter = ('audit_type',)
    search_fields = ('agency',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('url_inspections_count', 'url_inspections_failure_count', 'url_inspections_404_count',
                       'url_inspections_html_count', 'created_at', 'updated_at', 'messages')
    fieldsets = (
        (None, {
            'fields': (('agency', 'audit_type'), ('created_at', 'updated_at'), 'notes')
        }),
        ('Messages', {
            'fields': ('messages',)
        }),
        ('URL Inspections', {
            'fields': ('url_inspections_count', 'url_inspections_failure_count', 'url_inspections_404_count', 'url_inspections_html_count'),
            'classes': ('wide',),
        }),
    )

    def display_name(self, obj):
        name = 'Audit for {0}'.format(obj.agency.name)
        if obj.url:
            name = '{0} on {1}'.format(name, obj.url)
        return name


class URLInspectionAdmin(admin.ModelAdmin):
    list_display = ('requested_url', 'url', 'status_code', 'created_at')
    list_filter = ('status_code',)
    search_fields = ('requested_url', 'url')
    exclude = ('content',)
    ordering = ('-created_at',)
    readonly_fields = ('requested_url', 'url')

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Audit, AuditAdmin)
admin.site.register(Probe, ProbeAdmin)
admin.site.register(URLInspection, URLInspectionAdmin)

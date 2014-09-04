from django.contrib import admin
from thezombies.models import Agency, Report, URLInspection


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('agency', 'report_type', 'url', 'created_at')
    list_filter = ('report_type',)
    search_fields = ('agency', 'url')
    ordering =  ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('inspections_total_count', 'inspections_failure_count', 'inspections_404_count',
                        'inspections_html_count', 'created_at', 'updated_at', 'messages')
    fieldsets = (
        (None, {
                'fields': (('agency', 'report_type'), ('created_at', 'updated_at'), 'notes', 'url')
            }),
        ('Messages', {
                'fields': ('messages',)
            }),
        ('URL Inspections', {
                'fields': ('inspections_total_count', 'inspections_failure_count', 'inspections_404_count', 'inspections_html_count'),
                'classes': ('wide',),
            }),
    )

    def display_name(self, obj):
        name = 'Report for {0}'.format(obj.agency.name)
        if obj.url:
            name = '{0} on {1}'.format(name, obj.url)
        return name

class URLInspectionAdmin(admin.ModelAdmin):
    list_display = ('requested_url', 'url', 'status_code', 'report', 'created_at')
    list_filter = ('status_code',)
    search_fields = ('requested_url', 'url')
    exclude = ('content',)
    ordering =  ('-created_at',)
    readonly_fields = ('requested_url', 'url', 'info', 'errors')

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(URLInspection, URLInspectionAdmin)


from django.contrib import admin
from thezombies.models import Agency, Report, URLResponse


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url')

class ResponseInline(admin.TabularInline):
    model = URLResponse
    max_num = 10
    extra = 0
    can_delete = False
    exclude = ('headers', 'content')
    readonly_fields = ('url', 'requested_url', 'encoding', 'status_code', 'reason')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('agency', 'report_type', 'url', 'created_at')
    list_filter = ('report_type',)
    search_fields = ('agency', 'url')
    ordering =  ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('responses_total_count', 'responses_failure_count', 'responses_404_count',
                        'responses_html_count', 'created_at', 'updated_at', 'messages')
    fieldsets = (
        (None, {
                'fields': (('agency', 'report_type'), ('created_at', 'updated_at'), 'notes', 'url')
            }),
        ('Messages', {
                'fields': ('messages',)
            }),
        ('Responses', {
                'fields': ('responses_total_count', 'responses_failure_count', 'responses_404_count', 'responses_html_count'),
                'classes': ('wide',),
            }),
    )

    def display_name(self, obj):
        name = 'Report for {0}'.format(obj.agency.name)
        if obj.url:
            name = '{0} on {1}'.format(name, obj.url)
        return name

class URLResponseAdmin(admin.ModelAdmin):
    list_display = ('url', 'status_code', 'requested_url', 'report', 'created_at')
    list_filter = ('status_code',)
    search_fields = ('url', 'requested_url')
    exclude = ('content',)
    ordering =  ('-created_at',)
    readonly_fields = ('info', 'errors',)

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(URLResponse, URLResponseAdmin)


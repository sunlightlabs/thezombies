from django.contrib import admin
from thezombies.models import Agency, Report, RequestsResponse


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url')

class ResponseInline(admin.TabularInline):
    model = RequestsResponse
    exclude = ('headers', 'content')
    readonly_fields = ('url', 'requested_url', 'content',
        'encoding', 'apparent_encoding', 'status_code', 'reason',
        'content_type', 'content_length')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'url', 'agency', 'created_at')
    list_filter = ('agency',)
    ordering =  ('-created_at',)
    inlines = (ResponseInline,)

    def display_name(self, obj):
        name = 'Report for {0}'.format(obj.agency.name)
        if obj.url:
            name = '{0} on {1}'.format(name, obj.url)
        return name

class RequestsResponseAdmin(admin.ModelAdmin):
    list_display = ('url', 'status_code', 'requested_url', 'content_type', 'report', 'created_at')
    list_filter = ('report',)
    ordering =  ('-created_at',)

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(RequestsResponse, RequestsResponseAdmin)


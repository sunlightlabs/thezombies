from django.contrib import admin
from thezombies.models import Agency, Report, URLResponse


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url')

class ResponseInline(admin.TabularInline):
    model = URLResponse
    exclude = ('headers', 'content')
    readonly_fields = ('url', 'requested_url', 'encoding', 'apparent_encoding',
        'status_code', 'reason')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('agency', 'url', 'created_at')
    search_fields = ('agency', 'url')
    ordering =  ('-created_at',)
    readonly_fields = ('info', 'errors',)
    inlines = (ResponseInline,)

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

admin.site.register(Agency, AgencyAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(URLResponse, URLResponseAdmin)


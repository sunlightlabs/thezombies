from django.contrib import admin
from thezombies.models import Agency, Report


class AgencyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'agency_type', 'url')

class ReportAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'agency', 'url', 'created_at')
    list_filter = ('agency',)
    ordering =  ('-created_at',)

    def display_name(self, obj):
        return 'Report on resource for {0}'.format(obj.agency.name)


admin.site.register(Agency, AgencyAdmin)
admin.site.register(Report, ReportAdmin)


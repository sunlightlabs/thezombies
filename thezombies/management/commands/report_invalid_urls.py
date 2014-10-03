from __future__ import division
from django.core.management.base import BaseCommand
from django.utils import timezone
from thezombies.models import (Agency, Probe)

REPORT_DATE_FORMATTER = u"{:%Y-%m-%d %I:%M%p %Z}\n"


class Command(BaseCommand):
    """Show some information on invalid/bad urls"""

    def handle(self, *args, **kwargs):
        agency_list = Agency.objects.all()
        self.stdout.write(u"# Invalid URL Report\n")
        report_date = REPORT_DATE_FORMATTER.format(timezone.localtime(timezone.now()))
        self.stdout.write(u"Report generated: {0}\n\n".format(report_date))
        for agency in agency_list:
            self.stdout.write('## Agency: {0}\n\n'.format(agency.name))
            probe_list = Probe.objects.filter(audit__agency=agency).url_probes_invalid_url()
            if probe_list.count() == 0:
                self.stdout.write('None!\n\n')
            else:
                self.stdout.write('URL Count: {0}\n\n'.format(probe_list.count()))
            for probe in probe_list:
                self.stdout.write('* {0}'.format(probe.result.get('initial_url', '???')))
            if probe_list.count() > 0:
                self.stdout.write('\n')

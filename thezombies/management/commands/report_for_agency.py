from __future__ import division
from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from thezombies.models import (Agency, Audit, Probe)

REPORT_DATE_FORMATTER = u"{:%Y-%m-%d %I:%M%p %Z}\n"


class Command(BaseCommand):
    """Report on agency's data catalog"""
    args = '<agency_id ...>'

    def handle(self, *args, **options):
        agency_id = args[0]
        if agency_id:
            try:
                agency = Agency.objects.get(id=agency_id)
            except Agency.DoesNotExist:
                raise CommandError("Agency with id {} does not exist".format(agency_id))
            self.stdout.write("# Report for {agency}\n\n".format(agency=agency))
            report_date = REPORT_DATE_FORMATTER.format(timezone.localtime(timezone.now()))
            self.stdout.write(u"Report generated: {0}\n".format(report_date))
            validation_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_VALIDATION).latest()
            self.stdout.write('## Catalog Validation\n\n')
            self.stdout.write('Ran on {0}\n'.format(REPORT_DATE_FORMATTER.format(validation_audit.created_at)))
            validation_probe = validation_audit.probe_set.filter(probe_type=Probe.VALIDATION_PROBE).first()
            is_valid = validation_probe.result.get(u'is_valid_data_catalog', 'Unknown')
            self.stdout.write('Valid catalog: **{}**\n\n'.format(is_valid.title()))
            self.stdout.write('### Errors\n\n')
            if validation_audit.error_count() == 0:
                self.stdout.write('No errors encountered\n')
            else:
                error_counts = Counter([e.partition(':')[0] for e in validation_audit.error_list()])
                for el, count in error_counts.items():
                    self.stdout.write('- {0:,d} of type *{1}*\n'.format(count, el))
            self.stdout.write('\n')
            crawl_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_CRAWL).latest()
            self.stdout.write('## URL Inspections\n\n')
            self.stdout.write('Ran on {0}\n'.format(REPORT_DATE_FORMATTER.format(crawl_audit.created_at)))
            num_urls_found = crawl_audit.url_inspections.initial_urls_distinct().count()
            self.stdout.write('Inspected **{0:,d}** URLS\n\n'.format(num_urls_found))
            http_urls_distinct = crawl_audit.url_inspections.http_urls_distinct().count()
            self.stdout.write('- **{0:,}** distinct HTTP URLS\n'.format(http_urls_distinct))
            ftp_urls_distinct = crawl_audit.url_inspections.ftp_urls_distinct().count()
            self.stdout.write('- **{0:,}** distinct FTP URLS\n'.format(ftp_urls_distinct))
            suspicious_urls_distinct = crawl_audit.url_inspections.suspicious_urls_distinct()
            self.stdout.write('- **{0:,}** suspicious (not http or ftp) URLS\n'.format(suspicious_urls_distinct.count()))
            self.stdout.write('\n### Suspicious (not http or ftp) URLS\n\n'.format(suspicious_urls_distinct.count()))
            for insp in suspicious_urls_distinct:
                self.stdout.write('- {0}\n'.format(insp.requested_url))
            self.stdout.write('\n')
            not_found_urls = crawl_audit.url_inspections.not_found()
            self.stdout.write('### 404 (Not Found) responses\n\n')
            self.stdout.write('{0:,d} URLs returned an error of "404 Not found"\n'.format(not_found_urls.count()))
            for insp in not_found_urls:
                self.stdout.write('- {0}\n'.format(insp.requested_url))
            self.stdout.write('\n')

from __future__ import division
from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from thezombies.models import (Agency, Audit, Probe)
from thezombies.utils import datetime_string


class Command(BaseCommand):
    """Report on agency's data catalog"""
    args = '<agency_id ...>'

    def handle(self, *args, **options):
        if len(args) > 0:
            agency_id = args[0]
            if agency_id:
                try:
                    agency = Agency.objects.get(id=agency_id)
                except Agency.DoesNotExist:
                    raise CommandError(u"Agency with id {} does not exist".format(agency_id))
                report_lines = []
                report_lines.append(u"# Report for {agency}\n\n".format(agency=agency))
                report_date = datetime_string()
                report_lines.append(u"Report generated: {0}\n\n".format(report_date))
                validation_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_VALIDATION).latest()
                report_lines.append(u'## Catalog Validation\n\n')
                report_lines.append(u'Ran on {0}\n\n'.format(datetime_string(validation_audit.created_at)))
                validation_probe = validation_audit.probe_set.filter(probe_type=Probe.VALIDATION_PROBE).first()
                is_valid = validation_probe.result.get(u'is_valid_data_catalog', 'Unknown')
                report_lines.append(u'Valid catalog: **{}**\n\n'.format(is_valid.title()))
                report_lines.append(u'### Errors\n\n')
                if validation_audit.error_count() == 0:
                    report_lines.append(u'No errors encountered\n')
                else:
                    error_counts = Counter([e.partition(u':')[0] for e in validation_audit.error_list()])
                    for el, count in error_counts.items():
                        report_lines.append(u'- {0:,d} of type *{1}*\n'.format(count, el))
                report_lines.append(u'\n')
                crawl_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_CRAWL).latest()
                report_lines.append(u'## Catalog Listing\n\n')
                catalog_item_count = crawl_audit.probe_set.json_probes().count()
                report_lines.append(u'**{0:,d}** datasets listed\n\n'.format(catalog_item_count))
                report_lines.append(u'## URL Inspections\n\n')
                report_lines.append(u'Ran on {0}\n\n'.format(datetime_string(crawl_audit.created_at)))
                num_urls_found = crawl_audit.url_inspections.initial_urls_distinct().count()
                report_lines.append(u'Inspected **{0:,d}** URLS\n\n'.format(num_urls_found))
                http_urls_distinct = crawl_audit.url_inspections.http_urls_distinct().count()
                report_lines.append(u'- **{0:,}** distinct HTTP URLS\n'.format(http_urls_distinct))
                ftp_urls_distinct = crawl_audit.url_inspections.ftp_urls_distinct().count()
                report_lines.append(u'- **{0:,}** distinct FTP URLS\n'.format(ftp_urls_distinct))
                suspicious_urls_distinct = crawl_audit.url_inspections.suspicious_urls_distinct()
                report_lines.append(u'- **{0:,}** suspicious (not http or ftp) URLS\n'.format(suspicious_urls_distinct.count()))
                report_lines.append(u'\n### Suspicious (not http or ftp) URLS\n\n'.format(suspicious_urls_distinct.count()))
                if suspicious_urls_distinct.count() == 0:
                    report_lines.append(u'No suspicious urls discovered.\n')
                else:
                    for insp in suspicious_urls_distinct:
                        report_lines.append(u'- {0}\n'.format(insp.requested_url.strip()))
                report_lines.append(u'\n')
                not_found_urls = crawl_audit.url_inspections.not_found()
                report_lines.append(u'### 404 (Not Found) responses\n\n')
                report_lines.append(u'**{0:,d}** URLs returned an error of "404 Not found"\n\n'.format(not_found_urls.count()))
                for insp in not_found_urls:
                    dataset_title = insp.probe.previous.initial.get(u'title', 'No title for dataset')
                    report_lines.append(u'- *{title}*\n<{url}>\n\n'.format(title=dataset_title, url=insp.requested_url))
                report_lines.append(u'\n')
                sans_responses_urls = crawl_audit.url_inspections.sans_responses_distinct()
                report_lines.append(u'### URLs that did not respond\n\n')
                report_lines.append(u'**{0:,d}** URLs returned an error of "404 Not found"\n\n'.format(sans_responses_urls.count()))
                for insp in sans_responses_urls:
                    dataset_title = insp.probe.previous.initial.get(u'title', 'No title for dataset')
                    errors = u"\n".join(insp.probe.errors)[:280]
                    report_lines.append(u'- *{title}*\n<{url}>\n**{errors}**\n\n'.format(title=dataset_title, url=insp.requested_url, errors=errors))
                report_lines.append(u'\n')
                self.stdout.write(u''.join(report_lines))
        else:
            self.stdout.write(u'Please provide an agency id:\n')
            agency_list = u'\n'.join(['{0:2d}: {1}'.format(a.id, a.name) for a in Agency.objects.all()])
            self.stdout.write(agency_list)
            self.stdout.write(u'\n')

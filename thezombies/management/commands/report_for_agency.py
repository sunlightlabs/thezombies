from __future__ import division
from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from thezombies.models import (Agency, Audit, Probe, URLInspection, ftp_urls_q)
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
                report_date = datetime_string()
                validation_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_VALIDATION).latest()
                validation_probe = validation_audit.probe_set.filter(probe_type=Probe.VALIDATION_PROBE).first()
                is_valid = Probe.objects.filter(id=validation_probe.id).hpeek(attr=u'result', key=u'is_valid_data_catalog')
                crawl_audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_CRAWL).latest()
                catalog_item_count = crawl_audit.probe_set.json_probes().count()
                url_inspections = URLInspection.objects.filter(probe__in=crawl_audit.probe_set.all())
                num_urls_found = url_inspections.initial_urls_distinct().count()
                http_urls_distinct = url_inspections.http_urls_distinct().count()
                ftp_urls_distinct = url_inspections.ftp_urls_distinct()
                ftp_urls_pct = ftp_urls_distinct.count()/num_urls_found
                suspicious_urls_distinct = url_inspections.suspicious_urls_distinct()
                suspicious_urls_pct = suspicious_urls_distinct.count()/num_urls_found
                not_found_urls = url_inspections.not_found()
                not_found_pct = not_found_urls.count()/num_urls_found
                sans_responses_urls = url_inspections.exclude(ftp_urls_q).sans_responses_distinct()
                report_lines = []
                report_lines.append(u"# Report for {agency}\n\n".format(agency=agency))
                report_lines.append(u"Report generated: {0}\n\n".format(report_date))
                report_lines.append(u'## Catalog Validation\n\n')
                report_lines.append(u'Ran on {0}\n\n'.format(datetime_string(validation_audit.created_at)))
                report_lines.append(u'Valid catalog: **{}**\n\n'.format(is_valid.title()))
                report_lines.append(u'### Errors\n\n')
                if validation_audit.error_count() == 0:
                    report_lines.append(u'No errors encountered\n')
                else:
                    error_counts = Counter([e.partition(u':')[0] for e in validation_audit.error_list()])
                    for el, count in error_counts.items():
                        report_lines.append(u'- {0:,d} of type *{1}*\n'.format(count, el))
                report_lines.append(u'\n')
                report_lines.append(u'## Catalog Listing\n\n')
                report_lines.append(u'**{0:,d}** datasets listed\n\n'.format(catalog_item_count))
                report_lines.append(u'## URL Inspections\n\n')
                report_lines.append(u'Ran on {0}\n\n'.format(datetime_string(crawl_audit.created_at)))
                report_lines.append(u'Inspected **{0:,d}** URLS\n\n'.format(num_urls_found))
                report_lines.append(u'- **{0:,}** distinct HTTP URLS\n'.format(http_urls_distinct))
                report_lines.append(u'- **{0:,}** distinct FTP URLS ({1:.2%})\n'.format(ftp_urls_distinct.count(), ftp_urls_pct))
                report_lines.append(u'- **{0:,}** suspicious (not http or ftp) URLS ({1:.2%})\n'.format(suspicious_urls_distinct.count(), suspicious_urls_pct))
                report_lines.append(u'- **{0:,}** 404 "Not Found" responses ({1:.2%})\n'.format(not_found_urls.count(), not_found_pct))
                report_lines.append(u'\n### Suspicious (not http or ftp) URLS\n\n'.format(suspicious_urls_distinct.count()))
                if suspicious_urls_distinct.count() == 0:
                    report_lines.append(u'No suspicious urls discovered.\n')
                else:
                    for insp in suspicious_urls_distinct:
                        report_lines.append(u'- {0}\n'.format(insp.requested_url.strip()))
                report_lines.append(u'\n')
                report_lines.append(u'### 404 "Not Found" responses\n\n')
                report_lines.append(u'**{0:,d}** URLs returned an error of "404 Not found"\n\n'.format(not_found_urls.count()))
                for insp in not_found_urls:
                    dataset_title = Probe.objects.filter(id=insp.probe.previous.id).hpeek(attr=u'initial', key=u'title')
                    report_lines.append(u'- *{title}*\n<{url}>\n\n'.format(title=dataset_title, url=insp.requested_url))
                report_lines.append(u'\n')
                report_lines.append(u'### URLs that did not respond\n\n')
                report_lines.append(u'**{0:,d}** URLs where there was no response (or another error occurred\n\n'.format(sans_responses_urls.count()))
                for insp in sans_responses_urls:
                    dataset_title = Probe.objects.filter(id=insp.probe.previous.id).hpeek(attr=u'initial', key=u'title')
                    errors = u"\n".join(insp.probe.errors)[:280]
                    report_lines.append(u'- *{title}*\n<{url}>\n**{errors}**\n\n'.format(title=dataset_title, url=insp.requested_url, errors=errors))
                report_lines.append(u'\n')
                self.stdout.write(u''.join(report_lines))
        else:
            self.stdout.write(u'Please provide an agency id:\n')
            agency_list = u'\n'.join(['{0:2d}: {1}'.format(a.id, a.name) for a in Agency.objects.all()])
            self.stdout.write(agency_list)
            self.stdout.write(u'\n')

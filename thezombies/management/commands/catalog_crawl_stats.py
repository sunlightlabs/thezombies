from __future__ import division
from django.core.management.base import BaseCommand
from django.utils import timezone
from thezombies.models import (Audit, Agency, Probe)
from optparse import make_option

REPORT_DATE_FORMATTER = u"{:%Y-%m-%d %I:%M%p %Z}\n"


class Command(BaseCommand):
    """Report stats on data catalog crawl audits."""
    args = u'None'
    help = u'Report stats on data catalog crawl audits'

    option_list = BaseCommand.option_list + (
        make_option('--show-missing',
                    action='store_true',
                    dest='show-missing',
                    default=False,
                    help='Show a message for Agencies missing a data catalog crawl'),
        make_option('--bad-urls',
                    action='store_true',
                    dest='bad-urls',
                    default=False,
                    help='Show the possibly bad urls'),
    )

    def handle(self, *args, **options):
        agency_list = Agency.objects.all()
        for agency in agency_list:
            try:
                audit = Audit.objects.filter(agency=agency, audit_type=Audit.DATA_CATALOG_CRAWL).latest()
                self.stdout.write(u"# Data Catalog Crawl Report\n")
                report_date = REPORT_DATE_FORMATTER.format(timezone.localtime(timezone.now()))
                self.stdout.write(u"Report generated: {0}\n\n".format(report_date))
                self.stdout.write(u"## {0}".format(audit.agency.name))
                date_str = REPORT_DATE_FORMATTER.format(timezone.localtime(audit.updated_at))
                num_urls_visited = audit.url_inspections.filter(parent__isnull=True).count()
                insp_list = audit.url_inspections.filter(content__isnull=False)
                errored_inspections = insp_list.server_errors()
                not_found = insp_list.not_found().count()
                typeless_inspections = audit.url_inspections.responses_sans_content_type()
                ftp_inspections = typeless_inspections.ftp_urls_distinct()
                typeless_http_inspections = typeless_inspections.http_urls_distinct()
                other_typeless_inspections = typeless_inspections.exclude(id__in=ftp_inspections).exclude(id__in=typeless_http_inspections)
                sans_data_urls = audit.probe_set.json_probes_sans_urls().filter(initial__contains={u'accessLevel': u'public'})
                self.stdout.write(u"\nUpdated: {0}\n".format(date_str))
                self.stdout.write(u"| Errors | Entries without URLs | URLs inspected | Not Found | Server Errors | URLs no content-type | FTP URLs | Possibly Invalid URLs |")
                self.stdout.write(u"| ------ | -------------------- | -------------- | --------- | ----------- | -------------------- | -------- | --------------------- |")
                stats_row = u"| {errors:6,d} | {sans_urls: >14,d} | {inspected: >14,d} | {not_found: >14,d} | {errored_inspections: >14,d} | {typeless:20,d} | {ftp:8,d} | {invalid:21,d} |".format(
                            errors=audit.error_count(), inspected=num_urls_visited, typeless=typeless_http_inspections.count(),
                            ftp=ftp_inspections.count(), invalid=other_typeless_inspections.count(), sans_urls=sans_data_urls.count(),
                            errored_inspections=errored_inspections.count(), not_found=not_found)
                self.stdout.write(stats_row)
                selector = u'content__content_type'
                insp_content_types = insp_list.select_related(selector).order_by(selector).distinct(selector).only(selector)
                content_types = list(set([x.content.content_type.split(';')[0] for x in insp_content_types if x.content.content_type]))
                if len(content_types) > 0:
                    self.stdout.write(u"\n### Content Types\n\n")
                    self.stdout.write(u"| Number | Pct | Type |\n| ------ | ---- | ---- |")
                    for atype in sorted(content_types):
                        type_count = insp_list.filter(content__content_type__startswith=atype).count()
                        type_pct = type_count/insp_list.count()
                        type_report = u"| {count:6,d} | {pct:.2%} | {atype} |".format(count=type_count, atype=atype, pct=type_pct)
                        self.stdout.write(type_report)
                    type_count = typeless_inspections.count()
                    type_pct = typeless_inspections.count()/insp_list.count() if insp_list.count() > 0 else 0
                    type_report = u"| {count:6,d} | {pct:.2%} | {atype} |".format(count=type_count, atype=u"None/Unknown", pct=type_pct)
                    self.stdout.write(type_report)
                if options['bad-urls'] and other_typeless_inspections.count() > 0:
                    self.stdout.write(u"### Invalid URLs?")
                    for insp in other_typeless_inspections.only('requested_url'):
                        self.stdout.write(u"     '{0}'".format(insp.requested_url))
                self.stdout.write(u"\n")
                self.stdout.write(u"*"*80)
                self.stdout.write(u"\n")
            except Audit.DoesNotExist:
                if options['show-missing']:
                    self.stderr.write(u"No recent audit exists for {0}\n\n".format(agency.name))

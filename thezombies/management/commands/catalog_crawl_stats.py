from django.db.models import Q
from django.core.management.base import BaseCommand
from thezombies.models import (Audit, Agency, Probe)
from optparse import make_option


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
                self.stdout.write(u"## {0}".format(audit.agency.name))
                date_str = u"{:%Y-%m-%d %H:%M%p}\n".format(audit.updated_at)
                num_urls_visited = audit.url_inspections.filter(parent__isnull=True).count()
                insp_list = audit.url_inspections.filter(content__isnull=False)
                typeless_inspections = audit.url_inspections.filter(content__content_type__isnull=True)
                ftp_inspections = typeless_inspections.filter(requested_url__startswith='ftp')
                typeless_http_inspections = typeless_inspections.filter(requested_url__startswith='http')
                other_typeless_inspections = typeless_inspections.exclude(id__in=ftp_inspections).exclude(id__in=typeless_http_inspections)
                json_probes = audit.probe_set.filter(probe_type=Probe.JSON_PROBE, previous__isnull=False)
                json_probes_public = json_probes.filter(initial__contains={u'accessLevel': u'public'})
                has_distribution_q = Q(initial__contains=['distribution'])
                has_accessURL_q = Q(initial__contains=['accessURL'])
                has_accessURL_badkey_q = Q(initial__contains=['accessUrl'])
                has_webservice_q = Q(initial__contains=['webService'])
                sans_data_urls = json_probes_public.exclude(has_distribution_q | has_accessURL_q | has_accessURL_badkey_q | has_webservice_q)
                self.stdout.write(u"\nUpdated: {0}\n".format(date_str))
                self.stdout.write(u"| Errors | Entries sans urls | URLs inspected | URLs no content-type | FTP URLs | Possibly Invalid URLs |")
                self.stdout.write(u"| ------ | ----------------- | -------------- | -------------------- | -------- | --------------------- |")
                stats_row = u"| {errors:6,d} | {sans_urls: >14,d} | {inspected: >14,d} | {typeless:20,d} | {ftp:8,d} | {invalid:21,d} |".format(
                            errors=audit.error_count(), inspected=num_urls_visited, typeless=typeless_http_inspections.count(),
                            ftp=ftp_inspections.count(), invalid=other_typeless_inspections.count(), sans_urls=sans_data_urls.count())
                self.stdout.write(stats_row)
                selector = u'content__content_type'
                insp_content_types = insp_list.select_related(selector).order_by(selector).distinct(selector).only(selector)
                content_types = list(set([x.content.content_type.split(';')[0] for x in insp_content_types if x.content.content_type]))
                if len(content_types) > 0:
                    self.stdout.write(u"\n### Content Types\n\n")
                    self.stdout.write(u"| Number | Type |\n| ------ | ---- |")
                for atype in sorted(content_types):
                    type_count = insp_list.filter(content__content_type__startswith=atype).count()
                    type_report = u"| {0:6,d} | {1} |".format(type_count, atype)
                    self.stdout.write(type_report)
                if options['bad-urls'] and other_typeless_inspections.count() > 0:
                    self.stdout.write(u"### Invalid URLs?")
                    for insp in other_typeless_inspections.only('requested_url'):
                        self.stdout.write(u"     '{0}'".format(insp.requested_url))
                self.stdout.write(u"\n\n")
            except Audit.DoesNotExist:
                if options['show-missing']:
                    self.stderr.write(u"No recent audit exists for {0}\n\n".format(agency.name))

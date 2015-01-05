from django.core.management.base import BaseCommand
from thezombies.models import Agency
from thezombies.tasks.main import crawl_agency_datasets


class Command(BaseCommand):
    """Start a task that crawl the datasets from an agency data catalog. This command will exit, but the task will run in the background"""
    args = '<agency_id ...>'

    def handle(self, *args, **options):
        if len(args) > 0:
            agency_id = args[0]
            if agency_id:
                task = crawl_agency_datasets.delay(agency_id)
                self.stdout.write(u'Running task with id {0}'.format(task.id))
                self.stdout.write(u'This can take many minutes...')
            else:
                self.stderr.write(u"Didn't get an agency_id!")
        else:
            self.stdout.write(u'Please provide an agency id:\n')
            agency_list = u'\n'.join(['{0:2d}: {1}'.format(a.id, a.name) for a in Agency.objects.all()])
            self.stdout.write(agency_list)
            self.stdout.write(u'\n')

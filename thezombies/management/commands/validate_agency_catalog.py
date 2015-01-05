from django.core.management.base import BaseCommand
from thezombies.models import Agency
from thezombies.tasks.main import validate_agency_catalog


class Command(BaseCommand):
    """Start a task that fetches and validates an agency data catalog. This command will exit, but the task will run in the background"""
    args = '<agency_id ...>'

    def handle(self, *args, **options):
        if len(args) > 0:
            agency_id = args[0]
            if agency_id:
                task = validate_agency_catalog.delay(agency_id)
                self.stdout.write(u'Running fetch+validation task with id: {0}'.format(task.id))
                self.stdout.write(u'This can take many minutes...')
            else:
                self.stderr.write(u"Didn't get a valid agency_id!")
        else:
            self.stdout.write(u'Please provide an agency id:\n')
            agency_list = u'\n'.join(['{0:2d}: {1}'.format(a.id, a.name) for a in Agency.objects.all()])
            self.stdout.write(agency_list)
            self.stdout.write(u'\n')

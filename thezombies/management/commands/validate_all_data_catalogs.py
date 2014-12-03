from django.core.management.base import NoArgsCommand
from thezombies.tasks.main import validate_data_catalogs


class Command(NoArgsCommand):
    """Validate all of the agency data catalogs"""

    def handle_noargs(self):
        validator_group = validate_data_catalogs.delay()
        self.stdout.write(u"\nSpawned data catalog task group: {0}\n".format(validator_group.id))

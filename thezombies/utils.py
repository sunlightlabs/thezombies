from django.utils import timezone


DATETIME_FORMATTER = u"{:%Y-%m-%d %I:%M%p %Z}"


def datetime_string(dt_obj=None):
    return DATETIME_FORMATTER.format(timezone.localtime(dt_obj if dt_obj else timezone.now()))

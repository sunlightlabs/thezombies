from django import template
from django.template.defaultfilters import stringfilter, yesno
from django.http.response import REASON_PHRASES

register = template.Library()

@register.filter
@stringfilter
def truthy(value, arg=None):
    """Wraps django's yesno filter to allow for JavaScript-style true or false string values."""
    truthiness = None
    if value.lower() == 'true':
        truthiness = True
    elif value.lower() == 'false':
        truthiness = False
    return yesno(truthiness, arg)

@register.filter
def httpreason(value):
    """Uses django's REASON_PHRASES to change a status_code into a textual reason."""
    try:
        value_int = int(value)
    except TypeError:
        return ''
    return REASON_PHRASES.get(value_int, 'UNKNOWN STATUS CODE')


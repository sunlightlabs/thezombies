from django import template
from django.template.defaultfilters import stringfilter, yesno

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
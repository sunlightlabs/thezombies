from __future__ import absolute_import
from django_atomic_celery import task

try:
    import simplejson as json
except ImportError:
    import json
import ujson

from .utils import ResultDict


@task
def parse_json(taskarg):
    """
    Task to parse json from content

    :param taskarg: ResultDict or regular dict containing values for keys 'content and optionally 'encoding'.
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    content = taskarg.get('content', None)
    encoding = taskarg.get('encoding', 'iso-8859-1')
    jsondata = None
    parse_errors = False
    returnval = ResultDict()
    if content is None:
        returnval.add_error(Exception('No content to parse'))
    else:
        try:
            jsondata = json.loads(content, encoding=encoding)
        except Exception as e:
            parse_errors = True
            returnval.add_error(e)
            content_str = content.decode(encoding, 'replace')
            try:
                jsondata = ujson.loads(content_str)
            except Exception as e:
                parse_errors = True
                returnval.add_error(e)
    returnval.update({'json': jsondata, 'parse_errors': parse_errors})
    return returnval

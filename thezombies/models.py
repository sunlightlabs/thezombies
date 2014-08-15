import requests
import json

from .utils import is_valid_url


class Auditable(object):
    def __init__(self, instance):
        super(Auditable, self).__init__()
        self.instance = instance

    @property
    def url_is_valid(self):
        return is_valid_url(self.instance.url)

    def __getattr__(self, name):
        return self.instance.__getattribute__(name)

class AuditableRequest(Auditable):
    """docstring for AuditableRequest"""


class AuditableResponse(Auditable):
    """docstring for AuditableResponse"""

    def __init__(self, instance):
        super(AuditableResponse, self).__init__(instance)
        self._unicode_text = None

    @property
    def json_is_valid(self):
        obj = self.unicode_json()
        return obj is not None

    @property
    def unicode_text(self):
        if not self._unicode_text:
            self._unicode_text = requests.utils.get_unicode_from_response(self.instance)
        return self._unicode_text

    def unicode_json(self):
        json_obj = None
        try:
            json_obj = json.dumps(self.unicode_text)
        except Exception:
            pass
        return json_obj

    def audit(self):
        obj = {}
        attributes = ('status_code', 'apparent_encoding', 'encoding',
                        'url', 'url_is_valid', 'json_is_valid')
        for a in attributes:
            obj[a] = getattr(self, a, None)
        obj['content_type'] = self.instance.headers.get('Content-Type', 'Not specified')
        obj['seconds_elapsed'] = self.instance.elapsed.total_seconds() if self.instance.elapsed else None
        return obj



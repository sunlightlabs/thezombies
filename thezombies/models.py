import requests
import json

from .utils import is_valid_url


class Auditable(object):
    audit_attributes = ('status_code', 'apparent_encoding', 'encoding', 'url', 'url_is_valid')

    def __init__(self, instance):
        super(Auditable, self).__init__()
        self.instance = instance

    @property
    def url_is_valid(self):
        return is_valid_url(self.instance.url)

    def __getattr__(self, name):
        return self.instance.__getattribute__(name)

    def audit(self):
        obj = {}
        for a in Auditable.audit_attributes:
            obj[a] = getattr(self, a, None)
            obj['type'] = self.instance.__class__.__name__.lower()
        return obj


class AuditableRequest(Auditable):
    """docstring for AuditableRequest"""

    def __init__(self, instance):
        super(AuditableRequest, self).__init__(instance)


class AuditableResponse(Auditable):
    """docstring for AuditableResponse"""

    def __init__(self, instance):
        super(AuditableResponse, self).__init__(instance)
        self._unicode_text = None

    @property
    def json_is_valid(self):
        obj = self.unicode_json()
        return (obj is not None)

    @property
    def seconds_elapsed(self):
        return self.instance.elapsed.total_seconds() if self.instance.elapsed else None

    @property
    def unicode_text(self):
        if not self._unicode_text:
            self._unicode_text = self.instance.content.decode(self.instance.apparent_encoding)
        return self._unicode_text

    def unicode_json(self):
        json_obj = None
        try:
            json_obj = json.loads(self.unicode_text)
        except Exception:
            pass
        return json_obj

    def audit(self):
        obj = super().audit()
        obj['json_is_valid'] = getattr(self, 'json_is_valid', None)
        obj['content_type'] = self.instance.headers.get('Content-Type', 'Not specified')
        obj['seconds_elapsed'] = self.seconds_elapsed
        obj['content_length'] = len(self.instance.content)
        return obj



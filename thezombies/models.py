import requests

from .utils import (is_valid_url, is_valid_json)


class Auditable(object):
    def __init__(self, instance):
        super(Auditable, self).__init__()
        self.instance = instance

    @property
    def valid_url(self):
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

    def is_valid_json(self):
        return is_valid_json(self.instance.text)

    @property
    def unicode_text(self):
        if not self._unicode_text:
            self._unicode_text = requests.utils.get_unicode_from_response(self.instance)
        return self._unicode_text

    def report(self):
        obj = {}
        attributes = ('status_code', 'apparent_encoding', 'encoding', 'url')
        for a in attributes:
            obj[a] = getattr(self, a, None)
        return obj



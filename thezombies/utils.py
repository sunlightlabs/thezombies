import requests
import re
import json

# A riff on http://tools.ietf.org/html/rfc3986#appendix-B
RFC_URL_REGEX = "^((https?):)(//([^/?#]+))([^?#]*)(\?([^#]*))?(#(.*))?$"

url_matcher = re.compile(RFC_URL_REGEX, flags=re.I|re.U)

def is_valid_url(url):
    return url_matcher.match(url) is not None

def is_valid_json(text):
    obj = None
    try:
        obj = json.loads(text)
    except ValueError:
        u_text = str(text.encode(encoding="utf-8"))
        obj = json.loads(u_text, encoding="utf-8")
    except Exception as e:
        pass
    return obj is not None

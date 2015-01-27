from __future__ import absolute_import
from django.db import transaction
from django.conf import settings
from django_atomic_celery import task

import requests
from requests.exceptions import InvalidURL

from .utils import ResultDict, logger, response_to_dict
from thezombies.models import URLInspection, Probe

try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse


REQUEST_TIMEOUT = getattr(settings, 'REQUEST_TIMEOUT', 60)

session = requests.Session()


def open_streaming_response(method, url):
    """
    Open a URL for streaming. Returns a requests.Response.
    The file-like object will be available under resp.raw.
    **Don't forget to close the response object!**
    http://docs.python-requests.org/en/latest/user/advanced/#body-content-workflow
    """
    resp = session.request(method.upper(), url, stream=True,
                           allow_redirects=True, timeout=REQUEST_TIMEOUT, verify=False)
    return resp


@task
def check_and_correct_url(url, method='GET'):
    """Check a url for issues, record exceptions, and attempt to correct the url.

    :param url: URL to check and correct
    :param method: http method to use, as a string. Default is 'GET'
    """
    returnval = ResultDict({'initial_url': url})
    try:
        logger.info('Checking URL: {0}'.format(url))
        scheme, netloc, path, params, query, fragments = urlparse(str(url))
        if scheme is '':
            # Maybe it is an http url without the scheme?
            scheme, netloc, path, params, query, fragments = urlparse("http://{0}".format(str(url)))
        elif not (scheme.startswith('http') or scheme.startswith('sftp') or scheme.startswith('ftp')):
            # Not a typical 'web' scheme
            raise InvalidURL('Invalid scheme (not http(s) or (s)ftp)')

        if netloc is '':
            raise InvalidURL('Invalid network location')

        corrected_url = urlunparse((scheme, netloc, path, params, query, fragments))
        returnval['valid_url'] = True
        returnval['corrected_url'] = corrected_url
    except Exception as e:
        logger.warn("Error validating url '{url}'".format(url=url))
        returnval.add_error(e)
        returnval['valid_url'] = False

    return returnval


@task
def request_url(url, method='GET'):
    """Task to request a url, a GET request by default. Tracks and returns errors.
    Will not raise an Exception, but may return None for response

    :param url: URL to request
    :param method: http method to use, as a string. Default is 'GET'
    """
    resp = None
    logger.info('Preparing request for URL: {0}'.format(url))
    checker_result = check_and_correct_url(url)
    corrected_url = checker_result.get('corrected_url', None)
    returnval = ResultDict(checker_result)
    returnval['url_request_attempted'] = False
    if corrected_url:
        try:
            logger.info('Requesting URL: {0}'.format(url))
            resp = session.request(method.upper(), corrected_url,
                                   allow_redirects=True, timeout=REQUEST_TIMEOUT, verify=False)
        except requests.exceptions.Timeout as e:
            logger.warn('Requesting URL: {0}'.format(url))
            returnval.add_error(e)
            returnval['timeout'] = True
        except Exception as e:
            returnval.add_error(e)
        returnval['url_request_attempted'] = True
        # a non-None requests.Response will evaluate to False if it carries an HTTPError value
        if resp is not None:
            try:
                resp.raise_for_status()
            except Exception as e:
                returnval.add_error(e)
            if isinstance(resp, requests.Response):
                returnval['response'] = response_to_dict(resp)
            else:
                logger.error('session.request did not return a valid Response object')
    logger.info('Returning from request_url')
    return returnval


@task
def inspect_url(taskarg):
    """Task to check a URL and store some information about it. Tracks and returns errors.

    :param taskarg: A dictionary containing a url, and optionally a audit_id
    """
    returnval = ResultDict(taskarg)
    url = taskarg.get('url', None)
    url_type = taskarg.get('url_type', None)
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('prev_probe_id', None)
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(probe_type=Probe.URL_PROBE,
                                     initial={'url': url, 'url_type': url_type},
                                     previous_id=prev_probe_id, audit_id=audit_id)
    if url:
        result = request_url(url, 'HEAD')
        response = result.pop('response', None)
        returnval.errors.extend(result.errors)
        probe.errors.extend(result.errors)
        with transaction.atomic():
            if response is not None:
                inspection = URLInspection.objects.create_from_response(response, save_content=False)
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.probe = probe
                inspection.save()
                returnval['inspection_id'] = inspection.id
            else:
                timeout = result.get('timeout', False)
                probe.result['timeout'] = timeout
                inspection = URLInspection.objects.create(requested_url=url, timeout=timeout)
                inspection.probe = probe
                if audit_id:
                    inspection.audit_id = audit_id
                inspection.save()
                returnval['inspection_id'] = inspection.id
            probe.result.update(result)
            probe.result['initial_url'] = url
            probe.result['inspection_id'] = returnval['inspection_id']
            probe.save()

    return returnval


@task
def get_or_create_inspection(url, with_content=False):
    """Task to get the lastest URLInspection or create a new one if none exists.

    :param url: The url to retrieve.
    """
    latest_dates = URLInspection.objects.datetimes('created_at', 'minute')
    recent_inspections = None
    fetch_val = None
    if latest_dates:
        latest_date = latest_dates.latest()
        recent_inspections = URLInspection.objects.filter(requested_url=url,
                                                          created_at__day=latest_date.day,
                                                          parent_id__isnull=True,
                                                          content__isnull=(not with_content))

    inspection = None
    if recent_inspections and recent_inspections.count() > 0:
        inspection = recent_inspections.latest()
    else:
        logger.info('No stored inspection, fetch url')
        fetch_val = request_url(url)
        response = fetch_val.get('response', None)
        with transaction.atomic():
            if response is not None:
                inspection = URLInspection.objects.create_from_response(response)
                inspection.save()
            else:
                timeout = fetch_val.get('timeout', False)
                inspection = URLInspection.objects.create(requested_url=url, timeout=timeout)
                inspection.save()
    returnval = ResultDict(fetch_val or {})
    returnval['inspection_id'] = getattr(inspection, 'id', None)
    return returnval

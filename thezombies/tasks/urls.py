from __future__ import absolute_import
from django.db import transaction
from django.conf import settings
from celery import shared_task

import requests
from requests.exceptions import (MissingSchema)
from cachecontrol import CacheControl

from .utils import ResultDict, logger
from thezombies.models import URLInspection

REQUEST_TIMEOUT = getattr(settings, 'REQUEST_TIMEOUT', 60)
session = CacheControl(requests.Session(), cache_etags=False)


@shared_task
def check_and_correct_url(url, method='GET'):
    """Check a url for issues, record exceptions, and attempt to correct the url.

    :param url: URL to check and correct
    :param method: http method to use, as a string. Default is 'GET'
    """
    returnval = ResultDict({'initial_url': url})
    req = requests.Request(method.upper(), url)
    try:
        preq = req.prepare()
    except MissingSchema as e:
        returnval.add_error(e)
        new_url = 'http://{}'.format(req.url)
        req.url = new_url
        try:
            preq = req.prepare()
            returnval['corrected_url'] = preq.url
        except Exception as e:
            returnval.add_error(e)
    except Exception as e:
        returnval.add_error(e)

    return returnval


@shared_task
def request_url(url, method='GET'):
    """Task to request a url, a GET request by default. Tracks and returns errors.
    Will not raise an Exception, but may return None for response

    :param url: URL to request
    :param method: http method to use, as a string. Default is 'GET'
    """
    resp = None
    checker_result = check_and_correct_url(url)
    valid_url = checker_result.get('corrected_url', url)
    returnval = ResultDict(checker_result)
    try:
        resp = session.request(method.upper(), valid_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout as e:
        returnval.add_error(e)
        returnval['timeout'] = True
    except Exception as e:
        returnval.add_error(e)
    # a non-None requests.Response will evaluate to False if it carries an HTTPError value
    if resp is not None:
        try:
            resp.raise_for_status()
        except Exception as e:
            returnval.add_error(e)
    returnval['response'] = resp
    return returnval


@shared_task
def get_or_create_inspection(url):
    """Task to get the lastest URLInspection or create a new one if none exists.

    :param url: The url to retrieve.
    """
    latest_dates = URLInspection.objects.datetimes('created_at', 'minute')
    recent_inspections = None
    if latest_dates:
        latest_date = latest_dates.latest()
        recent_inspections = URLInspection.objects.filter(requested_url=url, created_at__day=latest_date.day, parent_id__isnull=True)

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
    return ResultDict({'inspection_id': getattr(inspection, 'id', None), 'url': url})

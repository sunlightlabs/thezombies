from __future__ import absolute_import
from celery import chain, group
from django_atomic_celery import task
from django.db import transaction, DatabaseError

from .utils import error_handler, ResultDict, logger
from .urls import request_url
from .json import parse_json
from .catalog import (validate_json_catalog, create_data_crawl_audit)
from thezombies.models import (Probe, Audit, URLInspection, Agency)


@task
def parse_json_from_inspection(taskarg):
    """
    Task to parse json from a inspection.
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    inspection_id = taskarg.get('inspection_id', None)
    audit_id = taskarg.get('audit_id', None)
    if not audit_id:
        logger.warn('Running parse_json_from_inspection with an audit_id')
    prev_probe_id = taskarg.get('probe_id', None)
    probe = None
    returnval = ResultDict(taskarg)
    try:
        with transaction.atomic():
            probe = Probe.objects.create(probe_type=Probe.JSON_PROBE,
                                         initial={'inspection_id': inspection_id},
                                         previous_id=prev_probe_id, audit_id=audit_id)
    except DatabaseError as e:
        returnval.add_error(e)
        logger.error('DatabaseError -> Unable to create JSON probe in parse_json_from_inspection')
    if probe:
        returnval['probe_id'] = probe.id
    inspection = URLInspection.objects.get(id=inspection_id)
    inspection_content = inspection.content.string()
    encoding = inspection.encoding if inspection.encoding else inspection.apparent_encoding
    result_dict = parse_json({'content': inspection_content, 'encoding': encoding})
    jsondata = result_dict.get('json', None)
    parse_errors = result_dict.get('parse_errors', False)
    probe.result['json_errors'] = True if parse_errors else False
    probe.result['is_json'] = True if jsondata else False
    probe.result['json'] = jsondata
    errors = result_dict.get('errors', None)
    try:
        with transaction.atomic():
            if errors:
                probe.errors.extend(errors)
            probe.save()
            logger.info('Updated JSON probe from parse_json_from_inspection')
    except DatabaseError:
        logger.warn('DatabaseError -> Unable finalize_audit')
        raise e

    return returnval


@task
def finalize_audit(taskarg):
    audit_id = taskarg.get('audit_id', None)
    audit_type = taskarg.get('audit_type', Audit.GENERIC_AUDIT)
    returnval = ResultDict(taskarg)
    returnval['saved'] = False
    if audit_id:
        try:
            with transaction.atomic():
                audit = Audit.objects.get(id=audit_id)
                audit.audit_type = audit_type
                audit.save()
                returnval['saved'] = True
        except DatabaseError as e:
            logger.warn('DatabaseError -> Unable finalize_audit')
            raise e
    else:
        logger.warn('Unable to finalize audit. No audit_id provided!')


@task
def audit_for_agency_url(agency_id, url, audit_type=Audit.GENERIC_AUDIT):
    """Task to save a basic audit given an agency_id and a url.

    :param agency_id: Database id of the agency to create a audit for.
    :param url: URL to audit on.
    :param audit_type: Optional audit type (as provided by Audit model)

    """
    probe = None
    with transaction.atomic():
        probe = Probe.objects.create(initial={'agency_id': agency_id, 'url': url}, probe_type=Probe.URL_PROBE)
    result = request_url((url))
    returnval = ResultDict(result)
    if probe:
        returnval['probe_id'] = probe.id
    response = result.get('response', None)
    inspection = None
    with transaction.atomic():
        if response is not None:
            inspection = URLInspection.objects.create_from_response(response)
            inspection.probe = probe
            probe.result['status_code'] = response.get('status_code')
            inspection.save()
        audit = Audit.objects.create(agency_id=agency_id)
        returnval['audit_id'] = audit.id
        audit.audit_type = audit_type
        audit.probe_set.add(probe)
        audit.save()
        if inspection:
            returnval['inspection_id'] = inspection.id
            probe.result['inspection_id'] = inspection.id
        probe.errors.extend(returnval.errors)
        probe.save()
    if response and not response.ok:
        # If the inspection is not okay, raise an error so we can handle that as an error
        logger.warn(u'Received non-okay response for requested url: {0}'.format(url))
        response.raise_for_status()
    return returnval


@task
def validate_agency_catalog(agency_id):
    try:
        agency = Agency.objects.get(id=agency_id)
        task_chain = chain(
            audit_for_agency_url.subtask((agency.id, agency.data_json_url, Audit.DATA_CATALOG_VALIDATION),
                                         options={'link_error': error_handler.s()}),
            parse_json_from_inspection.s(),
            validate_json_catalog.s(),
            finalize_audit.s()
        )
        return task_chain()
    except Agency.DoesNotExist as e:
        raise e


@task
def validate_data_catalogs():
    agencies = Agency.objects.all()
    groupchain = group([chain(
        audit_for_agency_url.subtask((agency.id, agency.data_json_url, Audit.DATA_CATALOG_VALIDATION),
                                     options={'link_error': error_handler.s()}),
        parse_json_from_inspection.s(),
        validate_json_catalog.s(),
        finalize_audit.s()
    ) for agency in agencies])
    return groupchain.skew(start=1, stop=20)()


@task
def crawl_agency_datasets(agency_id):
    """Task that crawl the datasets from an agency data catalog.
    Runs create_data_crawl_audit, which spawns inspect_data_catalog_item tasks which in turn spawns
    inspect_data_catalog_item_url tasks.

    :param agency_id: Database id of the agency whose catalog should be crawled.

    """
    agency = Agency.objects.get(id=agency_id)
    return create_data_crawl_audit.apply_async((agency.id, agency.data_json_url),
                                               options={'link_error': error_handler.s()})

from __future__ import absolute_import
from django_atomic_celery import task
from django.conf import settings
from django.db import transaction, DatabaseError
from itertools import islice
import os.path
from contextlib import closing

try:
    import simplejson as json
except ImportError:
    import json
from ijson.common import (JSONError, IncompleteJSONError)
try:
    import ijson.backends.yajl2 as ijson
except ImportError:
    import ijson
from jsonschema import Draft4Validator

from .utils import logger, ResultDict
from .urls import open_streaming_response
from thezombies.models import (Probe, Audit, Agency)

SCHEMA_ERROR_LIMIT = 100
SCHEMA_DIR = getattr(settings, 'SCHEMA_DIR', None)
JSON_SCHEMAS = getattr(settings, 'JSON_SCHEMAS', None)

DATASET_DESCRIPTIVE_KEYS = ('title', 'identifier', 'publisher', 'accessLevel')

COUNTDOWN_MODULO = 21


@task
def validate_json_object(taskarg):
    """
    Validate json data object against a json_schema
    """
    if isinstance(taskarg, tuple):
        taskarg = taskarg[0]
    probe = prev_probe = None
    is_valid = False
    json_object = taskarg.get('json_object', None)
    json_schema_name = taskarg.get('json_schema_name', None)
    audit_id = taskarg.get('audit_id', None)
    prev_probe_id = taskarg.get('probe_id', None)
    returnval = ResultDict(taskarg)
    if json_schema_name:
        # Generally validate_json_object should run in connectino with an audit
        if audit_id:
            logger.info('Validating JSON object for audit {0}'.format(audit_id))
        else:
            logger.warning(u'validate_json_object running without an audit_id')

        # Create a validation probe to record results of validation attempt
        try:
            with transaction.atomic():
                probe = Probe.objects.create(probe_type=Probe.VALIDATION_PROBE)
        except DatabaseError as e:
            returnval.add_error(e)
            logger.exception(e)
            logger.error('Error creating JSON probe in validate_json_object')
        if probe:
            returnval['probe_id'] = probe.id
        # May be in a chain of probes, typically when validating an entire catalog, not one entry
            if prev_probe_id:
                prev_probe_exists = False
                with transaction.atomic():
                    prev_probe_exists = Probe.objects.filter(id=prev_probe_id).exists()
                if prev_probe_exists:
                    probe.previous_id = prev_probe_id
            if audit_id:
                probe.audit_id = audit_id

        # Build schema path, load schema json, and create validator
        schema_info = JSON_SCHEMAS.get(json_schema_name)
        schema_path = os.path.join(SCHEMA_DIR, schema_info.get('schema'))
        if os.path.exists(schema_path):
            json_schema = json.load(open(schema_path, 'r'))
            validator = Draft4Validator(json_schema)

            if json_object and validator:
                try:
                    is_valid = validator.is_valid(json_object)
                except (JSONError, IncompleteJSONError) as e:
                    logger.exception(e)
                    returnval.add_error(e)
                if not is_valid:
                    # Save up to SCHEMA_ERROR_LIMIT errors from schema validation
                    error_iter = islice(validator.iter_errors(json_object), SCHEMA_ERROR_LIMIT)
                    for e in error_iter:
                        returnval.add_error(e)
            if probe:
                # Record results of validation into probe
                probe.result['object_position'] = taskarg.get('object_position', None)
                probe.result['object_identifier'] = json_object.get('identifier', None)
                probe.result['object_info'] = {key: json_object.get(key, None) for key in DATASET_DESCRIPTIVE_KEYS}
                probe.result['is_valid_schema_instance'] = is_valid
                # Record errors and save probe
                with transaction.atomic():
                    probe.errors.extend(returnval.errors)
                    probe.save()
                    logger.info('Updated JSON probe in validate_json_object')

            returnval['audit_type'] = Audit.DATA_CATALOG_VALIDATION
        else:
            logger.error('Unable to fetch JSON schema file to create validator')
    else:
        logger.error('No JSON schema name provided. Cannot validate without a schema')
    return returnval


@task
def validate_catalog_datasets(agency_id, schema='DATASET_1.0'):
    agency = audit = tasks = resp = None
    with transaction.atomic():
        try:
            # Get agency
            agency = Agency.objects.get(id=agency_id)

        except Agency.DoesNotExist as e:
            logger.exception(e)
            raise e

    # Get schema info (schema path, dataset_prefix)
    schema_info = JSON_SCHEMAS.get(schema, None)

    # TODO: Handle URL opening errors
    # ConnectionError
    # HTTPError
    with transaction.atomic():
        audit = Audit.objects.create(agency_id=agency_id, audit_type=Audit.DATA_CATALOG_VALIDATION)

    try:
        with closing(open_streaming_response('GET', agency.data_json_url)) as resp:
            # Use the schema dataset_prefix to get an iterator for the items to be validated.
            objects = ijson.items(resp.raw, schema_info.get('dataset_prefix', ''))

            default_args = {'json_schema_name': schema, 'source_url': agency.data_json_url}
            if audit:
                default_args.update({'audit_id': audit.id})

            # We're going to spin off async tas
            tasks = []
            for num, obj in enumerate(objects):
                args = default_args.copy()
                args.update({'json_object': obj, 'object_position': num})
                task = validate_json_object.apply_async(args=(args,), countdown=(num % COUNTDOWN_MODULO))
                tasks.append(task)

    except Exception as e:
        logger.exception(e)

    return tasks

# @task
# def validate_data_catalogs():
#     agencies = Agency.objects.all()
#     groupchain = group([chain(
#         audit_for_agency_url.subtask((agency.id, agency.data_json_url, Audit.DATA_CATALOG_VALIDATION),
#                                      options={'link_error': error_handler.s()}),
#         parse_json_from_inspection.s(),
#         # validate_json_catalog.s(),
#         finalize_audit.s()
#     ) for agency in agencies])
#     return groupchain.skew(start=1, stop=20)()

# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from functools import wraps
from flask_login import current_user

from flask import flash, g, request, redirect, url_for, abort

from celery import Celery
from solarmonitor.settings import ProdConfig
from solarmonitor.solaredge.se_api import SolarEdgeApi

from datetime import datetime
from datetime import datetime, timedelta, date
from calendar import monthrange
import json


celery = Celery(__name__, broker=ProdConfig.CELERY_BROKER_URL,
                backend=ProdConfig.CELERY_RESULT_BACKEND,
                redis_max_connections=ProdConfig.CELERY_REDIS_MAX_CONNECTIONS)


def pull_solar_chunks(start_date_object, end_date_object, user):
    print user.full_name
    from solarmonitor.celerytasks.se_tasks import process_se_data
    from solarmonitor.celerytasks.enphase_tasks import process_enphase_data
    for energy_account in user.energy_accounts:
        days_of_data_needed = (end_date_object - start_date_object).days

        while days_of_data_needed:
            days_to_pull = 30 if days_of_data_needed >= 30 else days_of_data_needed
            print days_of_data_needed
            print 'start date', start_date_object
            print 'end date', (start_date_object + timedelta(days=days_to_pull))

            if energy_account.enphase_user_id and energy_account.enphase_system_id:
                print 'enphase PULLING'
                process_enphase_data.delay(energy_account.id, start_date_object, (start_date_object + timedelta(days=days_to_pull)))

            if energy_account.solar_edge_site_id:
                print 'solar edge PULLING'
                se = SolarEdgeApi(energy_account)
                se_energy = json.loads(
                    se.site_energy_measurements(
                        start_date_object.strftime('%Y-%m-%d'),
                        (start_date_object + timedelta(days=days_to_pull)).strftime('%Y-%m-%d'),
                        energy_account.solar_edge_site_id,
                        'DAY'
                    ).text
                )
                task = process_se_data.delay(se_energy, energy_account.id)

            """Cleanup and prepare for next loop"""
            start_date_object = (start_date_object + timedelta(days=days_to_pull))
            days_of_data_needed -= days_to_pull


def pull_chunks(start_date_object, end_date_object, user):
    from solarmonitor.celerytasks.pgetasks import process_xml
    for energy_account in user.energy_accounts:
        days_of_data_needed = (end_date_object - start_date_object).days

        while days_of_data_needed:
            days_to_pull = 30 if days_of_data_needed >= 30 else days_of_data_needed
            print days_of_data_needed
            print 'start date', start_date_object
            print 'end date', (start_date_object + timedelta(days=days_to_pull))

            process_xml.delay(
                                energy_account,
                                start_date_object,
                                (start_date_object + timedelta(days=days_to_pull)),
                                user_id=user.id
                            )
            """Cleanup and prepare for next loop"""
            start_date_object = (start_date_object + timedelta(days=days_to_pull))
            days_of_data_needed -= days_to_pull


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)


def convert_to_kWh(microwatts):
    return round((microwatts * (10**-6)), 2)


def try_parsing_date(text):
    if not text:
        return None
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%-m/%-d/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_roles = [x.role for x in current_user.roles]
            for role in roles:
                if role not in user_roles:
                    return abort(401)
            return f(*args, **kwargs)
        return wrapped
    return wrapper

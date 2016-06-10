# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash

from celery import Celery
from solarmonitor.settings import ProdConfig
celery = Celery(__name__, broker=ProdConfig.CELERY_BROKER_URL)


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)

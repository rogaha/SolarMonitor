# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from functools import wraps
from flask_login import current_user

from flask import flash, g, request, redirect, url_for, abort

from celery import Celery
from solarmonitor.settings import ProdConfig


celery = Celery(__name__, broker=ProdConfig.CELERY_BROKER_URL, backend=ProdConfig.CELERY_RESULT_BACKEND)

def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)



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

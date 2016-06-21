# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
from flask import Flask, render_template

from solarmonitor import public, user, auth
from solarmonitor.user import dashboard
from solarmonitor.assets import assets
from solarmonitor.extensions import bcrypt, db, login_manager
from solarmonitor.settings import ProdConfig
from solarmonitor.public.forms import LoginForm

from celery import Celery
celery = Celery(__name__, broker=ProdConfig.CELERY_BROKER_URL, backend=ProdConfig.CELERY_RESULT_BACKEND)


def create_app(config_object=ProdConfig):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_logger(app)

    celery.conf.update(app.config)

    @app.context_processor
    def inject_login_form():
        login_form = LoginForm()
        return dict(login_form=login_form)

    return app

def register_extensions(app):
    """Register Flask extensions."""
    assets.init_app(app)
    bcrypt.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(public.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(auth.views.blueprint)
    app.register_blueprint(dashboard.views.blueprint)
    return None


def register_errorhandlers(app):
    """Register error handlers."""
    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template('{0}.html'.format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None

def register_logger(app):
    import logging
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('microblog startup')

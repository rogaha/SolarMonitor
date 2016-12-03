# -*- coding: utf-8 -*-
"""Application configuration."""
import os


class Config(object):
    """Base configuration."""

    SECRET_KEY = 'ft-EcE#=fnBxNL9BQ2g*_E7ZdJrtM3z&6MwJ6vbEr@K#uV-?Ar#z+L!qX99h5rEXS'  # TODO: Change me
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    BCRYPT_LOG_ROUNDS = 13
    ASSETS_DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_EMAILS = ['dan@danwins.com', 'brad@epirtle.com']
    SSL_CERTS = {'crt': os.path.join(APP_DIR, 'ssl/client_cert.pem'), 'key': os.path.join(APP_DIR, 'ssl/client_key.pem')}
    #client_id and client_key are the same thing
    PGE_CLIENT_CREDENTIALS = {'client_key': '4f5e3635db834479a6a8ecc77da25407', 'client_secret_key': 'e21cf6a248bb4096baf82fce4640bbd8'}
    REG_ACCESS_TOKEN = '5a01ad84-e582-43bb-9e8f-bffcb1d4129e'

    """The data custodian URL is found by calling GET /resource/Authorization and then in the resulting XML
    grabbing the resourceURI xml element. You then make yet another GET to /resource/ApplicationInformation/{ApplicationInformationID}
    and the custodian URL for starting the OAuth process from our website is returned, which is saved below. This shouldn't Change unless
    we create a new application."""
    PGE_DATA_CUSTODIAN_URL = 'https://sharemydata.pge.com/myAuthorization/?clientId=50154&verified=true'
    PGE_3rd_PARTY_REDIRECT_URI = 'https://notrueup.solardatapros.com/pge-oauth-redirect'
    TESTING_XML = os.path.join(APP_DIR, 'testing/bulk_data_2.xml')
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://h:p2kbl8u0gp3fvnd0cmtthi98bqq@ec2-54-221-253-136.compute-1.amazonaws.com:6819')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://h:p2kbl8u0gp3fvnd0cmtthi98bqq@ec2-54-221-253-136.compute-1.amazonaws.com:6819')
    ENPHASE_API_KEY = 'aedc75d38120f96a689e7f83c4ce22f8'
    ENPHASE_REDIRECT_URI = 'https://notrueup.solardatapros.com/enphase-authorization'
    ENPHASE_APP_ID = '1409613132468'
    ENPHASE_AUTHORIZATION_URL = 'https://enlighten.enphaseenergy.com/app_user_auth/new?app_id={}&redirect={}'.format(
                                                                                                    ENPHASE_APP_ID,
                                                                                                    ENPHASE_REDIRECT_URI)

class ProdConfig(Config):
    """Production configuration."""

    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgres://npyecevfvfiqyu:lczG2Ce2qeydBnN37WVBDnERcy@ec2-54-243-45-168.compute-1.amazonaws.com:5432/d88tv4rrrt3c55')
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar

class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    DB_NAME = 'dev.db'
    # Put the db file in project root
    DB_PATH = os.path.join(Config.PROJECT_ROOT, DB_NAME)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgres://npyecevfvfiqyu:lczG2Ce2qeydBnN37WVBDnERcy@ec2-54-243-45-168.compute-1.amazonaws.com:5432/d88tv4rrrt3c55')
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://solarmonitor:solarmonitor@localhost:3306/solarmonitor_test'
    BCRYPT_LOG_ROUNDS = 4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
    WTF_CSRF_ENABLED = False  # Allows form testing

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
    PGE_CLIENT_CREDENTIALS = {'client_key': 'b5020eaae0f34c56a62726ff6f059b45', 'client_secret_key': '69f7ad97530447f49d9468373cf2fc4f'}
    REG_ACCESS_TOKEN = '5fe3233d-c9f8-4ff9-9f63-3d02dc534c3c'

class ProdConfig(Config):
    """Production configuration."""

    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'postgres://zqdbbnsrdcldwf:hN8yok1PcmPR6elNtOXUyqOCQg@ec2-54-235-207-226.compute-1.amazonaws.com:5432/de83poa0e5nd3o'
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar

class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    DB_NAME = 'dev.db'
    # Put the db file in project root
    DB_PATH = os.path.join(Config.PROJECT_ROOT, DB_NAME)
    SQLALCHEMY_DATABASE_URI = 'postgres://zqdbbnsrdcldwf:hN8yok1PcmPR6elNtOXUyqOCQg@ec2-54-235-207-226.compute-1.amazonaws.com:5432/de83poa0e5nd3o'
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgres://zqdbbnsrdcldwf:hN8yok1PcmPR6elNtOXUyqOCQg@ec2-54-235-207-226.compute-1.amazonaws.com:5432/de83poa0e5nd3o'
    BCRYPT_LOG_ROUNDS = 4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
    WTF_CSRF_ENABLED = False  # Allows form testing

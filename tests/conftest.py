# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from webtest import TestApp

from solarmonitor.app import create_app
from solarmonitor.extensions import db as _db
from solarmonitor.settings import TestConfig

from solarmonitor.user.models import User


@pytest.yield_fixture(scope='function')
def app():
    """An application for the tests."""
    _app = create_app(TestConfig)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture(scope='function')
def testapp(app):
    """A Webtest app."""
    return TestApp(app)


@pytest.yield_fixture(scope='function')
def db(app):
    """A database for the tests."""
    _db.app = app
    with app.app_context():
        _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


@pytest.fixture
def user(db):
    """A user for the tests."""
    user = User(
        email='user_testing@solarmonitor.com',
        username='testing',
        first_name='solarsolar',
        last_name='solarsolarlast',
        password='myprecious',
        address_one='',
        address_two='',
        state='',
        city='',
        zip_code=0,
        cell_phone='',
        role_id=1,
        pge_bulk_id=1
        )
    db.session.add(user)
    db.session.commit()
    return user

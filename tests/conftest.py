# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from webtest import TestApp

from solarmonitor.app import create_app
from solarmonitor.extensions import db as _db
from solarmonitor.settings import TestConfig

from solarmonitor.user.models import User, EnergyAccount, Role

def login_user(user, testapp):
    # Goes to homepage
    res = testapp.get('/')
    # Fills out login form in navbar
    form = res.forms['loginForm']
    form['email'] = user.email
    form['password'] = 'myprecious'
    # Submits
    res = form.submit().follow()

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
def admin_user(db):
    """A user for the tests."""
    user = User(
        email='user_testing@solarmonitor.com',
        first_name='solarsolar',
        last_name='solarsolarlast',
        password='myprecious'
        )

    role = Role(
        role='Admin'
    )
    energy_account = EnergyAccount(
        address_one = '123 Unknown',
        address_two = 'db.Column(db.String(255))',
        city = 'Sacramento',
        state = 'CA',
        zip_code = '14545',
        pge_bulk_id = '54468',
        pge_access_token = '2151dsfsdf',
        solar_edge_site_id = 'api_key'
        )
    user.energy_accounts.append(energy_account)
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def user(db):
    """A user for the tests."""
    user = User(
        email='user_testing@solarmonitor.com',
        first_name='solarsolar',
        last_name='solarsolarlast',
        password='myprecious'
        )

    energy_account = EnergyAccount(
        address_one = '123 Unknown',
        address_two = 'db.Column(db.String(255))',
        city = 'Sacramento',
        state = 'CA',
        zip_code = '14545',
        pge_bulk_id = '54468',
        pge_access_token = '2151dsfsdf',
        solar_edge_site_id = 'api_key'
        )
    user.energy_accounts.append(energy_account)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def energy_account(db):
    """An energy account for the tests."""
    energy_account = EnergyAccount(
        address_one = '123 Unknown',
        address_two = 'db.Column(db.String(255))',
        city = 'Sacramento',
        state = 'CA',
        zip_code = '14545',
        pge_bulk_id = '54468',
        pge_access_token = '2151dsfsdf',
        solar_edge_site_id = 'api_key'
        )
    db.session.add(energy_account)
    db.session.commit()
    return energy_account

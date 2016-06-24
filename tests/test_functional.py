# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from flask import url_for

from solarmonitor.user.models import User
from solarmonitor.extensions import db
import pytest


class TestLoggingIn:
    """Login."""

    def test_can_log_in_returns_200(self, user, testapp):
        """Login successful."""
        # Goes to homepage
        res = testapp.get('/about')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()
        assert res.status_code == 200

    def test_sees_alert_on_log_out(self, user, testapp):
        #Show alert on logout.
        res = testapp.get('/about')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()
        res = testapp.get(url_for('auth.logout')).follow()
        # sees alert
        assert 'You are logged out.' in res


    def test_sees_error_message_if_password_is_incorrect(self, user, testapp):
        #Show error if password is incorrect.
        # Goes to homepage
        res = testapp.get('/about')
        # Fills out login form, password incorrect
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'wrong'
        # Submits
        res = form.submit()
        # sees error
        assert 'Invalid username or password' in res


    def test_sees_error_message_if_email_doesnt_exist(self, user, testapp):
        #Show error if username doesn't exist.
        # Goes to homepage
        res = testapp.get('/about')
        # Fills out login form, password incorrect
        form = res.forms['loginForm']
        form['email'] = 'unknown@d.com'
        form['password'] = 'myprecious'
        # Submits
        res = form.submit()
        # sees error
        print res
        assert 'Invalid username or password' in res

@pytest.mark.usefixtures('db')
class TestRegistering:
    #Register a user.

    def test_can_register(self, user, testapp):
        #Register a new user.
        old_count = len(User.query.all())
        # Goes to homepage
        res = testapp.get(url_for('public.home'))
        # Fills out the form
        form = res.forms['RegistrationForm']
        form['email'] = 'foo@bar.com'
        form['first_name'] = 'solar'
        form['last_name'] = 'solar'
        form['password'] = 'secret'
        form['password2'] = 'secret'
        # Submits
        res = form.submit().follow()
        assert res.status_code == 200
        # A new user was created
        assert len(User.query.all()) == old_count + 1

    def test_energy_account_created_upon_registering(self, user, testapp):
        res = testapp.get(url_for('public.home'))
        # Fills out the form
        form = res.forms['RegistrationForm']
        form['email'] = 'foo@bar.com'
        form['first_name'] = 'solar'
        form['last_name'] = 'solar'
        form['password'] = 'secret'
        form['password2'] = 'secret'
        # Submits
        res = form.submit().follow()

        new_user = User.query.filter_by(email='foo@bar.com').first()

        assert new_user.energy_accounts is not None


    def test_sees_error_message_if_passwords_dont_match(self, user, testapp):
        #Show error if passwords don't match.
        # Goes to registration page
        res = testapp.get(url_for('auth.register'))
        # Fills out form, but passwords don't match
        form = res.forms['RegistrationForm']
        form['email'] = 'foo@bar.com'
        form['first_name'] = 'solar'
        form['last_name'] = 'solar'
        form['password'] = 'secret'
        form['password2'] = 'secret2323232'
        # Submits
        res = form.submit()
        # sees error message
        assert 'Passwords must match' in res


    def test_sees_error_message_if_user_already_registered(self, user, testapp):
        #Show error if user already registered.

        # Goes to registration page
        res = testapp.get(url_for('auth.register'))
        # Fills out form, but username is already registered
        form = res.forms['RegistrationForm']
        form['email'] = user.email
        form['first_name'] = 'solar'
        form['last_name'] = 'solar'
        form['password'] = 'secret'
        form['password2'] = 'secret2323232'
        # Submits
        res = form.submit()
        # sees error
        assert 'Email already in use.' in res

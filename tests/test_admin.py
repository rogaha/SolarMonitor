# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from flask import url_for, session
import pytest

from solarmonitor.user.models import User
from conftest import login_user


class TestAdmin:
    """Tests for the user dashboard."""

    def test_reg_user_cant_see_admin(self, user, testapp):
        login_user(user, testapp)

        res = testapp.get(url_for('admin.test_user_account', modify='login_as', user_id=1), expect_errors=True)
        assert res.status_code == 401

        res = testapp.get(url_for('admin.users'), expect_errors=True)
        assert res.status_code == 401

        res = testapp.get(url_for('admin.events'), expect_errors=True)
        assert res.status_code == 401

    def test_admin_user_can_see_admin(self, admin_user, testapp):
        login_user(admin_user, testapp)

        res = testapp.get(url_for('admin.users'))
        assert res.status_code == 200

        res = testapp.get(url_for('admin.events'))
        assert res.status_code == 200

        res = testapp.get(url_for('admin.test_user_account', modify='login_as', user_id=1))
        assert res.status_code == 302 #Redirect to new user account

    def test_add_user_as_admin(self, admin_user, testapp):
        login_user(admin_user, testapp)

        res = testapp.get(url_for('admin.users'))
        form = res.forms['RegistrationForm']
        form['add-first_name'] = 'bob'
        form['add-last_name'] = 'bobby'
        form['add-email'] = 'bob@bobby.com'
        form['add-password'] = 'myprecious'
        form['add-password2'] = 'myprecious'
        res = form.submit()

        user = User.query.filter_by(email='bob@bobby.com').first()

        assert user.full_name == 'bob bobby'

        res = testapp.get(url_for('admin.users'))
        form = res.forms['content_{}'.format(user.id)]
        form['edit-first_name'] = 'bob2'
        res = form.submit().follow()

        user = User.query.filter_by(email='bob@bobby.com').first()

        assert user.full_name == 'bob2 bobby'

        res = testapp.get(url_for('admin.users', modify='del', user_id=user.id))
        user = User.query.filter_by(email='bob@bobby.com').first()

        assert user == None

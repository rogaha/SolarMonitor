# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from flask import url_for

from solarmonitor.extensions import db
from solarmonitor.user.models import User, PGEUsagePoint, SolarEdgeUsagePoint

import pytest

@pytest.mark.usefixtures('db')
class TestPublicRoutes200:
    """The purpose of this test suite is to make sure that each url route returns a 200 status code.
    It's essentially a quick way to make sure there are no show stopping errors in the template code,
    or the server side code. This class tests all public routes, that do no require authentication.
    """

    def test_home(self, testapp):
        """Home Page."""
        res = testapp.get(url_for('public.home'))
        assert res.status_code == 200

    def test_about(self, testapp):
        """About Page."""
        res = testapp.get(url_for('public.about'))
        assert res.status_code == 200

    def test_logout(self, user, testapp):
        """Logout Page."""

        # Goes to homepage to login
        res = testapp.get('/')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()

        #logout then redirects to home page
        res = testapp.get(url_for('auth.logout')).follow()
        assert res.status_code == 200

    def test_register(self, testapp):
        """Register Page."""
        res = testapp.get(url_for('auth.register'))
        assert res.status_code == 200

    def test_notifications(self, testapp):
        """Notification URL. Currently should return 200 if a visitor lands on it.
        Should also return 200 if POST data is submitted from PGE.
        """
        res = testapp.get(url_for('public.notifications'))
        assert res.status_code == 200

    def test_oauth(self, testapp):
        """This URL is part of the oauth process."""
        res = testapp.get(url_for('public.oauth'))
        assert res.status_code == 200

    def test_oauth_redirect(self, testapp):
        """This URL is part of the oauth process. Should return 200 currently,
        but will be update to a 301 at some point when PGE is ready.
        """
        res = testapp.get(url_for('public.oauth_redirect'))
        assert res.status_code == 200

    def test_selenium_img_generator(self, user, testapp):
        """Solar Edge chart page for downloading and viewing data.
        """
        res = testapp.get(url_for('public.selenium_img_generator', energy_account_id=user.energy_accounts[0].id))
        assert res.status_code == 200

        made_up_number = 5649875454
        res = testapp.get(url_for('public.selenium_img_generator', energy_account_id=made_up_number))
        assert res.status_code == 302

    def test_dashboard_home(self, user, testapp):
        """Solar Edge chart page for downloading and viewing data.
        """
        # Goes to homepage
        res = testapp.get('/')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()
        res = testapp.get(url_for('dashboard.home'))
        assert res.status_code == 200

    def test_solar_edge_charts(self, user, testapp):
        """Solar Edge chart page for downloading and viewing data.
        """
        # Goes to homepage
        res = testapp.get('/')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()
        res = testapp.get(url_for('dashboard.solar_edge'))
        assert res.status_code == 200

    def test_pge_charts(self, user, testapp):
        # Goes to homepage
        res = testapp.get('/')
        # Fills out login form in navbar
        form = res.forms['loginForm']
        form['email'] = user.email
        form['password'] = 'myprecious'
        # Submits
        res = form.submit().follow()
        """PGE Chart page for downloading and viewing data.
        """
        res = testapp.get(url_for('dashboard.charts'))
        assert res.status_code == 200

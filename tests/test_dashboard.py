# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from flask import url_for, session
import pytest

from solarmonitor.user.models import User



class TestDashboard:
    """Tests for the user dashboard."""

    def test_solar_edge_clear_session(self, user, testapp):
        # Goes to solar edge dashboard
        res = testapp.get(url_for('dashboard.solar_edge'))

        # Fills out date select form
        form = res.forms['solar_edge_data_view']
        form['date_select_form-start_date'] = '2016-06-05'
        form['date_select_form-end_date'] = '2016-06-01'
        form['date_select_form-data_time_unit'] = 'Daily'
        # Submits
        res = form.submit().follow()

        assert 'value="2016-06-05"' in res
        assert 'value="2016-06-01"' in res

        res = testapp.get(url_for('dashboard.solar_edge', modify='clear')).follow()

        assert 'value="2016-06-05"' not in res
        assert 'value="2016-06-01"' not in res

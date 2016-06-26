# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import SolarEdgeUsagePoint
from solarmonitor.solaredge.solaredge_helper import generate_random_solar_edge_data
import datetime

@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self, user, energy_account):
        """Get usagepoint by ID."""
        se_usage_point = SolarEdgeUsagePoint(
            energy_account_id=energy_account.id,
            time_unit='Wh',
            unit_of_measure='DAY',
            date=datetime.datetime.now(),
            value='2000.001'
            )
        db.session.add(se_usage_point)
        db.session.commit()

        retrieved = SolarEdgeUsagePoint.query.filter_by(id=se_usage_point.id).first()
        assert retrieved == se_usage_point


    def test_add_sample_solar_edge_data(self, user):
        generate_random_solar_edge_data(number_of_data_rows=10, account_id=user.energy_accounts[0].id, numbers_of_days_ago=10)

        retrieved = SolarEdgeUsagePoint.query.filter_by(energy_account_id=user.energy_accounts[0].id).all()
        assert len(retrieved) is 10

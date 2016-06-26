# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import PGEUsagePoint
from tests.test_pge_models import generate_random_pge_data
import datetime 

@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self, user, energy_account):
        """Get usagepoint by ID."""
        pge_usage_point = PGEUsagePoint(
            energy_account_id=energy_account.id,
            commodity_type=1,
            measuring_period=3,
            interval_start=datetime.datetime.now(),
            interval_duration=1,
            interval_value=2,
            flow_direction=17,
            unit_of_measure=5,
            power_of_ten_multiplier=-3,
            accumulation_behavior=4
            )
        db.session.add(pge_usage_point)
        db.session.commit()

        retrieved = PGEUsagePoint.query.filter_by(id=pge_usage_point.id).first()
        assert retrieved == pge_usage_point

    def test_add_sample_pge_data(self, user):
        generate_random_pge_data(number_of_data_rows=10, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)


        retrieved = PGEUsagePoint.query.filter_by(energy_account_id=user.energy_accounts[0].id).all()
        assert len(retrieved) is 10

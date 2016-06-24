# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import SolarEdgeUsagePoint
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

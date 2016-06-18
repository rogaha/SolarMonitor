# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import UsagePoint
import datetime

@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self, user):
        """Get usagepoint by ID."""
        pge_usage_point = UsagePoint(
            user_id=user.id,
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

        retrieved = UsagePoint.query.filter_by(id=pge_usage_point.id).first()
        assert retrieved == pge_usage_point

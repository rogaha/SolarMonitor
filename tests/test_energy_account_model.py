# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import User, EnergyAccount


@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self):
        """Get user by ID."""
        energy_account = EnergyAccount(
            address_one='123 Unknown',
            address_two='None',
            city='Sacramento',
            state='CA',
            zip_code='54647',
            )
        db.session.add(energy_account)
        db.session.commit()

        retrieved = EnergyAccount.query.filter_by(id=energy_account.id).first()
        assert retrieved == energy_account

# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import User, EnergyAccount, AppEvent, EnergyEvent


@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self):
        """Get user by ID."""
        user = User(
            email='user_testing@solarmonitor.com',
            first_name='solarsolar',
            last_name='solarsolarlast',
            password='myprecious'
            )
        db.session.add(user)
        db.session.commit()

        retrieved = User.query.filter_by(id=user.id).first()
        assert retrieved == user

    def test_get_app_event_by_id(self, user):
        """Get user by ID."""
        app_event = AppEvent(
            date_time=dt.datetime.now(),
            event_type=1,
            level=2,
            info='test',
            user_id=1
            )
        db.session.add(app_event)
        db.session.commit()

        retrieved = AppEvent.query.filter_by(id=app_event.id).first()
        assert retrieved == app_event

    def test_get_energy_event_by_id(self, user):
        """Get user by ID."""
        energy_event = EnergyEvent(
            energy_account_id=1,
            date=dt.datetime.now().date(),
            event_type=1,
            info='test'
            )
        db.session.add(energy_event)
        db.session.commit()

        retrieved = EnergyEvent.query.filter_by(id=energy_event.id).first()
        assert retrieved == energy_event

    def test_password_is_not_nullable(self):
        """Passwords can't be blank."""
        with pytest.raises(Exception):
            user = User(
                email='user_testing@solarmonitor.com',
                first_name='solarsolar',
                last_name='solarsolarlast',
                password=None
                )
            db.session.add(user)
            db.session.commit()


    def test_check_password(self):
        """Check password."""
        user = User(email='foo@bar.com',
                           password='foobarbaz123')
        assert user.verify_password('foobarbaz123') is True
        assert user.verify_password('barfoobaz') is False

    def test_multiple_energy_accounts(self):
            user = User(
                email='user_testing@solarmonitor.com',
                first_name='solarsolar',
                last_name='solarsolarlast',
                password='myprecious'
                )
            db.session.add(user)
            db.session.commit()

            assert len(user.energy_accounts) is 0

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
            db.session.commit()
            assert len(user.energy_accounts) is 1

            energy_account = EnergyAccount(
                address_one = '123 Unknown different',
                address_two = 'db.Column(db.String(255))',
                city = 'Sacramento',
                state = 'CA',
                zip_code = '1224545',
                pge_bulk_id = '544683',
                pge_access_token = '2151dsfsdf',
                solar_edge_site_id = 'api_key'
                )
            user.energy_accounts.append(energy_account)

            assert len(user.energy_accounts) is 2

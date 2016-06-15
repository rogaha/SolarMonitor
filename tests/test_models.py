# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import User


@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self):
        """Get user by ID."""
        user = User(
            email='user_testing@solarmonitor.com',
            username='testing2',
            first_name='solarsolar',
            last_name='solarsolarlast',
            password='myprecious',
            address_one='',
            address_two='',
            state='',
            city='',
            zip_code=0,
            cell_phone='',
            role_id=1,
            pge_bulk_id=1
            )
        db.session.add(user)
        db.session.commit()

        retrieved = User.query.filter_by(id=user.id).first()
        assert retrieved == user

    def test_password_is_not_nullable(self):
        """Passwords can't be blank."""
        with pytest.raises(Exception):
            user = User(
                email='user_testing@solarmonitor.com',
                username='testing2',
                first_name='solarsolar',
                last_name='solarsolarlast',
                password=None,
                address_one='',
                address_two='',
                state='',
                city='',
                zip_code=0,
                cell_phone='',
                role_id=1,
                pge_bulk_id=1
                )
            db.session.add(user)
            db.session.commit()


    def test_check_password(self):
        """Check password."""
        user = User(username='foo', email='foo@bar.com',
                           password='foobarbaz123')
        assert user.verify_password('foobarbaz123') is True
        assert user.verify_password('barfoobaz') is False

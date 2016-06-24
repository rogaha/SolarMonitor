# -*- coding: utf-8 -*-
"""Test forms."""

from solarmonitor.public.forms import LoginForm
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.user.models import User
from solarmonitor.extensions import db


class TestRegisterForm:
    """Register form."""

    def test_validate_email_already_registered(self, user):
        """Enter email that is already registered."""
        form = RegistrationForm(username='unique', email=user.email,
                            password='example', confirm='example')

        assert form.validate() is False
        assert 'Email already in use.' in form.email.errors

    def test_validate_success(self, db):
        """Register with success."""
        form = RegistrationForm(email='uniqueunique@bar.com',
                            password='example', password2='example', first_name='solarsolar', last_name='solarsolarlast')

        assert form.validate() is True


class TestLoginForm:
    """Login form."""

    def test_validate_success(self, user):
        """Login successful."""
        user.password = 'example'
        db.session.commit()
        form = LoginForm(email=user.email, password='example')
        assert form.validate() is True
        assert form.email.data == user.email

    def test_validate_unknown_username(self, db):
        """Unknown username."""
        form = LoginForm(email='unknown', password='example')
        user = User.query.filter_by(email=form.email.data).first()
        assert user is None

    def test_validate_invalid_password(self, user):
        """Invalid password."""
        user.password = 'example'
        db.session.commit()
        form = LoginForm(email=user.email, password='wrongpassword')
        assert user.verify_password(form.password.data) is False

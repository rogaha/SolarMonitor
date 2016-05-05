# -*- coding: utf-8 -*-
"""Public forms."""
from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import Required, Length


class LoginForm(Form):
    username = StringField('User Name', validators=[Required(), Length(1, 64)])
    password = PasswordField ('Password', validators=[Required()])
    submit = SubmitField('Log In')

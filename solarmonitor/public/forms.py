# -*- coding: utf-8 -*-
"""Public forms."""
from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import Required, Length


class LoginForm(Form):
    username = StringField('User Name', validators=[Required(), Length(1, 64)])
    password = PasswordField ('Password', validators=[Required()])
    submit = SubmitField('Log In')

class DateSelectForm(Form):
    start_date = StringField('Start Date')
    end_date = StringField('Start Date')
    data_time_unit = SelectField('Time Unit', choices=[('Daily', 'Daily'), ('Hourly', 'Hourly')])
    submit = SubmitField('Download Data')

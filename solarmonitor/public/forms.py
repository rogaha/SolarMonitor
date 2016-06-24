# -*- coding: utf-8 -*-
"""Public forms."""
from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import Required, Length, Email


class LoginForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64), Email()])
    password = PasswordField ('Password', validators=[Required()])
    submit = SubmitField('Log In')

class DateSelectForm(Form):
    start_date = StringField('Start Date')
    end_date = StringField('Start Date')
    data_time_unit = SelectField('Time Unit', choices=[('Daily', 'Daily'), ('Hourly', 'Hourly')])
    submit = SubmitField('Select Date Range')

class DownloadDataForm(Form):
    start_date = StringField('Start Date')
    end_date = StringField('Start Date')
    submit = SubmitField('Download Data')

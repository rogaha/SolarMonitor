"""Dashboard forms."""
from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import Required, Length, Email

class EventAddForm(Form):
    date = StringField('Start Date')
    info = StringField('Start Date')
    event_type = SelectField('Time Unit', coerce=int, choices=[(1, 'Weather'), (2, 'Panel Related')])

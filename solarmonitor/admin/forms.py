from flask_wtf import Form
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Required, Regexp, ValidationError

from solarmonitor.user.models import User  

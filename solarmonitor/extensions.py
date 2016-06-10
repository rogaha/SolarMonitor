# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy


bcrypt = Bcrypt()
login_manager = LoginManager()
db = SQLAlchemy()

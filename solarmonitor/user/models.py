# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin

from solarmonitor.extensions import bcrypt, db

class UsagePoint(db.Model):
    __tablename__ = 'usagepoints'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    commodity_type = db.Column(db.Integer)
    measuring_period = db.Column(db.Integer)
    interval_start = db.Column(db.Integer)
    interval_duration = db.Column(db.Integer)
    interval_value = db.Column(db.Integer)
    flow_direction = db.Column(db.Integer)
    unit_of_measure = db.Column(db.Integer)
    power_of_ten_multiplier = db.Column(db.Integer)
    accumulation_behavior = db.Column(db.Integer)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64))
    username = db.Column(db.String(64), unique=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    address_one = db.Column(db.String(64))
    address_two = db.Column(db.String(64))
    state = db.Column(db.String(64))
    city = db.Column(db.String(64))
    zip_code = db.Column(db.Integer)
    cell_phone = db.Column(db.Integer)
    pge_bulk_id = db.Column(db.Integer)
    role_id = db.Column(db.Integer)
    password_hash = db.Column(db.String(128))
    usage_points = db.relationship('UsagePoint', backref="user", cascade="all, delete-orphan", lazy='dynamic')


    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password, 12)

    def verify_password(self, password):
        try:
            return bcrypt.check_password_hash(self.password_hash, password)
        except:
            return check_password_hash(self.password_hash, password)



    def __repr__(self):
        return '<User {}>' .format(self.first_name)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(app.config['SECRET_KEY'], expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(self, token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('id') != self.id:
            return False
        self.confirmed = 1
        db.session.commit()
        return True

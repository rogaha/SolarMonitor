# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy.orm import relationship

from solarmonitor.extensions import bcrypt, db

energy_accounts = db.Table('energy_accounts_users',
    db.Column('energy_account_id', db.Integer, db.ForeignKey('energy_accounts.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)

role_associations = db.Table('users_roles',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)

permission_associations = db.Table('permissions_roles',
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
)

class EnergyAccount(db.Model):
    __tablename__ = 'energy_accounts'
    id = db.Column(db.Integer, primary_key=True)
    address_one = db.Column(db.String(255))
    address_two = db.Column(db.String(255))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.Integer)
    pge_bulk_id = db.Column(db.Integer)
    pge_access_token = db.Column(db.String(255))
    solar_edge_api_key = db.Column(db.String(255))
    pge_usage_points = db.relationship('PGEUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    solar_edge_usage_points = db.relationship('SolarEdgeUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    celery_tasks = db.relationship('CeleryTask', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')


    def __repr__(self):
        return '<EnergyAccount {}>' .format(self.id)

class PGEUsagePoint(db.Model):
    __tablename__ = 'pge_usage_points'
    id = db.Column(db.Integer, primary_key=True)
    energy_account_id = db.Column(db.Integer, db.ForeignKey('energy_accounts.id'))
    commodity_type = db.Column(db.Integer)
    measuring_period = db.Column(db.Integer)
    interval_start = db.Column(db.DateTime)
    interval_duration = db.Column(db.Integer)
    interval_value = db.Column(db.Integer)
    flow_direction = db.Column(db.Integer)
    unit_of_measure = db.Column(db.Integer)
    power_of_ten_multiplier = db.Column(db.Integer)
    accumulation_behavior = db.Column(db.Integer)

    def __repr__(self):
        return '<PGEUsagePoint {}>' .format(self.id)

class SolarEdgeUsagePoint(db.Model):
    __tablename__ = 'solar_edge_usage_points'
    id = db.Column(db.Integer, primary_key=True)
    energy_account_id = db.Column(db.Integer, db.ForeignKey('energy_accounts.id'))
    time_unit = db.Column(db.String(50))
    unit_of_measure = db.Column(db.String(50))
    date = db.Column(db.Date)
    value = db.Column(db.Numeric(20, 5))

    def __repr__(self):
        return '<SolarEdgeUsagePoint {}>' .format(self.id)

class CeleryTask(db.Model):
    __tablename__ = 'celery_tasks'
    id = db.Column(db.Integer, primary_key=True)
    energy_account_id = db.Column(db.Integer, db.ForeignKey('energy_accounts.id'))
    task_id = db.Column(db.String(50))
    task_status = db.Column(db.Integer)

    def __repr__(self):
        return '<CeleryTask {}>' .format(self.id)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))
    permissions = relationship("Permission",
                    secondary=permission_associations,
                    backref="roles")

    def __repr__(self):
        return '<Role {}>' .format(self.id)

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    permission = db.Column(db.String(50))

    def __repr__(self):
        return '<Permission {}>' .format(self.id)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    password_hash = db.Column(db.String(128))
    energy_accounts = relationship("EnergyAccount",
                    secondary=energy_accounts,
                    backref="users")
    roles = relationship("Role",
                    secondary=role_associations,
                    backref="users")

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password, 12)

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


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

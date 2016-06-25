# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

from flask_login import UserMixin
from sqlalchemy.orm import relationship

from solarmonitor.extensions import bcrypt, db
import datetime
from datetime import timedelta

today = datetime.datetime.today().date()
seven_days_ago = datetime.datetime.today().date() - timedelta(days=7)

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
    nick_name = db.Column(db.String(255))
    address_one = db.Column(db.String(255))
    address_two = db.Column(db.String(255))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(50))
    pge_bulk_id = db.Column(db.String(50))
    pge_access_token = db.Column(db.String(255))
    solar_edge_site_id = db.Column(db.String(255))
    pge_usage_points = db.relationship('PGEUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    solar_edge_usage_points = db.relationship('SolarEdgeUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    celery_tasks = db.relationship('CeleryTask', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')

    def production_net_usage_graph(self, start_date=seven_days_ago, end_date=today):
        production, labels = self.solar_edge_production_graph(start_date, end_date)
        net_usage = self.pge_incoming_outgoing_combined_graph(start_date, end_date)[0]

        return production, net_usage, labels

    def production_net_usage_percentage_graph(self, start_date=seven_days_ago, end_date=today):
        production, labels = self.solar_edge_production_graph(start_date, end_date)
        net_usage = self.pge_incoming_outgoing_combined_graph(start_date, end_date)[0]

        production_percentage = [(x/(x + y)*100 )for x, y in zip(production, net_usage)]
        production_percentage = [x if x <=100 else 100 for x in production_percentage]

        net_usage_percentage = [100-x for x in production_percentage]

        net_input = [((x/(x + y)) - 1) for x, y in zip(production, net_usage)]
        net_input = [x * 100 if x > 0 else 0 for x in net_input]

        return production_percentage, net_input, net_usage_percentage, labels

    def pge_incoming_outgoing_graph(self, start_date=seven_days_ago, end_date=today):
        from solarmonitor.pge.pge_helpers import PGEHelper
        pge_helper = PGEHelper(start_date, end_date, self.id)

        """Set the variables """
        incoming_data, incoming_labels, outgoing_data, outgoing_labels = pge_helper.get_daily_data_and_labels()

        return incoming_data, outgoing_data, outgoing_labels

    def pge_incoming_outgoing_combined_graph(self, start_date=seven_days_ago, end_date=today):
        from solarmonitor.pge.pge_helpers import PGEHelper
        pge_helper = PGEHelper(start_date, end_date, self.id)

        """Set the variables """
        incoming_data, incoming_labels, outgoing_data, outgoing_labels = pge_helper.get_daily_data_and_labels()

        net_usage = [x - y for x, y in zip(incoming_data, outgoing_data)]

        return net_usage, incoming_labels

    def solar_edge_production_graph(self, start_date=seven_days_ago, end_date=today):
        solar_edge_data_pull = SolarEdgeUsagePoint.query.filter(
            (SolarEdgeUsagePoint.date>=start_date)&
            (SolarEdgeUsagePoint.energy_account_id==self.id)&
            (SolarEdgeUsagePoint.date<=end_date)
            ).order_by(SolarEdgeUsagePoint.date.asc()).all()

        se_energy_data = []
        se_energy_labels = []

        for each in solar_edge_data_pull:
            se_energy_data.append(each.value)
            se_energy_labels.append(each.date.strftime('%Y-%m-%d'))

        se_energy_data = [float(x)/1000 for x in se_energy_data]

        return se_energy_data, se_energy_labels

    def serialize(self):
        return {
            'nick_name': self.nick_name,
            'address_one': self.address_one,
            'address_two': self.address_two,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'pge_bulk_id': self.pge_bulk_id,
            'solar_edge_site_id': self.solar_edge_site_id,
        }


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

# -*- coding: utf-8 -*-
"""User models."""
import datetime as dt

import json
from flask_login import UserMixin
from sqlalchemy.orm import relationship

from solarmonitor.extensions import bcrypt, db
import datetime
from datetime import timedelta
from flask.ext.login import AnonymousUserMixin
from sqlalchemy import func

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


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.full_name = 'Anonymous'

    def log_event(self, event_type=None, level=1, info=None):
        event = AppEvent(
            user_id=1,
            date_time=datetime.datetime.utcnow(),
            event_type=event_type,
            level=level,
            info=info
        )
        db.session.add(event)
        db.session.commit()


class AppEvent(db.Model):
    __tablename__ = 'app_events'
    id = db.Column(db.Integer, primary_key=True)
    date_time = db.Column(db.DateTime)
    event_type = db.Column(db.Integer)
    level = db.Column(db.Integer)
    info = db.Column(db.String(355))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class EnergyEvent(db.Model):
    __tablename__ = 'energy_events'
    id = db.Column(db.Integer, primary_key=True)
    energy_account_id = db.Column(db.Integer, db.ForeignKey('energy_accounts.id'))
    date = db.Column(db.Date)
    event_type = db.Column(db.Integer)
    info = db.Column(db.String(355))

class EnergyAccount(db.Model):
    __tablename__ = 'energy_accounts'
    id = db.Column(db.Integer, primary_key=True)
    energy_events = db.relationship('EnergyEvent', backref="energy_account", lazy='dynamic', cascade="all, delete-orphan")
    nick_name = db.Column(db.String(255))
    address_one = db.Column(db.String(255))
    address_two = db.Column(db.String(255))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(50))
    pge_bulk_id = db.Column(db.String(50))
    pge_subscription_id = db.Column(db.String(50))
    pge_usage_point = db.Column(db.String(50))
    pge_access_token = db.Column(db.String(255))
    pge_refresh_token = db.Column(db.String(255))
    pge_last_date = db.Column(db.DateTime)
    pge_first_date = db.Column(db.DateTime)
    solar_install_date = db.Column(db.DateTime)
    solar_edge_site_id = db.Column(db.String(255))
    pge_usage_points = db.relationship('PGEUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    solar_edge_usage_points = db.relationship('SolarEdgeUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    celery_tasks = db.relationship('CeleryTask', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')

    def energy_events(self, start_date=seven_days_ago, end_date=today, serialize=False):
        events = EnergyEvent.query.filter(
            (EnergyEvent.date <= end_date)&
            (EnergyEvent.date >= start_date)&
            (EnergyEvent.energy_account_id == self.id)
        ).order_by(EnergyEvent.date.desc()).all()

        if serialize:
            serialized_events = []
            for event in events:
                event_dict = {}
                event_dict['date'] = event.date.strftime('%m/%d/%Y')
                event_dict['event_type'] = 'Weather Related' if event.event_type == 1 else 'Panel Related'
                event_dict['info'] = event.info
                event_dict['id'] = event.id
                serialized_events.append(event_dict)
            return json.dumps(serialized_events)

        return events

    def cumulative_usage_graph(self, start_date=seven_days_ago, end_date=today):
        """Graph that shows net usage.
        Ex.
        3) Graph the daily cumulative usage from a date (1/1), on any graph. So if I am graphing 9/1 - 9/19, we do this:

        a) Pull the usage from 1/1 to 8/31 and sum it (either with sum SQL or just adding up the data)

        b) Starting the graph range, start and the cumulative and show each days change.
        This is a line graph similar to the SE production.

        c) Later we can move to a "caching" style db that saves us processing a year of data, but for now, lets just pull the usage data live and see how bad it is in terms of timing.
        for flow_direction 1 means delivered electric and 19 means reversed and sold back to grid. """
        today = datetime.datetime.now()
        first_of_year = datetime.datetime(year=today.year, month=1, day=1)

        if self.solar_install_date and (self.solar_install_date > first_of_year):
            historical_start = self.solar_install_date
        else:
            historical_start = first_of_year


        #sold back to grid
        negative_usage = PGEUsagePoint.query.with_entities(func.sum(PGEUsagePoint.interval_value)).filter(
            (PGEUsagePoint.flow_direction==19)&
            (PGEUsagePoint.interval_start < start_date)&
            (PGEUsagePoint.interval_start >= historical_start)
        ).scalar()

        #used electric
        positive_usage = PGEUsagePoint.query.with_entities(func.sum(PGEUsagePoint.interval_value)).filter(
            (PGEUsagePoint.flow_direction==1)&
            (PGEUsagePoint.interval_start < start_date)&
            (PGEUsagePoint.interval_start >= historical_start)
        ).scalar()

        print positive_usage, negative_usage

        starting_point = positive_usage - negative_usage

        print starting_point

        starting_point = starting_point / (1000*1000)

        original_graph = self.pge_incoming_outgoing_combined_graph(start_date, end_date)

        new_graph = [((x + starting_point), y) for x, y in original_graph]

        return new_graph




    def production_net_usage_graph(self, start_date=seven_days_ago, end_date=today):
        """Solar Edge production vs Combined PGE data"""
        production = self.solar_edge_production_graph(start_date, end_date)
        net_usage = self.pge_incoming_outgoing_combined_graph(start_date, end_date)

        """Before we can output the data, we need to push the data with matching dates together.
        The goal is to have the same data ranges available from both solar edge and PGE but sometimes
        we will only have 10 days of data for pge and 15 days of data for solar edge. Data for the same date
        ranges need to be displayed together, otherwise funky things happen with the chart."""

        #get all the dates for both lists and combine them into one list in date order, removing duplicates, convert to dict
        date_dict = {key:None for key in set([p[1] for p in production] + [n[1] for n in net_usage])}

        for value, date in net_usage:
            date_dict[date] = (value,)

        for value, date in production:
            if not date_dict[date]:
                date_dict[date] = (value, 0)
            else:
                date_dict[date] = (value,) + date_dict[date]

        date_list = sorted(date_dict.items(), key=lambda x: x[0])

        date_list = [(values[0], values[1], labels) if len(values) == 2 else (0, 0, labels) for labels, values in date_list]

        # Returns a list of tuples e.g. [(production, net usage, label)]
        return date_list

    def production_net_usage_percentage_graph(self, start_date=seven_days_ago, end_date=today):
        """Solar Edge Production vs Combined PGE data normalized to 100%"""
        p = self.production_net_usage_graph(start_date, end_date)

        labels = [labels for production, net_usage, labels in p]
        production_percentage = [(x/(x + y)*100) if (x + y) != 0 else 0 for x, y, l in p]
        production_percentage = [x if x <=100 else 100 for x in production_percentage]

        net_usage_percentage = [100-x if x != 0 else 0 for x in production_percentage ]

        net_input = [((x/(x + y)) - 1) if (x + y) != 0 else 0 for x, y, l in p]
        net_input = [x * 100 if x > 0 else 0 for x in net_input]

        return zip(production_percentage, net_input, net_usage_percentage, labels)

    def pge_incoming_outgoing_graph(self, start_date=seven_days_ago, end_date=today):
        from solarmonitor.pge.pge_helpers import PGEHelper
        pge_helper = PGEHelper(start_date, end_date, self.id)

        """Set the variables """
        incoming_data, incoming_labels, outgoing_data, outgoing_labels = pge_helper.get_daily_data_and_labels()

        return zip(incoming_data, outgoing_data, outgoing_labels)

    def pge_incoming_outgoing_combined_graph(self, start_date=seven_days_ago, end_date=today, separate=None, financial=False):
        """Uses the PGEHelper class to return a zipped list of kWh values and datetime objects as a list of tuples.
        If no data is found for a particular day, a value of zero is returned as the kWh part of the tuple."""
        from solarmonitor.pge.pge_helpers import PGEHelper
        pge_helper = PGEHelper(start_date, end_date, self.id)

        """Set the variables """
        incoming_data, incoming_labels, outgoing_data, outgoing_labels = pge_helper.get_daily_data_and_labels()

        net_usage = [x - y for x, y in zip(incoming_data, outgoing_data)]

        positive_usage = [x if x > 0 else 0 for x in net_usage]
        negative_usage = [x if x < 0 else 0 for x in net_usage]

        cost_per_kWh = 0.028780

        if financial:
            net_usage = [((x - y) * cost_per_kWh) for x, y in zip(incoming_data, outgoing_data)]

        if separate:
            return zip(positive_usage, negative_usage, incoming_labels)

        return zip(net_usage, incoming_labels)

    def solar_edge_production_graph(self, start_date=seven_days_ago, end_date=today):
        """Pulls all solar edge data (by day) and returns a zipped list of kWh values and datetime objects as a list of tuples."""
        solar_edge_data_pull = SolarEdgeUsagePoint.query.filter(
            (SolarEdgeUsagePoint.date>=start_date)&
            (SolarEdgeUsagePoint.energy_account_id==self.id)&
            (SolarEdgeUsagePoint.date<=end_date)
            ).order_by(SolarEdgeUsagePoint.date.asc()).all()

        se_energy_data = []
        se_energy_labels = []

        for each in solar_edge_data_pull:
            se_energy_data.append(each.value)
            se_energy_labels.append(each.date)

        se_energy_data = [float(x)/1000 for x in se_energy_data]

        return zip(se_energy_data, se_energy_labels)


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

    def serialize_charts(self, chart, start_date=seven_days_ago, end_date=today, date_format='%m/%d', separate=False, financial=False):
        if chart == 'solar_edge_production_graph':
            solar_edge_production_graph = self.solar_edge_production_graph(start_date, end_date)
            return {
                'se_energy_data': [data for data, labels in solar_edge_production_graph],
                'labels': [labels.strftime(date_format) for data, labels in solar_edge_production_graph]
            }

        elif chart == 'pge_incoming_outgoing_combined_graph':
            if separate:
                pge_incoming_outgoing_combined_graph = self.pge_incoming_outgoing_combined_graph(start_date, end_date, separate)
                return {
                    'net_usage_positive': [pos_data for pos_data, neg_data, labels in pge_incoming_outgoing_combined_graph],
                    'net_usage_negative': [neg_data for pos_data, neg_data, labels in pge_incoming_outgoing_combined_graph],
                    'labels': [labels.strftime(date_format) for pos_data, neg_data, labels in pge_incoming_outgoing_combined_graph]
                }
            if financial:
                pge_incoming_outgoing_combined_graph = self.pge_incoming_outgoing_combined_graph(start_date, end_date, financial=financial)
                return {
                    'net_usage': [data for data, labels in pge_incoming_outgoing_combined_graph],
                    'labels': [labels.strftime(date_format) for data, labels in pge_incoming_outgoing_combined_graph]
                }
            pge_incoming_outgoing_combined_graph = self.pge_incoming_outgoing_combined_graph(start_date, end_date)
            return {
                'net_usage': [data for data, labels in pge_incoming_outgoing_combined_graph],
                'labels': [labels.strftime(date_format) for data, labels in pge_incoming_outgoing_combined_graph]
            }

        elif chart == 'pge_incoming_outgoing_graph':
            pge_incoming_outgoing_graph = self.pge_incoming_outgoing_graph(start_date, end_date)
            return {
                'incoming_data': [inc_data for inc_data, out_data, labels in pge_incoming_outgoing_graph],
                'outgoing_data': [out_data for inc_data, out_data, labels in pge_incoming_outgoing_graph],
                'labels': [labels.strftime(date_format) for inc_data, out_data, labels in pge_incoming_outgoing_graph]
            }

        elif chart == 'cumulative_usage_graph':
            cumulative_usage_graph = self.cumulative_usage_graph(start_date, end_date)
            return {
                'net_usage': [data for data, labels in cumulative_usage_graph],
                'labels': [labels.strftime(date_format) for data, labels in cumulative_usage_graph]
            }

        elif chart == 'production_net_usage_percentage_graph':
            production_net_usage_percentage_graph = self.production_net_usage_percentage_graph(start_date, end_date)
            return {
                'production_percentage': [production_percentage for production_percentage, net_input, net_usage_percentage, labels in production_net_usage_percentage_graph],
                'net_input': [net_input for production_percentage, net_input, net_usage_percentage, labels in production_net_usage_percentage_graph],
                'net_usage_percentage': [net_usage_percentage for production_percentage, net_input, net_usage_percentage, labels in production_net_usage_percentage_graph],
                'labels': [labels.strftime(date_format) for production_percentage, net_input, net_usage_percentage, labels in production_net_usage_percentage_graph]
            }

        elif chart == 'production_net_usage_graph':
            production_net_usage_graph = self.production_net_usage_graph(start_date, end_date)
            return {
                'production': [production for production, net_usage, labels in production_net_usage_graph],
                'net_usage': [net_usage for production, net_usage, labels in production_net_usage_graph],
                'labels': [labels.strftime(date_format) for production, net_usage, labels in production_net_usage_graph]
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
    address_one = db.Column(db.String(64))
    address_two = db.Column(db.String(64))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    zip_code = db.Column(db.String(5))
    password_hash = db.Column(db.String(128))
    app_events = db.relationship('AppEvent', backref="user", lazy='dynamic', cascade="all, delete-orphan")
    energy_accounts = relationship("EnergyAccount",
                    secondary=energy_accounts,
                    backref="users")
    roles = relationship("Role",
                    secondary=role_associations,
                    backref="users")

    def has_role(self, role):
        user_roles = [x.role for x in self.roles]
        return True if role in user_roles else False

    def can(self, permission):
        permissions = []
        for role in self.roles:
            for permission in role:
                list(set(permissions.append(permission.permission)))
        return True if permission in permissions else False

    @property
    def full_address(self):
        if self.address_one and self.city and self.state:
            return '{} {} {}, {} {}'.format(self.address_one, self.address_two, self.city, self.state, self.zip_code)
        elif len(self.energy_accounts) > 0:
            first_account = self.energy_accounts[0]
            if first_account.address_one and first_account.city and first_account.state:
                return '{} {} {}, {} {}'.format(
                    first_account.address_one,
                    first_account.address_two,
                    first_account.city,
                    first_account.state,
                    first_account.zip_code
                )
        else:
            return 'None'

    def log_event(self, event_type=None, level=1, info=None):
        event = AppEvent(
            user_id=self.id,
            date_time=datetime.datetime.utcnow(),
            event_type=event_type,
            level=level,
            info=info
        )
        db.session.add(event)
        db.session.commit()

    @property
    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

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

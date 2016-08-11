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
    pge_subscription_id = db.Column(db.String(50))
    pge_usage_point = db.Column(db.String(50))
    pge_access_token = db.Column(db.String(255))
    pge_refresh_token = db.Column(db.String(255))
    solar_edge_site_id = db.Column(db.String(255))
    pge_usage_points = db.relationship('PGEUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    solar_edge_usage_points = db.relationship('SolarEdgeUsagePoint', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')
    celery_tasks = db.relationship('CeleryTask', backref="energy_account", cascade="all, delete-orphan" , lazy='dynamic')

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

        net_usage_percentage = [100-x for x in production_percentage]

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

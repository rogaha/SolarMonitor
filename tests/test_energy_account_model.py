# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from solarmonitor.extensions import db
from solarmonitor.user.models import User, EnergyAccount, SolarEdgeUsagePoint, PGEUsagePoint
from solarmonitor.solaredge.solaredge_helper import generate_random_solar_edge_data
from solarmonitor.pge.pge_helpers import generate_random_pge_data
from datetime import datetime, timedelta


@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self):
        """Get energy account by ID."""
        energy_account = EnergyAccount(
            address_one='123 Unknown',
            address_two='None',
            city='Sacramento',
            state='CA',
            zip_code='54647',
            )
        db.session.add(energy_account)
        db.session.commit()

        retrieved = EnergyAccount.query.filter_by(id=energy_account.id).first()
        assert retrieved == energy_account

    def test_solar_edge_production_graph(self, user):
        generate_random_solar_edge_data(number_of_data_rows=4, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        se_energy_data, se_energy_labels = user.energy_accounts[0].solar_edge_production_graph(start_date, end_date)

        assert len(se_energy_data) == len(se_energy_labels)
        assert len(se_energy_labels) == 4

    def test_pge_incoming_outgoing_combined_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        net_usage, incoming_labels = user.energy_accounts[0].pge_incoming_outgoing_combined_graph(start_date, end_date)

        assert len(net_usage) == len(incoming_labels)
        assert len(incoming_labels) == 4

    def test_pge_incoming_outgoing_combined_graph2(self, user):
        """If there is no PGE data, we still produce a list of zeroes for the requested date range."""
        generate_random_pge_data(number_of_data_rows=0, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        net_usage, incoming_labels = user.energy_accounts[0].pge_incoming_outgoing_combined_graph(start_date, end_date)

        assert len(net_usage) == len(incoming_labels)
        assert len(incoming_labels) == 4

    def test_pge_incoming_outgoing_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        incoming_data, outgoing_data, labels = user.energy_accounts[0].pge_incoming_outgoing_graph(start_date, end_date)

        assert len(incoming_data) == len(labels)
        assert len(outgoing_data) == len(labels)
        assert len(labels) == 4

    def test_production_net_usage_percentage_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=4, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        production_percentage, net_input, net_usage_percentage, labels = user.energy_accounts[0].production_net_usage_percentage_graph(start_date, end_date)

        assert len(production_percentage) == len(labels)
        assert len(net_input) == len(labels)
        assert len(net_usage_percentage) == len(labels)
        assert len(labels) == 4

    def test_production_net_usage_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=4, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        production, net_usage, labels = user.energy_accounts[0].production_net_usage_graph(start_date, end_date)

        assert len(production) == len(labels)
        assert len(net_usage) == len(labels)
        assert len(labels) == 4

    def test_production_net_usage_percentage_graph_unequal_input2(self, user):
        """This tests against the case, where we have 10 days of SE data, but only 5 days of PGE data.
        The graph should shorten to match the lowest range of available data.
        """
        generate_random_pge_data(number_of_data_rows=12, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=6, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        production_percentage, net_input, net_usage_percentage, labels = user.energy_accounts[0].production_net_usage_percentage_graph(start_date, end_date)

        assert len(production_percentage) == len(labels)
        assert len(net_input) == len(labels)
        assert len(net_usage_percentage) == len(labels)
        assert len(labels) == 4


    def test_production_net_usage_percentage_graph_unequal_input3(self, user):
        """This tests against the case, where we have 10 days of SE data, but only 5 days of PGE data.
        The graph should shorten to match the lowest range of available data.
        """
        generate_random_pge_data(number_of_data_rows=0, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)
        generate_random_solar_edge_data(number_of_data_rows=6, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=6)
        production_percentage, net_input, net_usage_percentage, labels = user.energy_accounts[0].production_net_usage_percentage_graph(start_date, end_date)

        assert len(production_percentage) == len(labels)
        assert len(net_input) == len(labels)
        assert len(net_usage_percentage) == len(labels)
        assert len(labels) == 6








    def next():
        pass

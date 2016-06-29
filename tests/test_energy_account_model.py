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
        result = user.energy_accounts[0].serialize_charts('solar_edge_production_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['se_energy_data']) == 4

    def test_pge_incoming_outgoing_combined_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['net_usage']) == 4

    def test_pge_incoming_outgoing_combined_graph2(self, user):
        """If there is no PGE data, we still produce a list of zeroes for the requested date range."""
        generate_random_pge_data(number_of_data_rows=0, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['net_usage']) == 4

    def test_pge_incoming_outgoing_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['incoming_data']) == 4
        assert len(result['outgoing_data']) == 4

    def test_production_net_usage_percentage_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=4, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('production_net_usage_percentage_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['net_input']) == 4
        assert len(result['net_usage_percentage']) == 4
        assert len(result['production_percentage']) == 4

    def test_production_net_usage_graph(self, user):
        generate_random_pge_data(number_of_data_rows=96, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=4, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('production_net_usage_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['net_usage']) == 4
        assert len(result['production']) == 4


    def test_production_net_usage_percentage_graph_unequal_input(self, user):
        """This tests against the case, where we have 10 days of SE data, but only 5 days of PGE data.
        The graph should shorten to match the lowest range of available data.
        """
        generate_random_pge_data(number_of_data_rows=240, account_id=user.energy_accounts[0].id, numbers_of_days_ago=20)
        generate_random_solar_edge_data(number_of_data_rows=10, account_id=user.energy_accounts[0].id, numbers_of_days_ago=20)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        production_percentage, net_input, net_usage_percentage, labels = user.energy_accounts[0].production_net_usage_percentage_graph(start_date, end_date)

        assert len(production_percentage) == len(labels)
        assert len(net_input) == len(labels)
        assert len(net_usage_percentage) == len(labels)
        assert len(labels) == 4


    def test_production_net_usage_percentage_graph_unequal_input2(self, user):
        """This tests against the case, where we have 10 days of SE data, but only 5 days of PGE data.
        The graph should shorten to match the lowest range of available data.
        """
        generate_random_pge_data(number_of_data_rows=12, account_id=user.energy_accounts[0].id, numbers_of_days_ago=4)
        generate_random_solar_edge_data(number_of_data_rows=6, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=4)
        result = user.energy_accounts[0].serialize_charts('production_net_usage_percentage_graph', start_date, end_date)

        assert len(result['labels']) == 4
        assert len(result['net_input']) == 4
        assert len(result['net_usage_percentage']) == 4
        assert len(result['production_percentage']) == 4


    def test_production_net_usage_percentage_graph_unequal_input3(self, user):
        """This tests against the case, where we have 10 days of SE data, but only 5 days of PGE data.
        The graph should shorten to match the lowest range of available data.
        """
        generate_random_pge_data(number_of_data_rows=0, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)
        generate_random_solar_edge_data(number_of_data_rows=6, account_id=user.energy_accounts[0].id, numbers_of_days_ago=6)

        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=6)
<<<<<<< HEAD
        result = user.energy_accounts[0].serialize_charts('production_net_usage_percentage_graph', start_date, end_date)

        assert len(result['labels']) == 6
        assert len(result['net_input']) == 6
        assert len(result['net_usage_percentage']) == 6
        assert len(result['production_percentage']) == 6
=======
        production_percentage, net_input, net_usage_percentage, labels = user.energy_accounts[0].production_net_usage_percentage_graph(start_date, end_date)

        assert len(production_percentage) == len(labels)
        assert len(net_input) == len(labels)
        assert len(net_usage_percentage) == len(labels)
        assert len(labels) == 6
>>>>>>> b93938fba1378eeec0bb8ebae107e900f56dc4df

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Management script."""
import os
from glob import glob
from subprocess import call

from flask import render_template, url_for
from flask_migrate import Migrate, MigrateCommand
from flask_script import Command, Manager, Option, Server, Shell
from flask_script.commands import Clean, ShowUrls

from solarmonitor.app import create_app
from solarmonitor.mailgun.mailgun_api import send_html_email
from solarmonitor.settings import DevConfig, ProdConfig, Config
from solarmonitor.user.models import User, EnergyAccount
from solarmonitor.extensions import db
from solarmonitor.pge.pge import Api, ClientCredentials
from solarmonitor.solaredge.se_api import SolarEdgeApi
from solarmonitor.celerytasks.se_tasks import process_se_data
import json

import datetime
from datetime import timedelta

CONFIG = ProdConfig if os.environ.get('SOLARMONITOR_ENV') == 'prod' else DevConfig
HERE = os.path.abspath(os.path.dirname(__file__))
TEST_PATH = os.path.join(HERE, 'tests')

app = create_app(CONFIG)
manager = Manager(app)
#migrate = Migrate(app, db)

cc = ClientCredentials(CONFIG.PGE_CLIENT_CREDENTIALS, CONFIG.SSL_CERTS)
api = Api(CONFIG.SSL_CERTS)


def _make_context():
    """Return context dict for a shell session so you can access app, db, and the User model by default."""
    return {'app': app, 'db': db, 'User': User}


@manager.command
def test():
    """Run the tests."""
    import pytest
    exit_code = pytest.main([TEST_PATH, '--verbose'])
    return exit_code


class Lint(Command):
    """Lint and check code style with flake8 and isort."""

    def get_options(self):
        """Command line options."""
        return (
            Option('-f', '--fix-imports', action='store_true', dest='fix_imports', default=False,
                   help='Fix imports using isort, before linting'),
        )

    def run(self, fix_imports):
        """Run command."""
        skip = ['requirements']
        root_files = glob('*.py')
        root_directories = [name for name in next(os.walk('.'))[1] if not name.startswith('.')]
        files_and_directories = [arg for arg in root_files + root_directories if arg not in skip]

        def execute_tool(description, *args):
            """Execute a checking tool with its arguments."""
            command_line = list(args) + files_and_directories
            print('{}: {}'.format(description, ' '.join(command_line)))
            rv = call(command_line)
            if rv is not 0:
                exit(rv)

        if fix_imports:
            execute_tool('Fixing import order', 'isort', '-rc')
        execute_tool('Checking code style', 'flake8')

@manager.command
def run_server():
    app.run(host='0.0.0.0', debug=True)

@manager.command
def email_users_graph_data():
    energy_accounts = EnergyAccount.query.all()
    print '\n \n \n \n RUNNING EMAIL NIGHTLY TASK \n \n \n \n \n '


    end_date = datetime.datetime.today().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=15)

    for account in energy_accounts:
        for user in account.users:
            print 'user: {}, energy_account: {}'.format(user.first_name, account.id)
            html = render_template('email/nightly_update.html', energy_account=account, user=user, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
            send_html_email('Solarmonitor Admin <admin@solarmonitor.com>', 'Your daily update', user.email, html)


@manager.command
def bulk_download_pge_data(number_of_days_history=7):
    client_credentials = cc.get_client_access_token('https://api.pge.com/datacustodian/oauth/v2/token')

    today = datetime.datetime.today().date() + timedelta(days=1)
    x_days_ago = datetime.datetime.today().date() - timedelta(days=number_of_days_history)

    energy_accounts = EnergyAccount.query.all()
    for account in energy_accounts:
        start_date = x_days_ago
        end_date = today

        bulk_id = account.pge_bulk_id
        bulk_url =  'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Bulk/{}'.format(bulk_id)
        bulk_url += '?published-min={}&published-max={}' .format(
            start_date.strftime('%Y-%m-%dT%H:%m:%SZ'),
            end_date.strftime('%Y-%m-%dT%H:%m:%SZ')
        )
        """Logging"""
        print api.simple_request(bulk_url, client_credentials[u'client_access_token']), 'BULK ID: {} \n Start: {} End: {} \n\n'.format(
            bulk_id,
            start_date,
            end_date
        )

@manager.command
def bulk_download_solar_edge_data(number_of_days_history=7):
    today = datetime.datetime.today().date() + timedelta(days=1)
    x_days_ago = datetime.datetime.today().date() - timedelta(days=number_of_days_history)

    energy_accounts = EnergyAccount.query.all()
    for account in energy_accounts:
        start_date = x_days_ago
        end_date = today

        se = SolarEdgeApi()
        se_energy = json.loads(
            se.site_energy_measurements(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                '237846',
                'DAY'
            ).text
        )

        task = process_se_data.delay(se_energy, account.id)

        """Logging"""
        print 'Account ID: {} \n Start: {} End: {} \n\n'.format(
            account.id,
            start_date,
            end_date
        )


manager.add_command('server', Server())
manager.add_command('shell', Shell(make_context=_make_context))
manager.add_command('db', MigrateCommand)
manager.add_command('urls', ShowUrls())
manager.add_command('clean', Clean())
manager.add_command('lint', Lint())
manager.add_command('run', Lint())

if __name__ == '__main__':
    manager.run()

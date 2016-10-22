# -*- coding: utf-8 -*-
"""User dashboard views."""
from flask import Blueprint, render_template, session, flash, redirect, request, url_for, jsonify
from flask_login import login_required, current_user
from solarmonitor.extensions import login_manager
from solarmonitor.settings import Config
from solarmonitor.celerytasks.pgetasks import process_xml
from solarmonitor.celerytasks.se_tasks import process_se_data
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
from solarmonitor.pge.pge_helpers import PGEHelper
from solarmonitor.solaredge.se_api import SolarEdgeApi
from solarmonitor.mailgun.mailgun_api import send_email
from solarmonitor.user.models import User, PGEUsagePoint, CeleryTask, SolarEdgeUsagePoint, EnergyAccount, EnergyEvent
from solarmonitor.user.dashboard.forms import EventAddForm
from solarmonitor.public.forms import DateSelectForm, DownloadDataForm
from solarmonitor.extensions import db
from solarmonitor.utils import try_parsing_date
import requests
import json

from jxmlease import parse

import datetime
from datetime import datetime, timedelta, date
from calendar import monthrange

config = Config()
cc = ClientCredentials(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)
api = Api(config.SSL_CERTS)
oauth = OAuth2(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)

blueprint = Blueprint('dashboard', __name__, url_prefix='/users/dashboard', static_folder='../static')

@blueprint.route('', methods=['GET', 'POST'])
@blueprint.route('/<modify>/<int:id>', methods=['GET', 'POST'])
@login_required
def home(modify=None, id=None):
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home'))]
    heading = 'Dashboard'

    start_date = datetime.today().date() - timedelta(days=8)
    end_date = datetime.today().date() - timedelta(days=1)


    """The data for each chart needs to be calculated here, otherwise the calculations
    Are performed for each occurrence of a data set. This also makes the template
    Code Neater"""
    #TODO assumes for now that we want only the first energy account.
    prod_net_usg_pct = current_user.energy_accounts[0].serialize_charts('production_net_usage_percentage_graph', start_date, end_date)

    prod_net_usg = current_user.energy_accounts[0].serialize_charts('production_net_usage_graph', start_date, end_date)

    prod_comb = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date, separate=True)

    financial = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date, financial=True)

    cumulative = current_user.energy_accounts[0].serialize_charts('cumulative_usage_graph', start_date, end_date)

    events = current_user.energy_accounts[0].energy_events(start_date, end_date)

    if current_user.energy_accounts[0].solar_install_date:
        solar_install_date = current_user.energy_accounts[0].solar_install_date.strftime('%m/%d/%Y')
    else:
        solar_install_date = None

    form = EventAddForm()

    if modify == 'del':
        event = EnergyEvent.query.filter_by(id=id).first()
        db.session.delete(event)
        db.session.commit()
        flash('Energy event deleted')
        current_user.log_event(info="Energy event deleted")
        return redirect(url_for('dashboard.home'))

    if form.validate_on_submit():
        energy_event = EnergyEvent(
            info=form.info.data,
            date=try_parsing_date(form.date.data),
            event_type=form.event_type.data,
            energy_account_id=current_user.energy_accounts[0].id
        )
        db.session.add(energy_event)
        db.session.commit()
        flash('New energy event added!')
        current_user.log_event(info="Energy event added")
        return redirect(url_for('dashboard.home'))


    return render_template('users/dashboard/home.html',
        prod_net_usg_pct=prod_net_usg_pct,
        prod_net_usg=prod_net_usg,
        prod_comb=prod_comb,
        financial=financial,
        cumulative=cumulative,
        account_id=current_user.energy_accounts[0].id,
        solar_install_date=solar_install_date,
        breadcrumbs=breadcrumbs, heading=heading,
        events=events,
        form=form
        )

@blueprint.route('/pull-ytd', methods=['GET', 'POST'])
@login_required
def pull_ytd():
    for energy_account in current_user.energy_accounts:
        """First find the whole date range to pull data."""
        end_date = datetime.now() if energy_account.pge_last_date == None else energy_account.pge_last_date
        start_date = datetime(year=datetime.now().year, month=1, day=1)

        for month in range(start_date.month, (end_date.month+1)):
            """For the given date range, break into month chunks and pull PGE Data"""
            week_day, last_day = monthrange(start_date.year, month)

            start_date = datetime(year=start_date.year, month=month, day=1)
            end_date = datetime(year=start_date.year, month=month, day=last_day)

            print start_date, end_date

            process_xml.delay(energy_account, start_date, end_date, user_id=current_user.id)


    return redirect(url_for('dashboard.charts'))

@blueprint.route('/account', methods=['GET', 'POST'])
@blueprint.route('/account/<modify>', methods=['GET', 'POST'])
@login_required
def account(modify=None):
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('Account', 'user', url_for('dashboard.account'))]
    heading = 'Dashboard'
    if modify == 'del_pge':
        current_user.energy_accounts[0].pge_access_token = None
        current_user.energy_accounts[0].pge_refresh_token = None
        current_user.energy_accounts[0].pge_subscription_id = None
        current_user.energy_accounts[0].pge_usage_point = None
        db.session.commit()
        flash('PGE connection deleted on SDP energy account. ')
        return redirect(url_for('dashboard.account'))

    return render_template('users/dashboard/account.html',
        energy_accounts=current_user.energy_accounts,
        breadcrumbs=breadcrumbs, heading=heading,
        )

@blueprint.route('/authorizations', methods=['GET', 'POST'])
@blueprint.route('/authorizations/pge/<start_oauth>', methods=['GET', 'POST'])
@login_required
def authorizations(start_oauth=None):
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')),
                   ('Account', 'user', url_for('dashboard.account')),
                   ('Authorizations', 'user', url_for('dashboard.authorizations'))]
    heading = 'Authorizations'

    if start_oauth:
        #See settings.py for more info on this.
        return redirect(config.PGE_DATA_CUSTODIAN_URL, code=302)

    return render_template('users/dashboard/authorizations.html',
        energy_accounts=current_user.energy_accounts,
        breadcrumbs=breadcrumbs, heading=heading,
        )


@blueprint.route('/graph/update/<int:account_id>/<start_date>/<end_date>', methods=['GET', 'POST'])
@login_required
def graph_update(account_id=None, start_date=None, end_date=None):
    energy_account = EnergyAccount.query.filter_by(id=account_id).first()

    s_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    e_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    result = {
        'production_net_usage_percentage_graph': energy_account.serialize_charts('production_net_usage_percentage_graph', s_date, e_date),
        'production_net_usage_graph': energy_account.serialize_charts('production_net_usage_graph', s_date, e_date),
        'net_usage_separated': energy_account.serialize_charts('pge_incoming_outgoing_combined_graph', s_date, e_date, separate=True),
        'cumulative': energy_account.serialize_charts('cumulative_usage_graph', s_date, e_date)
    }

    return jsonify(result)

@blueprint.route('/energy_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def modify_energy_account(account_id=None):
    energy_account = EnergyAccount.query.filter_by(id=account_id).first()
    energy_account.nick_name = request.form['nick_name']
    energy_account.address_one = request.form['address_one']
    energy_account.address_two = request.form['address_two']
    energy_account.city = request.form['city']
    energy_account.state = request.form['state']
    energy_account.zip_code = request.form['zip_code']
    energy_account.pge_bulk_id = request.form['pge_bulk_id']
    energy_account.solar_edge_site_id = request.form['solar_edge_site_id']
    energy_account.solar_edge_api_key = request.form['solar_edge_api_key']
    if not request.form['solar_install_date']:
        energy_account.solar_install_date = None
    else:
        try:
            energy_account.solar_install_date = try_parsing_date(request.form['solar_install_date'])
        except:
            flash('Date not a recognized format')
    db.session.commit()

    result = energy_account.serialize()

    return jsonify(result)

@blueprint.route('/charts', methods=['GET', 'POST'])
@blueprint.route('/charts/session/<modify>', methods=['GET', 'POST'])
@login_required
def charts(modify=None):
    """PGE Electricity Usage Chart"""
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('PGE', 'bar-chart-o', url_for('dashboard.charts'))]
    heading = 'PGE Electricity'

    date_select_form = DateSelectForm(prefix="date_select_form")
    download_data_form = DownloadDataForm(prefix="download_data_form")

    if modify == 'clear':
        session.pop('start_date_pge', None)
        session.pop('end_date_pge', None)
        session.pop('data_time_unit', None)
        return redirect(url_for('dashboard.charts'))

    if modify == 'delete-data':
        PGEUsagePoint.query.filter_by(energy_account_id=current_user.energy_accounts[0].id).delete()
        db.session.commit()
        return redirect(url_for('dashboard.charts'))

    if 'start_date_pge' in session:
        start_date_pge = datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
    else:
        start_date_pge = datetime.now() - timedelta(days=1)

    if 'end_date_pge' in session:
        end_date_pge = datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)
    else:
        end_date_pge = datetime.now()

    if date_select_form.validate_on_submit():
        session['data_time_unit'] = date_select_form.data_time_unit.data
        session['start_date_pge'] = date_select_form.start_date.data
        session['end_date_pge'] = date_select_form.end_date.data
        start_date_pge = datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
        end_date_pge = datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)
        return redirect(url_for('dashboard.charts'))

    if download_data_form.validate_on_submit():

        session['start_date_pge'] = download_data_form.start_date.data
        session['end_date_pge'] = download_data_form.end_date.data

        start_date_pge = datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
        end_date_pge = datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)

        process_xml.delay(current_user.energy_accounts[0], start_date_pge, end_date_pge, user_id=current_user.id)
        flash('Data processing')
        return redirect(url_for('dashboard.charts'))

    pge_inc_outg_grph = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_graph', start_date_pge, end_date_pge)

    pge_inc_outg_grph_combnd = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date_pge, end_date_pge)

    return render_template('users/dashboard/data_chart.html',
        breadcrumbs=breadcrumbs,
        heading=heading,
        date_select_form=date_select_form,
        download_data_form=download_data_form,
        pge_inc_outg_grph=pge_inc_outg_grph,
        pge_inc_outg_grph_combnd=pge_inc_outg_grph_combnd,
        start_date=start_date_pge,
        end_date=end_date_pge
    )

@blueprint.route('/solaredge', methods=['GET', 'POST'])
@blueprint.route('/solaredge/<modify>', methods=['GET', 'POST'])
@login_required
def solar_edge(modify=None):
    """Solar Edge API"""
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('Solar Edge', 'bar-chart-o', url_for('dashboard.solar_edge'))]
    heading = 'Solar Edge Electricity'

    energy_account = current_user.energy_accounts[0]

    date_select_form = DateSelectForm(prefix="date_select_form")
    download_data_form = DownloadDataForm(prefix="download_data_form")

    if modify == 'clear':
        session.pop('start_date_se', None)
        session.pop('end_date_se', None)
        session.pop('data_time_unit_se', None)
        session.pop('se_energy_data', None)
        session.pop('se_energy_labels', None)
        return redirect(url_for('dashboard.solar_edge'))

    if modify == 'delete-data':
        session.pop('start_date_se', None)
        session.pop('end_date_se', None)
        session.pop('data_time_unit_se', None)
        session.pop('se_energy_data', None)
        session.pop('se_energy_labels', None)
        SolarEdgeUsagePoint.query.filter_by(energy_account_id=energy_account.id).delete()
        db.session.commit()
        return redirect(url_for('dashboard.solar_edge'))

    """Set some default dates if nothing has been entered in the form."""
    if 'start_date_se' in session:
        start_date_se = datetime.strptime(session['start_date_se'], '%Y-%m-%d')
    else:
        start_date_se = datetime.now() - timedelta(days=1)

    if 'end_date_se' in session:
        end_date_se = datetime.strptime(session['end_date_se'], '%Y-%m-%d')
    else:
        end_date_se = datetime.now()

    solar_edge_production_graph = energy_account.serialize_charts('solar_edge_production_graph', start_date_se.date(), end_date_se.date())

    session['se_energy_data'] = solar_edge_production_graph['se_energy_data']
    session['se_energy_labels'] = solar_edge_production_graph['labels']

    """Load the form data into the session to save user selection"""
    if date_select_form.validate_on_submit():
        session['data_time_unit_se'] = date_select_form.data_time_unit.data
        session['start_date_se'] = date_select_form.start_date.data
        session['end_date_se'] = date_select_form.end_date.data

        try:
            start_date_se = datetime.strptime(session['start_date_se'], '%Y-%m-%d')
            end_date_se = datetime.strptime(session['end_date_se'], '%Y-%m-%d')
        except:
            flash('Date entered, not in correct format.')
            return redirect(url_for('dashboard.solar_edge'))

        return redirect(url_for('dashboard.solar_edge'))

    if download_data_form.validate_on_submit():
        session['start_date_se'] = download_data_form.start_date.data
        session['end_date_se'] = download_data_form.end_date.data

        try:
            start_date_se = datetime.strptime(session['start_date_se'], '%Y-%m-%d')
            end_date_se = datetime.strptime(session['end_date_se'], '%Y-%m-%d')
        except:
            flash('Date entered, not in correct format.')
            return redirect(url_for('dashboard.solar_edge'))

        se = SolarEdgeApi(energy_account)

        if 'data_time_unit_se' in session:
            time_unit = 'DAY' if session['data_time_unit_se'] == 'Daily' else 'HOUR'
            se_energy = json.loads(se.site_energy_measurements(start_date_se.strftime('%Y-%m-%d'), end_date_se.strftime('%Y-%m-%d'), energy_account.solar_edge_site_id, time_unit).text)
        else:
            se_energy = json.loads(se.site_energy_measurements(start_date_se.strftime('%Y-%m-%d'), end_date_se.strftime('%Y-%m-%d'), energy_account.solar_edge_site_id).text)

        """Send the data returned by the API to celery for async processing."""
        task = process_se_data.delay(se_energy, energy_account.id)

        return redirect(url_for('dashboard.solar_edge'))

    date_select_form.start_date.data = start_date_se.strftime('%Y-%m-%d')
    date_select_form.end_date.data = end_date_se.strftime('%Y-%m-%d')

    return render_template('users/dashboard/solar_edge.html',
        date_select_form=date_select_form,
        download_data_form=download_data_form,
        breadcrumbs=breadcrumbs,
        heading=heading
        )

@blueprint.route('/status/<task_id>', methods=['GET', 'POST'])
@blueprint.route('/status/<task_id>/<start_date>/<end_date>', methods=['GET', 'POST'])
@blueprint.route('/status/<task_id>/<change_status>', methods=['GET', 'POST'])
def taskstatus(task_id=None, change_status=None, start_date=None, end_date=None):
    if change_status == "mark_complete":
        celery_task = CeleryTask.query.filter_by(task_id=task_id).first()
        celery_task.task_status = 1
        db.session.commit()
        response = {'response': 'task {} completed'.format(task_id)}
        return jsonify(response)

    if task_id == 'events':
        return current_user.energy_accounts[0].energy_events(
            start_date=try_parsing_date(start_date),
            end_date=try_parsing_date(end_date),
            serialize=True
        )

    if task_id == "task_check":
        unfinished_tasks = CeleryTask.query.filter(
            (CeleryTask.task_status==0)&
            (CeleryTask.energy_account_id==current_user.energy_accounts[0].id)
            ).all()

        unfinished_tasks_dict = {}
        for task in unfinished_tasks:
            unfinished_tasks_dict[task.id] = task.task_id

        return jsonify(unfinished_tasks_dict)


    task = process_xml.AsyncResult(task_id)
    if task.state == 'PENDING':

        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

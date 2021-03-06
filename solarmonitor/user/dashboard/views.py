# -*- coding: utf-8 -*-
"""User dashboard views."""
from flask import Blueprint, render_template, session, flash, redirect, request, url_for, jsonify
from flask_login import login_required, current_user
from solarmonitor.extensions import login_manager
from solarmonitor.settings import Config
from solarmonitor.celerytasks.pgetasks import process_xml
from solarmonitor.celerytasks.se_tasks import process_se_data
from solarmonitor.celerytasks.enphase_tasks import process_enphase_data
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
from solarmonitor.utils import requires_roles
from solarmonitor.pge.pge_helpers import PGEHelper
from solarmonitor.solaredge.se_api import SolarEdgeApi
from solarmonitor.enphase.enphase_api import EnphaseApi
from solarmonitor.mailgun.mailgun_api import send_email
from solarmonitor.user.models import User, PGEUsagePoint, CeleryTask, SolarEdgeUsagePoint, EnergyAccount, EnergyEvent
from solarmonitor.user.dashboard.forms import EventAddForm
from solarmonitor.public.forms import DateSelectForm, DownloadDataForm
from solarmonitor.extensions import db
from solarmonitor.utils import try_parsing_date, pull_chunks, pull_solar_chunks
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
    # TODO assumes for now that we want only the first energy account.

    prod_net_usg = current_user.energy_accounts[0].serialize_charts('production_net_usage_graph', start_date, end_date)

    prod_comb = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date, separate=True)

    financial = current_user.energy_accounts[0].serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date, financial=True)

    cumulative = current_user.energy_accounts[0].serialize_charts('cumulative_usage_graph', start_date, end_date)

    comparison_graph = current_user.energy_accounts[0].serialize_charts('comparison_graph', start_date, end_date)

    comparison_graph_solar = current_user.energy_accounts[0].serialize_charts('comparison_graph_solar', start_date, end_date)

    print comparison_graph_solar
    if cumulative:
        financial_cumulative = [int(float(x) * 0.23627) for x in cumulative['net_usage']]
        financial_min = round(financial_cumulative[0] * 2, -1) / 2
        financial_max = round(financial_cumulative[-1] * 2, -1) / 2
        financial_step_value = (financial_max - financial_min) / 10
    else:
        financial_min = 0
        financial_max = 100
        financial_step_value = 10

    events = current_user.energy_accounts[0].energy_events(start_date, end_date)

    if current_user.energy_accounts[0].solar_install_date:
        solar_install_date = current_user.energy_accounts[0].solar_install_date.strftime('%m/%d/%Y')
    else:
        solar_install_date = datetime(year=datetime.now().year, month=1, day=1).strftime('%m/%d/%Y')

    form = EventAddForm()

    if modify == 'del':
        event = EnergyEvent.query.filter_by(id=id).first()
        db.session.delete(event)
        db.session.commit()
        flash('Energy event deleted', 'info')
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
        flash('New energy event added! ({})'.format(energy_event.info), 'info')
        current_user.log_event(info="Energy event added")
        return redirect(url_for('dashboard.home'))

    return render_template('users/dashboard/home.html',
                           prod_net_usg=prod_net_usg,
                           prod_comb=prod_comb,
                           comparison_graph=comparison_graph,
                           comparison_graph_solar=comparison_graph_solar,
                           financial=financial,
                           financial_min=financial_min,
                           financial_max=financial_max,
                           financial_step_value=financial_step_value,
                           cumulative=cumulative,
                           account_id=current_user.energy_accounts[0].id,
                           solar_install_date=solar_install_date,
                           breadcrumbs=breadcrumbs, heading=heading,
                           events=events,
                           form=form)


@blueprint.route('/select-solar', methods=['GET', 'POST'])
@login_required
def select_solar():
    form = request.form
    print form
    if form['solar_provider'] == 'enphase':
        return redirect(url_for('dashboard.authorizations', start_oauth='enphase'))


@blueprint.route('/hide_pge_nag', methods=['GET', 'POST'])
@login_required
def hide_pge_nag():
    current_user.energy_accounts[0].pge_nag = 0
    db.session.commit()
    return jsonify({
        'result': 'ok'
    })

@blueprint.route('/hide_solar_nag', methods=['GET', 'POST'])
@login_required
def hide_solar_nag():
    current_user.energy_accounts[0].solar_nag = 0
    db.session.commit()
    return jsonify({
        'result': 'ok'
    })


@blueprint.route('/pull-ytd', methods=['GET', 'POST'])
@blueprint.route('/pull-ytd/<pull_type>', methods=['GET', 'POST'])
@login_required
def pull_ytd(pull_type=None):
    if session.get('select_user', None):
        user = User.query.filter_by(id=session['select_user']).first()
        energy_account = user.energy_accounts[0]
    else:
        energy_account = current_user.energy_accounts[0]

    end_date = datetime.now() if energy_account.pge_last_date is None else energy_account.pge_last_date
    start_date = datetime(year=datetime.now().year, month=1, day=1)

    if pull_type == 'solar':
        pull_solar_chunks(start_date, end_date, current_user)
        return redirect(url_for('dashboard.solar_edge'))

    pull_chunks(start_date, end_date, current_user)

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
        current_user.energy_accounts[0].pge_nag = 1
        db.session.commit()
        flash('PGE connection deleted on SDP energy account.', 'info')
        return redirect(url_for('dashboard.account'))

    if modify == 'del_enphase':
        current_user.energy_accounts[0].enphase_user_id = None
        current_user.energy_accounts[0].enphase_system_id = None
        db.session.commit()
        flash('Enphase connection deleted on SDP energy account.', 'info')
        return redirect(url_for('dashboard.account'))

    return render_template('users/dashboard/account.html',
                           energy_accounts=current_user.energy_accounts,
                           breadcrumbs=breadcrumbs, heading=heading,)


@blueprint.route('/authorizations', methods=['GET', 'POST'])
@blueprint.route('/authorizations/pge/<start_oauth>', methods=['GET', 'POST'])
@login_required
def authorizations(start_oauth=None):
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')),
                   ('Account', 'user', url_for('dashboard.account')),
                   ('Authorizations', 'user', url_for('dashboard.authorizations'))]
    heading = 'Authorizations'
    if start_oauth == 'enphase':
        return redirect(config.ENPHASE_AUTHORIZATION_URL, code=302)

    if start_oauth:
        # See settings.py for more info on this.
        return redirect(config.PGE_DATA_CUSTODIAN_URL, code=302)

    return render_template('users/dashboard/authorizations.html',
                           energy_accounts=current_user.energy_accounts,
                           breadcrumbs=breadcrumbs, heading=heading)


@blueprint.route('/graph/update/<int:account_id>/<start_date>/<end_date>', methods=['GET', 'POST'])
@login_required
def graph_update(account_id=None, start_date=None, end_date=None):
    energy_account = EnergyAccount.query.filter_by(id=account_id).first()

    s_date = try_parsing_date(start_date).date()
    e_date = try_parsing_date(end_date).date()

    result = {
        'production_net_usage_graph': energy_account.serialize_charts('production_net_usage_graph', s_date, e_date),
        'net_usage_separated': energy_account.serialize_charts('pge_incoming_outgoing_combined_graph', s_date, e_date, separate=True),
        'cumulative': energy_account.serialize_charts('cumulative_usage_graph', s_date, e_date),
        'comparison_graph': energy_account.serialize_charts('comparison_graph', s_date, e_date),
        'comparison_graph_solar': energy_account.serialize_charts('comparison_graph_solar', s_date, e_date)
    }

    return jsonify(result)


@blueprint.route('/energy_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def modify_energy_account(account_id=None):
    energy_account = EnergyAccount.query.filter_by(id=account_id).first()
    if request.form.get('nick_name', None):
        energy_account.nick_name = request.form['nick_name']
    if request.form.get('address_one', None):
        energy_account.address_one = request.form['address_one']
    if request.form.get('address_two', None):
        energy_account.address_two = request.form['address_two']
    if request.form.get('city', None):
        energy_account.city = request.form['city']
    if request.form.get('state', None):
        energy_account.state = request.form['state']
    if request.form.get('zip_code', None):
        energy_account.zip_code = request.form['zip_code']
    # energy_account.pge_bulk_id = request.form['pge_bulk_id'] TODO Removed temporarily
    if request.form.get('solar_edge_site_id', None):
        energy_account.solar_edge_site_id = request.form['solar_edge_site_id']
    if request.form.get('solar_edge_api_key', None):
        energy_account.solar_edge_api_key = request.form['solar_edge_api_key']
    if request.form.get('solar_install_date', None) is None:
        energy_account.solar_install_date = None
    else:
        try:
            energy_account.solar_install_date = try_parsing_date(request.form['solar_install_date'])
        except:
            flash('Date not a recognized format', 'info')
    db.session.commit()

    result = energy_account.serialize()

    return jsonify(result)


@blueprint.route('/charts', methods=['GET', 'POST'])
@blueprint.route('/charts/session/<modify>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def charts(modify=None):
    """PGE Electricity Usage Chart"""
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('PGE', 'bar-chart-o', url_for('dashboard.charts'))]
    heading = 'PGE Electricity'

    date_select_form = DateSelectForm(prefix="date_select_form")
    download_data_form = DownloadDataForm(prefix="download_data_form")

    if session.get('select_user', None):
        user = User.query.filter_by(id=session['select_user']).first()
        energy_account = user.energy_accounts[0]
    else:
        energy_account = current_user.energy_accounts[0]

    if modify == 'clear':
        session.pop('start_date_pge', None)
        session.pop('end_date_pge', None)
        session.pop('data_time_unit', None)
        return redirect(url_for('dashboard.charts'))

    if modify == 'delete-data':
        PGEUsagePoint.query.filter_by(energy_account_id=current_user.energy_accounts[0].id).delete()
        energy_account.pge_first_date = None
        energy_account.pge_last_date = None
        db.session.commit()
        return redirect(url_for('dashboard.charts'))

    if 'start_date_pge' in session:
        start_date_pge = try_parsing_date(session['start_date_pge'])
    else:
        start_date_pge = datetime.now() - timedelta(days=1)

    if 'end_date_pge' in session:
        end_date_pge = try_parsing_date(session['end_date_pge'])
    else:
        end_date_pge = datetime.now()

    if date_select_form.validate_on_submit():
        session['data_time_unit'] = date_select_form.data_time_unit.data
        session['start_date_pge'] = date_select_form.start_date.data
        session['end_date_pge'] = date_select_form.end_date.data
        start_date_pge = try_parsing_date(session['start_date_pge'])
        end_date_pge = try_parsing_date(session['end_date_pge'])
        return redirect(url_for('dashboard.charts'))

    if download_data_form.validate_on_submit():

        session['start_date_pge'] = download_data_form.start_date.data
        session['end_date_pge'] = download_data_form.end_date.data

        start_date_pge = try_parsing_date(session['start_date_pge'])
        end_date_pge = try_parsing_date(session['end_date_pge'])

        # process_xml.delay(
        #                     energy_account,
        #                     start_date_pge,
        #                     end_date_pge,
        #                     user_id=current_user.id
        #                 )

        pull_chunks(start_date_pge, end_date_pge, current_user)

        flash('Data processing', 'info')
        return redirect(url_for('dashboard.charts'))

    pge_inc_outg_grph = energy_account.serialize_charts('pge_incoming_outgoing_graph',
                                                                         start_date_pge, (end_date_pge + timedelta(days=1)))

    pge_inc_outg_grph_combnd = energy_account.serialize_charts('pge_incoming_outgoing_combined_graph',
                                                                                start_date_pge, (end_date_pge + timedelta(days=1)))

    date_select_form.start_date.data = start_date_pge.strftime('%m/%d/%Y')
    date_select_form.end_date.data = end_date_pge.strftime('%m/%d/%Y')

    users = User.query.all()
    users = [(user.id, user.full_name) for user in users]

    return render_template('users/dashboard/data_chart.html',
                           breadcrumbs=breadcrumbs,
                           heading=heading,
                           date_select_form=date_select_form,
                           download_data_form=download_data_form,
                           pge_inc_outg_grph=pge_inc_outg_grph,
                           pge_inc_outg_grph_combnd=pge_inc_outg_grph_combnd,
                           start_date=start_date_pge,
                           end_date=end_date_pge,
                           users=users)



@blueprint.route('/select_user/<int:user_id>', methods=['GET', 'POST'])
@blueprint.route('/select_user/modify/<modify>', methods=['GET', 'POST'])
@requires_roles('Admin')
@login_required
def select_user(user_id=None, modify=None):
    session['select_user'] = user_id

    if modify == 'clear':
        session.pop('select_user', None)

    return redirect(request.referrer)

@blueprint.route('/solaredge', methods=['GET', 'POST'])
@blueprint.route('/solaredge/<modify>', methods=['GET', 'POST'])
@requires_roles('Admin')
@login_required
def solar_edge(modify=None):
    """Solar Edge API"""
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('Solar Edge', 'bar-chart-o', url_for('dashboard.solar_edge'))]
    heading = 'Solar Electricity Production'
    users = User.query.all()
    users = [(user.id, user.full_name) for user in users]

    if session.get('select_user', None):
        current_user = User.query.filter_by(id=session['select_user']).first()
        energy_account = current_user.energy_accounts[0]
    else:
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
        energy_account.solar_first_date = None
        energy_account.solar_last_date = None
        session.pop('end_date_se', None)
        session.pop('data_time_unit_se', None)
        session.pop('se_energy_data', None)
        session.pop('se_energy_labels', None)
        SolarEdgeUsagePoint.query.filter_by(energy_account_id=energy_account.id).delete()
        db.session.commit()
        return redirect(url_for('dashboard.solar_edge'))

    """Set some default dates if nothing has been entered in the form."""
    if 'start_date_se' in session:
        start_date_se = try_parsing_date(session['start_date_se'])
    else:
        start_date_se = datetime.now() - timedelta(days=1)

    if 'end_date_se' in session:
        end_date_se = try_parsing_date(session['end_date_se'])
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
            start_date_se = try_parsing_date(session['start_date_se'])
            end_date_se = try_parsing_date(session['end_date_se'])
        except:
            flash('Date entered, not in correct format.', 'info')
            return redirect(url_for('dashboard.solar_edge'))

        return redirect(url_for('dashboard.solar_edge'))

    if download_data_form.validate_on_submit():
        session['start_date_se'] = download_data_form.start_date.data
        session['end_date_se'] = download_data_form.end_date.data

        try:
            start_date_se = try_parsing_date(session['start_date_se'])
            end_date_se = try_parsing_date(session['end_date_se'])
            if end_date_se > datetime.now():
                end_date_se = datetime.now()
        except:
            flash('Date entered, not in correct format.', 'info')
            return redirect(url_for('dashboard.solar_edge'))

        pull_solar_chunks(start_date_se, end_date_se, current_user)

        return redirect(url_for('dashboard.solar_edge'))

    date_select_form.start_date.data = start_date_se.strftime('%m/%d/%Y')
    date_select_form.end_date.data = end_date_se.strftime('%m/%d/%Y')

    return render_template('users/dashboard/solar_edge.html',
                           date_select_form=date_select_form,
                           download_data_form=download_data_form,
                           breadcrumbs=breadcrumbs,
                           heading=heading,
                           users=users)


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
            (CeleryTask.task_status == 0) &
            (CeleryTask.energy_account_id == current_user.energy_accounts[0].id)
            ).all()

        pending_tasks = []
        for task in unfinished_tasks:
            celery_task = process_xml.AsyncResult(task.task_id)
            print celery_task, str(celery_task.info), celery_task.state
            if (celery_task.state == 'FAILURE') or (celery_task.state == 'RETRY'):
                info = str(celery_task.info)
            else:
                info = celery_task.info
            task_dict = {
                'id': task.task_id,
                'info': info,
                'state': celery_task.state
            }
            pending_tasks.append(task_dict)
        print pending_tasks
        return jsonify(pending_tasks=pending_tasks)

    task = process_xml.AsyncResult(task_id)
    if task.state == 'PENDING':

        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
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

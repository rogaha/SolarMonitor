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
from solarmonitor.user.models import User, PGEUsagePoint, CeleryTask, SolarEdgeUsagePoint, EnergyAccount
from solarmonitor.public.forms import DateSelectForm, DownloadDataForm
from solarmonitor.extensions import db
import requests
import json

from jxmlease import parse

import datetime
from datetime import timedelta, date

config = Config()
cc = ClientCredentials(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)
api = Api(config.SSL_CERTS)
oauth = OAuth2(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)

blueprint = Blueprint('dashboard', __name__, url_prefix='/users/dashboard', static_folder='../static')

@blueprint.route('', methods=['GET', 'POST'])
@login_required
def home():
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home'))]
    heading = 'Dashboard'

    start_date = datetime.datetime.today().date() - timedelta(days=7)
    end_date = datetime.datetime.today().date()


    """The data for each chart needs to be calculated here, otherwise the calculations
    Are performed for each occurrence of a data set. This also makes the template
    Code Neater"""
    #TODO assumes for now that we want only the first energy account.
    prod_net_usg_pct = current_user.energy_accounts[0].serialize_charts('production_net_usage_percentage_graph', start_date, end_date)

    prod_net_usg = current_user.energy_accounts[0].serialize_charts('production_net_usage_graph', start_date, end_date)

    return render_template('users/dashboard/home.html',
        prod_net_usg_pct=prod_net_usg_pct,
        prod_net_usg=prod_net_usg,
        account_id=current_user.energy_accounts[0].id,
        breadcrumbs=breadcrumbs, heading=heading,
        )

@blueprint.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    breadcrumbs = [('Dashboard', 'dashboard', url_for('dashboard.home')), ('Account', 'user', url_for('dashboard.account'))]
    heading = 'Dashboard'
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
        return redirect("https://sharemydata.pge.com/myAuthorization/?clientId=50154&verified=true", code=302)

    refresh = oauth.get_refresh_token('https://api.pge.com/datacustodian/oauth/v2/token', current_user.energy_accounts[0].pge_refresh_token)

    print refresh

    current_user.energy_accounts[0].pge_refresh_token = refresh[u'refresh_token']
    current_user.energy_accounts[0].pge_access_token = refresh[u'access_token']
    db.session.commit()

    """
    batch_subscription = api.sync_request_simple(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Subscription/202674',
        current_user.energy_accounts[0].pge_access_token
    )

    all_usgpnts = api.sync_request_simple(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Subscription/202674/UsagePoint',
        current_user.energy_accounts[0].pge_access_token
    )

    usage_point_id = api.sync_request_simple(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Subscription/202674/UsagePoint/0053420795?published-min=2016-07-15T00:07:00Z&published-max=2016-07-17T00:07:00Z',
        current_user.energy_accounts[0].pge_access_token
    )
    """
    usage_point_summary = api.sync_request_simple(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Subscription/202674/UsagePoint/0053420795/UsageSummary?published-min=2016-07-15T00:07:00Z&published-max=2016-07-17T00:07:00Z',
        current_user.energy_accounts[0].pge_access_token
    )


    batch_usgpnt = api.sync_request_simple(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Subscription/202674/UsagePoint/0053420795?published-min=2016-06-01T00:07:00Z&published-max=2016-06-02T00:07:00Z',
        current_user.energy_accounts[0].pge_access_token
    )

    return render_template('users/dashboard/authorizations.html',
        energy_accounts=current_user.energy_accounts,
        breadcrumbs=breadcrumbs, heading=heading,
        #batch_subscription=batch_subscription,
        #all_usgpnts=all_usgpnts,
        #usage_point_id=usage_point_id,
        #usage_point_summary=usage_point_summary,
        batch_usgpnt=batch_usgpnt
        )


@blueprint.route('/graph/update/<int:account_id>/<start_date>/<end_date>', methods=['GET', 'POST'])
@login_required
def graph_update(account_id=None, start_date=None, end_date=None):
    energy_account = EnergyAccount.query.filter_by(id=account_id).first()

    s_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    e_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

    result = {
        'production_net_usage_percentage_graph': energy_account.serialize_charts('production_net_usage_percentage_graph', s_date, e_date),
        'production_net_usage_graph': energy_account.serialize_charts('production_net_usage_graph', s_date, e_date)
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
        PGEUsagePoint.query.filter_by(energy_account_id=energy_account.id).delete()
        db.session.commit()
        return redirect(url_for('dashboard.charts'))

    if 'start_date_pge' in session:
        start_date_pge = datetime.datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
    else:
        start_date_pge = datetime.datetime.now() - timedelta(days=1)

    if 'end_date_pge' in session:
        end_date_pge = datetime.datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)
    else:
        end_date_pge = datetime.datetime.now()

    if date_select_form.validate_on_submit():
        session['data_time_unit'] = date_select_form.data_time_unit.data
        session['start_date_pge'] = date_select_form.start_date.data
        session['end_date_pge'] = date_select_form.end_date.data
        start_date_pge = datetime.datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
        end_date_pge = datetime.datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)
        return redirect(url_for('dashboard.charts'))

    if download_data_form.validate_on_submit():
        session['client_credentials'] = cc.get_client_access_token('https://api.pge.com/datacustodian/oauth/v2/token')
        session['resource_authorization'] = api.simple_request(
            'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Authorization',
            session['client_credentials'][u'client_access_token']
            )

        session['start_date_pge'] = download_data_form.start_date.data
        session['end_date_pge'] = download_data_form.end_date.data

        start_date_pge = datetime.datetime.strptime(session['start_date_pge'], '%Y-%m-%d')
        end_date_pge = datetime.datetime.strptime(session['end_date_pge'], '%Y-%m-%d') + timedelta(days=1)

        xml_dict = parse(session['resource_authorization']['data'])
        bulk_url = xml_dict[u'ns1:feed'][u'ns1:entry'][1][u'ns1:content'][u'ns0:Authorization'][u'ns0:resourceURI']
        bulk_url += '?published-min={}&published-max={}' .format(start_date_pge.strftime('%Y-%m-%dT%H:%m:%SZ'), end_date_pge.strftime('%Y-%m-%dT%H:%m:%SZ'))


        print bulk_url
        print api.simple_request(bulk_url, session['client_credentials'][u'client_access_token'])

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
        start_date_se = datetime.datetime.strptime(session['start_date_se'], '%Y-%m-%d')
    else:
        start_date_se = datetime.datetime.now() - timedelta(days=1)

    if 'end_date_se' in session:
        end_date_se = datetime.datetime.strptime(session['end_date_se'], '%Y-%m-%d')
    else:
        end_date_se = datetime.datetime.now()

    solar_edge_production_graph = energy_account.serialize_charts('solar_edge_production_graph', start_date_se.date(), end_date_se.date())

    session['se_energy_data'] = solar_edge_production_graph['se_energy_data']
    session['se_energy_labels'] = solar_edge_production_graph['labels']

    """Load the form data into the session to save user selection"""
    if date_select_form.validate_on_submit():
        session['data_time_unit_se'] = date_select_form.data_time_unit.data
        session['start_date_se'] = date_select_form.start_date.data
        session['end_date_se'] = date_select_form.end_date.data

        try:
            start_date_se = datetime.datetime.strptime(session['start_date_se'], '%Y-%m-%d')
            end_date_se = datetime.datetime.strptime(session['end_date_se'], '%Y-%m-%d')
        except:
            flash('Date entered, not in correct format.')
            return redirect(url_for('dashboard.solar_edge'))

        return redirect(url_for('dashboard.solar_edge'))

    if download_data_form.validate_on_submit():
        session['start_date_se'] = download_data_form.start_date.data
        session['end_date_se'] = download_data_form.end_date.data

        try:
            start_date_se = datetime.datetime.strptime(session['start_date_se'], '%Y-%m-%d')
            end_date_se = datetime.datetime.strptime(session['end_date_se'], '%Y-%m-%d')
        except:
            flash('Date entered, not in correct format.')
            return redirect(url_for('dashboard.solar_edge'))

        se = SolarEdgeApi()

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
@blueprint.route('/status/<task_id>/<change_status>', methods=['GET', 'POST'])
def taskstatus(task_id=None, change_status=None):
    if change_status == "mark_complete":
        celery_task = CeleryTask.query.filter_by(task_id=task_id).first()
        celery_task.task_status = 1
        db.session.commit()
        response = {'response': 'task {} completed'.format(task_id)}
        return jsonify(response)

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

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

    start_date = datetime.date(2016, 6, 1)
    end_date = datetime.date(2016, 6, 16)

    energy_account = current_user.energy_accounts[0]

    pge_helper = PGEHelper(start_date, end_date, energy_account.id)
    incoming_data, incoming_labels, outgoing_data, outgoing_labels = pge_helper.get_daily_data_and_labels()

    daily_combined_electric_usage = [x - y for x, y in zip(incoming_data, outgoing_data)]

    solare_edge_data_pull = SolarEdgeUsagePoint.query.filter(
        (SolarEdgeUsagePoint.date>=start_date)&
        (SolarEdgeUsagePoint.energy_account_id==energy_account.id)&
        (SolarEdgeUsagePoint.date<=end_date)
        ).order_by(SolarEdgeUsagePoint.date.asc()).all()

    production = []
    for each in solare_edge_data_pull:
        production.append(float(each.value)/1000)

    net_usage = daily_combined_electric_usage

    production_percentage = [(x/(x + y)*100 )for x, y in zip(production, net_usage)]
    production_percentage = [x if x <=100 else 100 for x in production_percentage]

    net_usage_percentage = [100-x for x in production_percentage]

    net_input = [((x/(x + y)) - 1) for x, y in zip(production, net_usage)]
    net_input = [x * 100 if x > 0 else 0 for x in net_input]

    return render_template('users/dashboard/home.html',
        energy_accounts=current_user.energy_accounts,
        breadcrumbs=breadcrumbs, heading=heading,
        production_percentage=production_percentage,
        net_usage_percentage=net_usage_percentage,
        net_input=net_input,
        labels=incoming_labels,
        production=production,
        daily_combined_electric_usage=daily_combined_electric_usage
        )

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
    energy_account.solar_edge_api_key = request.form['solar_edge_api_key']
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

    energy_account = current_user.energy_accounts[0]

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

        print start_date_pge, end_date_pge

        xml_dict = parse(session['resource_authorization']['data'])
        bulk_url = xml_dict[u'ns1:feed'][u'ns1:entry'][1][u'ns1:content'][u'ns0:Authorization'][u'ns0:resourceURI']
        bulk_url += '?published-min={}&published-max={}' .format(start_date_pge.strftime('%Y-%m-%dT%H:%m:%SZ'), end_date_pge.strftime('%Y-%m-%dT%H:%m:%SZ'))

        print bulk_url

        print api.simple_request(bulk_url, session['client_credentials'][u'client_access_token'])

    """This next section will grab the data and organize it into usage by day."""
    incoming_electric_daily_data = []
    incoming_electric_daily_label = []
    outgoing_electric_daily_data = []
    outgoing_electric_daily_label = []
    if 'data_time_unit' in session:
        if session['data_time_unit'] == "Daily":
            pge_helper = PGEHelper(start_date_pge, end_date_pge, energy_account.id)

            incoming_electric_daily_data, incoming_electric_daily_label, outgoing_electric_daily_data, outgoing_electric_daily_label = pge_helper.get_daily_data_and_labels()


    """This next section will grab the data and organize it into usage by hour."""
    outgoing_electric_list = PGEUsagePoint.query.filter(
        (PGEUsagePoint.flow_direction==19)&
        (PGEUsagePoint.energy_account_id==energy_account.id)&
        (PGEUsagePoint.interval_start>=start_date_pge)&
        (PGEUsagePoint.interval_start<end_date_pge)
        ).order_by(PGEUsagePoint.interval_start.asc()).all()

    outgoing_electric = [x.interval_value * (10**(x.power_of_ten_multiplier -3)) for x in outgoing_electric_list]
    outgoing_labels = [x.interval_start.strftime('%m/%d %H:%S') for x in outgoing_electric_list]

    incoming_electric_list = PGEUsagePoint.query.filter(
        (PGEUsagePoint.flow_direction==1)&
        (PGEUsagePoint.energy_account_id==energy_account.id)&
        (PGEUsagePoint.interval_start>=start_date_pge)&
        (PGEUsagePoint.interval_start<end_date_pge)
        ).order_by(PGEUsagePoint.interval_start.asc()).all()

    incoming_electric = [x.interval_value * (10**(x.power_of_ten_multiplier -3)) for x in incoming_electric_list]
    incoming_labels = [x.interval_start.strftime('%m/%d %H:%S') for x in incoming_electric_list]

    #Add default data to the form, so you know what you picked last time
    date_select_form.start_date.data = start_date_pge.strftime('%Y-%m-%d')
    date_select_form.end_date.data = (end_date_pge - timedelta(days=1)).strftime('%Y-%m-%d')

    """This section merges both incoming and outgoing daily electric usage """
    daily_combined_electric_usage = [x - y for x, y in zip(incoming_electric_daily_data, outgoing_electric_daily_data)]

    hourly_combined_electric_usage = [x - y for x, y in zip(incoming_electric, outgoing_electric)]


    return render_template('users/dashboard/data_chart.html',
        breadcrumbs=breadcrumbs,
        heading=heading,
        date_select_form=date_select_form,
        download_data_form=download_data_form,
        incoming_electric=incoming_electric,
        outgoing_electric=outgoing_electric,
        incoming_labels=incoming_labels,
        outgoing_labels=outgoing_labels,
        incoming_electric_daily_data=incoming_electric_daily_data,
        incoming_electric_daily_label=incoming_electric_daily_label,
        outgoing_electric_daily_data=outgoing_electric_daily_data,
        outgoing_electric_daily_label=outgoing_electric_daily_label,
        daily_combined_electric_usage=daily_combined_electric_usage,
        hourly_combined_electric_usage=hourly_combined_electric_usage
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

        solare_edge_data_pull = SolarEdgeUsagePoint.query.filter(
            (SolarEdgeUsagePoint.date>=start_date_se)&
            (SolarEdgeUsagePoint.energy_account_id==energy_account.id)&
            (SolarEdgeUsagePoint.date<=end_date_se)
            ).order_by(SolarEdgeUsagePoint.date.asc()).all()

        if not solare_edge_data_pull:
            flash('No data for that date range available. Pull from Solar Edge.')

        session['se_energy_data'] = []
        session['se_energy_labels'] = []

        for each in solare_edge_data_pull:
            session['se_energy_data'].append(each.value)
            session['se_energy_labels'].append(each.date.strftime('%Y-%m-%d'))

        session['se_energy_data'] = [float(x)/1000 for x in session['se_energy_data']]

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
            se_energy = json.loads(se.site_energy_measurements(start_date_se.strftime('%Y-%m-%d'), end_date_se.strftime('%Y-%m-%d'), '237846', time_unit).text)
        else:
            se_energy = json.loads(se.site_energy_measurements(start_date_se.strftime('%Y-%m-%d'), end_date_se.strftime('%Y-%m-%d'), '237846').text)

        task = process_se_data.delay(se_energy, energy_account.id)

        session['se_energy_data'] = []
        session['se_energy_labels'] = []

        for each in se_energy['energy']['values']:
            if each['value'] == None:
                session['se_energy_data'].append(0)
            else:
                session['se_energy_data'].append(each['value']/1000)
            session['se_energy_labels'].append(str(each['date']))

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

# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, session, jsonify
from flask_login import login_required, login_user, logout_user, current_user

from solarmonitor.extensions import login_manager, db, login_user, logout_user
from solarmonitor.public.forms import LoginForm, DateSelectForm, DownloadDataForm
from solarmonitor.user.forms import RegistrationForm
from solarmonitor.user.models import User, UsagePoint, CeleryTask
from solarmonitor.utils import flash_errors
from solarmonitor.settings import Config
from solarmonitor.celerytasks.pgetasks import process_xml
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
import requests

from jxmlease import parse

import datetime
from datetime import timedelta
import pytz

local = pytz.timezone ('US/Eastern')

config = Config()
cc = ClientCredentials(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)
api = Api(config.SSL_CERTS)
oauth = OAuth2(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)

blueprint = Blueprint('public', __name__, static_folder='../static')

def send_email(sender, subject, to, text):
    return requests.post(
        "https://api.mailgun.net/v3/app618ef831f75f4a2eb15e3f08f18d09fe.mailgun.org/messages",
        auth=("api", "key-e3bfd2daee0cab79737c792954d54b12"),
        data={"from": sender,
              "to": to,
              "subject": subject,
              "text": text})


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@blueprint.route('/', methods=['GET', 'POST'])
def home():
    """Home page."""
    form = LoginForm(request.form)
    # Handle logging in
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(username=form.username.data).first()
            except:
                db.session.rollback()
                user = User.query.filter_by(username=form.username.data).first()
            if user is not None and user.verify_password(form.password.data):
                login_user(user, True)
                next = request.args.get('next')
                #if not next_is_valid('next'):
                #    return abort(400)

                return redirect(next or url_for('public.home'))
            flash('Invalid username or password')
        else:
            flash_errors(form)
    return render_template('public/home.html', form=form)


@blueprint.route('/logout')
@login_required
def logout():
    """Logout."""
    logout_user()
    flash('You are logged out.', 'info')
    return redirect(url_for('public.home'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    username=form.username.data,
                    password=form.password.data,
                    role_id=1,
                    address_one='',
                    address_two='',
                    city='',
                    state='',
                    zip_code=0,
                    pge_bulk_id=0,
                    cell_phone=0,)
        db.session.add(user)
        db.session.commit()
        flash('Thank you for registering. You can now log in.', 'success')
        return redirect(url_for('public.home'))
    else:
        flash_errors(form)
    return render_template('public/register.html', form=form)


@blueprint.route('/about')
def about():
    """About page."""
    return render_template('public/about.html')

@blueprint.route('/charts', methods=['GET', 'POST'])
@blueprint.route('/charts/session/<modify>', methods=['GET', 'POST'])
def charts(modify=None):
    """Electricity Usage Chart

    """

    date_select_form = DateSelectForm(prefix="date_select_form")
    download_data_form = DownloadDataForm(prefix="download_data_form")

    if modify == 'clear':
        session.clear()
        return redirect(url_for('public.charts'))

    if modify == 'delete-data':
        UsagePoint.query.delete()
        db.session.commit()
        return redirect(url_for('public.charts'))

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
            delta = end_date_pge - start_date_pge
            n = 0
            while n < delta.days:
                incoming_electric_daily = UsagePoint.query.filter(
                    (UsagePoint.flow_direction==1)&
                    (UsagePoint.interval_start>=(start_date_pge + timedelta(days=n)))&
                    (UsagePoint.interval_start<(start_date_pge + timedelta(days=n+1)))
                    ).order_by(UsagePoint.interval_start.asc()).all()

                outgoing_electric_daily = UsagePoint.query.filter(
                    (UsagePoint.flow_direction==19)&
                    (UsagePoint.interval_start>=(start_date_pge + timedelta(days=n)))&
                    (UsagePoint.interval_start<(start_date_pge + timedelta(days=n+1)))
                    ).order_by(UsagePoint.interval_start.asc()).all()

                incoming_interval_value = 0
                outgoing_interval_value = 0

                for datapoint in incoming_electric_daily:
                    incoming_interval_value += (datapoint.interval_value * (10**(datapoint.power_of_ten_multiplier -3)))

                for datapoint in outgoing_electric_daily:
                    outgoing_interval_value += (datapoint.interval_value * (10**(datapoint.power_of_ten_multiplier -3)))

                incoming_electric_daily_data.append(incoming_interval_value)
                incoming_electric_daily_label.append((start_date_pge + timedelta(days=n)).strftime('%m/%d'))

                outgoing_electric_daily_data.append(outgoing_interval_value)
                outgoing_electric_daily_label.append((start_date_pge + timedelta(days=n)).strftime('%m/%d'))
                n += 1

    """This next section will grab the data and organize it into usage by hour."""
    outgoing_electric_list = UsagePoint.query.filter(
        (UsagePoint.flow_direction==19)&
        (UsagePoint.interval_start>=start_date_pge)&
        (UsagePoint.interval_start<end_date_pge)
        ).order_by(UsagePoint.interval_start.asc()).all()

    outgoing_electric = [x.interval_value * (10**(x.power_of_ten_multiplier -3)) for x in outgoing_electric_list]
    outgoing_labels = [x.interval_start.strftime('%m/%d %H:%S') for x in outgoing_electric_list]

    incoming_electric_list = UsagePoint.query.filter(
        (UsagePoint.flow_direction==1)&
        (UsagePoint.interval_start>=start_date_pge)&
        (UsagePoint.interval_start<end_date_pge)
        ).order_by(UsagePoint.interval_start.asc()).all()

    incoming_electric = [x.interval_value * (10**(x.power_of_ten_multiplier -3)) for x in incoming_electric_list]
    incoming_labels = [x.interval_start.strftime('%m/%d %H:%S') for x in incoming_electric_list]

    #Add default data to the form, so you know what you picked last time
    date_select_form.start_date.data = start_date_pge.strftime('%Y-%m-%d')
    date_select_form.end_date.data = (end_date_pge - timedelta(days=1)).strftime('%Y-%m-%d')

    """This section merges both incoming and outgoing daily electric usage """
    daily_combined_electric_usage = [x - y for x, y in zip(incoming_electric_daily_data, outgoing_electric_daily_data)]

    hourly_combined_electric_usage = [x - y for x, y in zip(incoming_electric, outgoing_electric)]


    return render_template('public/data_chart.html', date_select_form=date_select_form, download_data_form=download_data_form, incoming_electric=incoming_electric, outgoing_electric=outgoing_electric, incoming_labels=incoming_labels, outgoing_labels=outgoing_labels, incoming_electric_daily_data=incoming_electric_daily_data, incoming_electric_daily_label=incoming_electric_daily_label, outgoing_electric_daily_data=outgoing_electric_daily_data, outgoing_electric_daily_label=outgoing_electric_daily_label, daily_combined_electric_usage=daily_combined_electric_usage, hourly_combined_electric_usage=hourly_combined_electric_usage)

@blueprint.route('/test')
def test():
    """Testing"""

    return render_template('public/test.html')

@blueprint.route('/oauth', methods=['GET', 'POST'])
def oauth():
    """	The OAuth URL you provide here will be used to direct customers to your customer login page to complete the authorization."""
    return render_template('public/oauth.html')

@blueprint.route('/oauth-redirect', methods=['GET', 'POST'])
def oauth_redirect():
    """	The redirect URI you provide here is where PG&E will send the Authorization Code once customer authorization is completed and you make a request for the authorization code.
    """

    return render_template('public/oauth.html', page_title='Redirect')

@blueprint.route('/notifications', methods=['GET', 'POST'])
def notifications():
    """	The URI you provide here is where PG&E will send notifications that customer-authorized data is available  """

    if request.method == 'POST':
        xml_dict = parse(request.data) #Create dictionary from XML using jxmlease library

        xml_dict.prettyprint()

        client_credentials = cc.get_client_access_token('https://api.pge.com/datacustodian/oauth/v2/token')

        bulk_data = []
        for resource in xml_dict[u'ns0:BatchList'][u'ns0:resources']:
            """When a get request is made to the bulk data url, PGE will respond by posting XML data to this view function. The xml data will have one or more url's
            that can be used to access the bulk data. The urls look identical the bulk data url, but there is an extra paramater at the end.
            ex. https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Bulk/50098?correlationID=f5ee53cf-247b-4a2f-abdc-7f650fecb1b5

            This for-loop will grab all of these url's and make a get request to each one. PGE will then respond to the GET request by returning the bulk data
            XML immediately, which is then added to the bulk_data list for processing.
            """
            bulk_data.append(api.simple_request(resource, client_credentials[u'client_access_token']))


        """This for-loop will work through the bulk_data list containing one or more XML trees. It will parse the tree, and insert the useful parts into the
        database. Before calling db.session.commit(), we also check to see if the data is already in the system, and ignores the data if true.
        """

        task = process_xml.delay((bulk_data[0]['data']))


        celery_task = CeleryTask(task_id=task.id, task_status=0, user_id=1)
        db.session.add(celery_task)
        db.session.commit()

        print "task id:", task.id

    return render_template('public/oauth.html', page_title='Notification Bucket')

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
        unfinished_tasks = CeleryTask.query.filter_by(task_status=0).all()

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

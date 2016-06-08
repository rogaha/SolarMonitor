# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, session
from flask_login import login_required, login_user, logout_user, current_user

from solarmonitor.extensions import login_manager, db, login_user, logout_user
from solarmonitor.public.forms import LoginForm
from solarmonitor.user.forms import RegistrationForm
from solarmonitor.user.models import User, UsagePoint
from solarmonitor.utils import flash_errors
from solarmonitor.settings import Config
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
import requests

from jxmlease import parse
import xml.etree.cElementTree as ET

import datetime




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

@blueprint.route('/charts')
def charts():
    """Electricity Usage Chart
    #####################
    Batch Subscription (Standard and EEF 3rd parties)
    You can also request usage and billing information via the batch bulk asynchronous API for all of your customer authorizations for usage/billing data (i.e. Subscriptions).
    Example Batch Bulk Request URL
    https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Bulk/{BulkID}?published-min={startDate}&publishedmax={endDate}
    """

    return render_template('public/data_chart.html')

@blueprint.route('/test')
def test():
    """Testing"""

    session['client_credentials'] = cc.get_client_access_token('https://api.pge.com/datacustodian/oauth/v2/token')
    session['resource_authorization'] = api.simple_request(
        'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Authorization',
        session['client_credentials'][u'client_access_token']
        )

    xml_dict = parse(session['resource_authorization']['data'])
    bulk_url = xml_dict[u'ns1:feed'][u'ns1:entry'][1][u'ns1:content'][u'ns0:Authorization'][u'ns0:resourceURI']

    api.simple_request(bulk_url, session['client_credentials'][u'client_access_token'])

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

        for resource in bulk_data:
            """This for-loop will work through the bulk_data list containing one or more XML trees. It will parse the tree, and insert the useful parts into the
            database. Before calling db.session.commit(), we also check to see if the data is already in the system, and ignores the data if true.
            """
            data = parse(resource['data'])

            data.prettyprint()

            reading_type = {}

            for resource in data[u'ns1:feed'][u'ns1:entry']:

                if u'ns0:ReadingType' in resource[u'ns1:content']:
                    reading_type['commodity_type'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:commodity']
                    reading_type['flow_direction'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:flowDirection']
                    reading_type['unit_of_measure'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:uom']
                    reading_type['measuring_period'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:measuringPeriod']
                    reading_type['power_of_ten_multiplier'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:powerOfTenMultiplier']
                    reading_type['accumulation_behavior'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:accumulationBehaviour']

                if u'ns0:IntervalBlock' in resource[u'ns1:content']:

                    for reading in resource[u'ns1:content'][u'ns0:IntervalBlock'][u'ns0:IntervalReading']:
                        reading_type['interval_start'] = reading[u'ns0:timePeriod'][u'ns0:start']
                        reading_type['interval_duration'] = reading[u'ns0:timePeriod'][u'ns0:duration']
                        reading_type['interval_value'] = reading[u'ns0:value']

                        usage_point = UsagePoint(
                            user_id=50098,
                            commodity_type=reading_type['commodity_type'],
                            measuring_period=reading_type['measuring_period'],
                            interval_value=reading_type['interval_value'],
                            interval_start=datetime.datetime.fromtimestamp(int(reading_type['interval_start'])),
                            interval_duration=reading_type['interval_duration'],
                            flow_direction=reading_type['flow_direction'],
                            unit_of_measure=reading_type['unit_of_measure'],
                            power_of_ten_multiplier=reading_type['power_of_ten_multiplier'],
                            accumulation_behavior=reading_type['accumulation_behavior']
                            )

                        duplicate_check = UsagePoint.query.filter_by(
                            user_id=50098,
                            interval_value=usage_point.interval_value,
                            flow_direction=usage_point.flow_direction,
                            interval_start=usage_point.interval_start
                            ).first()

                        if duplicate_check == None:
                            db.session.add(usage_point)
                            db.session.commit()
                        else:
                            print 'usage_point already in database'

    return render_template('public/oauth.html', page_title='Notification Bucket')

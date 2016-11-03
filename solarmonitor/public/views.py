# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, session, jsonify, send_file, make_response
from flask_login import login_required, login_user, logout_user, current_user

from solarmonitor.celerytasks.pgetasks import process_xml
from solarmonitor.extensions import login_manager, db, login_user, logout_user
from solarmonitor.public.forms import LoginForm
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.user.models import User, EnergyAccount, AppEvent
from solarmonitor.utils import flash_errors
from solarmonitor.settings import Config
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
from solarmonitor.enphase.enphase_api import EnphaseApi
from io import BytesIO
import io
import datetime
from datetime import timedelta

from jxmlease import parse
import json

config = Config()

blueprint = Blueprint('public', __name__, static_folder='../static')

cc = ClientCredentials(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)
api = Api(config.SSL_CERTS)
oauth2 = OAuth2(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)


@blueprint.route('/get_graph/<int:energy_account_id>_<start_date>_<end_date>_charts.png', methods=['GET', 'POST'])
def selenium_img_generator(energy_account_id=None, start_date=None, end_date=None):
    energy_account = EnergyAccount.query.filter_by(id=energy_account_id).first()

    if energy_account == None:
        return redirect(url_for('public.home'))

    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.datetime.today().date()

    if start_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=14)

    prod_net_usg = energy_account.serialize_charts('production_net_usage_graph', start_date, end_date)

    prod_comb = energy_account.serialize_charts('pge_incoming_outgoing_combined_graph', start_date, end_date, separate=True)

    html = render_template('email/img_generator.html',
        prod_net_usg=prod_net_usg,
        start_date=start_date,
        prod_comb=prod_comb,
        end_date=end_date)

    selenium_html_string = """{}""".format(html)

    from selenium import webdriver

    driver = webdriver.PhantomJS()
    driver.set_window_size(560, 300)
    driver.get(selenium_html_string)
    img = driver.get_screenshot_as_png()

    return send_file(io.BytesIO(img))

@blueprint.route('/', methods=['GET', 'POST'])
def home():
    """Home page."""
    form = LoginForm(request.form)
    register_form = RegistrationForm()
    next = request.args.get('next')
    # Handle logging in
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(email=form.email.data).first()
            except:
                db.session.rollback()
                user = User.query.filter_by(email=form.email.data).first()
            if user is not None and user.verify_password(form.password.data):
                login_user(user, True)
                #if not next_is_valid('next'):
                #    return abort(400)
                current_user.log_event(info='{} just logged in.'.format(current_user.full_name))
                return redirect(next or url_for('dashboard.home'))
            flash('Invalid email address or password', 'info')
        else:
            flash_errors(form)
            return redirect(url_for('public.home', next=next))
    return render_template('public/home.html', form=form, register_form=register_form)

@blueprint.route('/about')
def about():
    """About page."""
    return render_template('public/about.html')

@blueprint.route('/enphase-authorization')
@login_required
def enphase_authorization():
    """Enphase Authorization landing page."""
    user_id = request.args.get('user_id', None)
    if not user_id:
        flash('Unable to connect Enphase account', 'info')
        return redirect(url_for('dashboard.account'))

    enphase = EnphaseApi(current_user.energy_accounts[0]) #assumes only one energy account for each user
    system_info = enphase.systems().text
    system_info = json.loads(system_info)
    print system_info
    system_id = system_info['systems'][0]['system_id'] #assumes only one solar power system for each user

    current_user.enphase_system_id = system_id
    current_user.enphase_user_id = user_id
    db.session.commit()

    flash('Enphase account successfully connected', 'info')
    return render_template('public/about.html')


#TODO Need to move this route to the auth module. Need to clear with PGE first.
@blueprint.route('/pge-oauth-scope', methods=['GET', 'POST'])
@login_required
def oauth():
    """	The OAuth URL you provide here will be used to direct customers to your customer login page to complete the authorization."""
    scope = request.args.get('scope')
    return redirect("https://api.pge.com/datacustodian/oauth/v2/authorize?client_id={}&redirect_uri={}&scope={}&response_type=code".format(
        config.PGE_CLIENT_CREDENTIALS['client_key'],
        config.PGE_3rd_PARTY_REDIRECT_URI,
        scope
    ), code=302)

#TODO Need to move this route to the auth module. Need to clear with PGE first.
@blueprint.route('/pge-oauth-redirect', methods=['GET', 'POST'])
def oauth_redirect():
    """	The redirect URI you provide here is where PG&E will send the Authorization Code once customer authorization is completed and you make a request for the authorization code.
    """
    code = request.args.get('code')

    """the `get_access_token` method will retrieve and save the access_token,
    refresh_token, electric usage_point, and subscription_id
    """
    oauth2.get_access_token(
        'https://api.pge.com/datacustodian/oauth/v2/token',
        code,
        'https://notrueup.solardatapros.com/pge-oauth-redirect',
        current_user.energy_accounts[0]
    )

    flash('PGE Connectivity Completed Successfully', 'info')
    current_user.log_event(info="PGE Account Successfully connected via oauth.")

    return redirect(url_for('dashboard.home'))

#TODO Need to move this route to the user.dashboard module. Need to clear with PGE first.
@blueprint.route('/pge-notifications', methods=['GET', 'POST'])
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

        task = process_xml.delay(bulk_data[0]['data'])

    return render_template('public/oauth.html', page_title='Notification Bucket')

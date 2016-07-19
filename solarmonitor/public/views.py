# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, session, jsonify, send_file, make_response
from flask_login import login_required, login_user, logout_user, current_user

from solarmonitor.celerytasks.pgetasks import process_xml
from solarmonitor.extensions import login_manager, db, login_user, logout_user
from solarmonitor.public.forms import LoginForm
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.user.models import User, EnergyAccount
from solarmonitor.utils import flash_errors
from solarmonitor.settings import Config
from solarmonitor.pge.pge import Api, ClientCredentials
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

@blueprint.route('/get_graph/<int:energy_account_id>_charts.png', methods=['GET', 'POST'])
def selenium_img_generator(energy_account_id=None):
    energy_account = EnergyAccount.query.filter_by(id=energy_account_id).first()

    if energy_account == None:
        return redirect(url_for('public.home'))

    end_date = datetime.datetime.today().date()
    start_date = end_date - timedelta(days=14)
    energy_account = EnergyAccount.query.filter_by(id=energy_account.id).first()
    html = render_template('email/img_generator.html',
        energy_account=energy_account,
        start_date=start_date,
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
                next = request.args.get('next')
                #if not next_is_valid('next'):
                #    return abort(400)

                return redirect(next or url_for('dashboard.home'))
            flash('Invalid email address or password')
        else:
            flash_errors(form)
    return render_template('public/home.html', form=form, register_form=register_form)

@blueprint.route('/about')
def about():
    """About page."""
    return render_template('public/about.html')


#TODO Need to move this route to the auth module. Need to clear with PGE first.
@blueprint.route('/pge-oauth-scope', methods=['GET', 'POST'])
def oauth():
    """	The OAuth URL you provide here will be used to direct customers to your customer login page to complete the authorization."""
    return render_template('public/oauth.html')

#TODO Need to move this route to the auth module. Need to clear with PGE first.
@blueprint.route('/pge-oauth-redirect', methods=['GET', 'POST'])
def oauth_redirect():
    """	The redirect URI you provide here is where PG&E will send the Authorization Code once customer authorization is completed and you make a request for the authorization code.
    """
    return render_template('public/oauth.html', page_title='Redirect')

#TODO Need to move this route to the user.dashboard module. Need to clear with PGE first.
@blueprint.route('/pge-notification', methods=['GET', 'POST'])
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

# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from solarmonitor.extensions import login_manager, db, login_user, logout_user
from solarmonitor.public.forms import LoginForm
from solarmonitor.user.forms import RegistrationForm
from solarmonitor.user.models import User
from solarmonitor.utils import flash_errors

blueprint = Blueprint('public', __name__, static_folder='../static')

def send_email(sender, subject, to, text):
    import requests
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
    form = LoginForm(request.form)
    return render_template('public/about.html', form=form)

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
    """	The URI you provide here is where PG&E will send notifications that customer-authorized data is available """
    if request.method == 'POST':
        print request.values
        send_email('Dan <admin@solarmonitor>', 'dan@danwins.com', 'Incoming POST data', request.values )
    return render_template('public/oauth.html', page_title='Notification Bucket')

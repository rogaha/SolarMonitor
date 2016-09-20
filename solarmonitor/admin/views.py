from flask import Blueprint, render_template, flash, redirect, url_for, session
from flask_login import login_required, login_user, logout_user, current_user
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.utils import flash_errors, requires_roles, try_parsing_date, flash_errors
from solarmonitor.user.models import User, EnergyAccount, AppEvent
from solarmonitor.extensions import db
from solarmonitor.public.forms import DownloadDataForm
from solarmonitor.auth.forms import RegistrationForm

from datetime import timedelta, datetime


blueprint = Blueprint('admin', __name__, url_prefix='/admin', static_folder='../static')

@blueprint.route('/test/<modify>/<int:user_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def test_user_account(page=1, modify=None, user_id=None):
    if modify == 'login_as':
        test_user = User.query.filter_by(id=user_id).first()
        current_user.log_event(info='{} logged in as {}'.format(current_user.full_name, test_user.full_name))
        logout_user()
        login_user(test_user, True)
        return redirect(url_for('dashboard.home'))

@blueprint.route('/users', methods=['GET', 'POST'])
@blueprint.route('/users/page/<int:page>', methods=['GET', 'POST'])
@blueprint.route('/<modify>/<int:user_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def users(page=1, modify=None, user_id=None):
    """Admin Home Page."""
    breadcrumbs = [('Admin Dashboard', 'dashboard', url_for('admin.users'))]
    heading = 'Admin Dashboard'

    users = User.query

    add_user_form = RegistrationForm(prefix="add")
    edit_user_form = RegistrationForm(prefix="edit")

    if modify == 'edit':
        user = User.query.filter_by(id=user_id).first()
        user.first_name = edit_user_form.first_name.data
        user.last_name = edit_user_form.last_name.data
        if edit_user_form.email.data != user.email:
            user_check = User.query.filter_by(email=edit_user_form.email.data).first()
            if user_check:
                flash('Email already in use.')
                return redirect(url_for('admin.users'))
            else:
                user.email = edit_user_form.email.data

        if edit_user_form.password.data:
            user.password=edit_user_form.password.data

        db.session.commit()
        flash('User modified.')
        current_user.log_event(info='user account: {} modified'.format(user.full_name))
        return redirect(url_for('admin.users'))

    if modify == 'del':
        user = User.query.filter_by(id=user_id).first()
        name = user.full_name
        if current_user == user:
            flash('You can\'t delete yourself!')
            return redirect(url_for('admin.users'))
        db.session.delete(user)
        db.session.commit()
        flash('User deleted')
        current_user.log_event(info='user account: {} deleted'.format(name))
        return redirect(url_for('admin.users'))

    if add_user_form.validate_on_submit():
        user = User(
            email=add_user_form.email.data,
            first_name=add_user_form.first_name.data,
            last_name=add_user_form.last_name.data,
            password=add_user_form.password.data,
        )
        energy_account = EnergyAccount(nick_name='Default Account')
        user.energy_accounts.append(energy_account)
        current_user.log_event(info="Default energy account created for \'{}\' by admin.".format(user.full_name))
        current_user.log_event(info="New user account created for \'{}\' by admin.".format(user.full_name))
        db.session.add(user)
        db.session.commit()
        flash('User created.', 'success')

        return redirect(url_for('admin.users'))


    return render_template('admin/users.html',
        page=page,
        breadcrumbs=breadcrumbs,
        heading=heading,
        users=users.paginate(page, 10, False),
        add_user_form=add_user_form,
        edit_user_form=edit_user_form
    )

@blueprint.route('/events', methods=['GET', 'POST'])
@blueprint.route('/events/page/<int:page>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def events(page=1):
    """Admin Home Page."""
    breadcrumbs = [('Admin Dashboard', 'dashboard', url_for('admin.events'))]
    heading = 'Admin Dashboard'

    app_events = AppEvent.query.order_by(AppEvent.date_time.desc())

    form = DownloadDataForm()

    if form.validate_on_submit():
        if form.start_date.data:
            session['event_start_date'] = form.start_date.data
        if form.end_date.data:
            session['event_end_date'] = form.end_date.data
        return redirect(url_for('admin.events'))

    app_events = AppEvent.query.filter(
        (AppEvent.date_time <= try_parsing_date(session.get('event_end_date', (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d'))))&
        (AppEvent.date_time >= try_parsing_date(session.get('event_start_date', (datetime.utcnow() - timedelta(days=365)).strftime('%Y-%m-%d'))))
    ).order_by(AppEvent.date_time.desc())

    form.start_date.data = session.get('event_start_date', None)
    form.end_date.data = session.get('event_end_date', None)

    return render_template('admin/events.html',
        page=page,
        breadcrumbs=breadcrumbs,
        heading=heading,
        app_events=app_events.paginate(page, 10, False),
        form=form
    )

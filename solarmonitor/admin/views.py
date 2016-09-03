from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, login_user, logout_user
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.utils import flash_errors, requires_roles
from solarmonitor.user.models import User, EnergyAccount, AppEvent
from solarmonitor.extensions import db


blueprint = Blueprint('admin', __name__, url_prefix='/admin', static_folder='../static')


@blueprint.route('/users', methods=['GET', 'POST'])
@blueprint.route('/users/page/<int:page>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def users(page=1):
    """Admin Home Page."""
    breadcrumbs = [('Admin Dashboard', 'dashboard', url_for('admin.users'))]
    heading = 'Admin Dashboard'

    users = User.query

    return render_template('admin/users.html',
        page=page,
        breadcrumbs=breadcrumbs,
        heading=heading,
        users=users.paginate(page, 10, False),
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

    return render_template('admin/events.html',
        page=page,
        breadcrumbs=breadcrumbs,
        heading=heading,
        app_events=app_events.paginate(page, 10, False)
    )

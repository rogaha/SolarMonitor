from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, login_user, logout_user
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.utils import flash_errors, requires_roles
from solarmonitor.user.models import User, EnergyAccount
from solarmonitor.extensions import db


blueprint = Blueprint('admin', __name__, url_prefix='/admin', static_folder='../static')


@blueprint.route('/', methods=['GET', 'POST'])
@blueprint.route('/page/<int:page>', methods=['GET', 'POST'])
@login_required
@requires_roles('Admin')
def home(page=1):
    """Admin Home Page."""
    breadcrumbs = [('Admin Dashboard', 'dashboard', url_for('admin.home'))]
    heading = 'Admin Dashboard'

    users = User.query

    return render_template('admin/home.html',
        page=page,
        breadcrumbs=breadcrumbs,
        heading=heading,
        users=users.paginate(page, 1, False)
    )

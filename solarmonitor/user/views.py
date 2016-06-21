# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template
from flask_login import login_required
from solarmonitor.extensions import login_manager
from solarmonitor.user.models import User

blueprint = Blueprint('user', __name__, url_prefix='/users', static_folder='../static')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@blueprint.route('/')
@login_required
def members():
    """List members."""
    return render_template('users/members.html')

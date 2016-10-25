from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from solarmonitor.extensions import login_manager
from solarmonitor.auth.forms import RegistrationForm
from solarmonitor.utils import flash_errors
from solarmonitor.user.models import User, EnergyAccount
from solarmonitor.extensions import db



blueprint = Blueprint('auth', __name__, url_prefix='/auth', static_folder='../static')


@blueprint.route('/logout')
@login_required
def logout():
    """Logout."""
    current_user.log_event(info='{} just logged out.'.format(current_user.full_name))
    logout_user()
    flash('You are logged out.', 'info')
    return redirect(url_for('public.home'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user."""
    form = RegistrationForm()
    next = request.args.get('next')
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=form.password.data,
        )
        energy_account = EnergyAccount(nick_name='Default Account')
        user.energy_accounts.append(energy_account)

        db.session.add(user)
        db.session.commit()
        user.log_event(info="Default energy account created for new user \'{}\'.".format(user.full_name))
        user.log_event(info="New user account created for \'{}\'.".format(user.full_name))
        login_user(user, True)

        #if not next_is_valid('next'):
        #    return abort(400)
        current_user.log_event(info='{} just logged in.'.format(current_user.full_name))
        flash('Thank you for registering.', 'success')
        return redirect(next or url_for('dashboard.home'))
    else:
        flash_errors(form)
        return redirect(url_for('dashboard.home', next=next))
    return render_template('public/register.html', form=form)

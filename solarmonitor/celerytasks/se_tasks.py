from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import SolarEdgeUsagePoint, EnergyAccount
import datetime
from datetime import timedelta, date

from solarmonitor.utils import celery


@celery.task(bind=True)
def process_se_data(self, json_data, energy_account_id):
    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():

        for each in json_data['energy']['values']:

            usage_point = SolarEdgeUsagePoint()
            usage_point.energy_account_id = energy_account_id
            usage_point.time_unit = json_data['energy']['timeUnit']
            usage_point.unit_of_measure = json_data['energy']['unit']
            usage_point.date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')
            usage_point.value = 0 if each['value'] == None else each['value']

            duplicate_check = SolarEdgeUsagePoint.query.filter(
                (SolarEdgeUsagePoint.date==usage_point.date)&
                (SolarEdgeUsagePoint.energy_account_id==energy_account_id)
                ).first()

            if duplicate_check:
                duplicate_check.value = usage_point.value
                db.session.commit()
            else:
                db.session.add(usage_point)
                db.session.commit()
        energy_account = EnergyAccount.query.filter_by(id=energy_account_id).first()
        for user in energy_account.users:
            user.log_event(info="Incoming Solar Edge Data finished processing. Energy Acount: {}".format(energy_account.id))

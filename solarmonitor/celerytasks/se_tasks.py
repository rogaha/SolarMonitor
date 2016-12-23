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
        """Debug printing statements so we can see what data is returned"""
        print 'SOLAR EDGE DATA:'
        print json_data

        for index, each in enumerate(json_data['energy']['values']):
            if index == 0:
                start_date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')

            end_date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')

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
        if energy_account.solar_last_date:
            if energy_account.solar_last_date < end_date:
                energy_account.solar_last_date = end_date
        else:
            energy_account.solar_last_date = end_date

        if energy_account.solar_first_date:
            if energy_account.solar_first_date > start_date:
                energy_account.solar_first_date = start_date
        else:
            energy_account.solar_first_date = start_date

        db.session.commit()

        for user in energy_account.users:
            user.log_event(info="Incoming Solar Edge Data finished processing. Energy Acount: {}".format(energy_account.id))

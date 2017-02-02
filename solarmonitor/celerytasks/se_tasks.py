from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import SolarEdgeUsagePoint, EnergyAccount
import datetime
from datetime import timedelta, date

from solarmonitor.utils import celery


@celery.task(bind=True)
def process_se_data(self, json_data, energy_account_id):
    """{"energy":{"timeUnit":"DAY","unit":"Wh","values":[{"date":"2013-06-01 00:00:00","value":null},{"date":"2013-
    06-02 00:00:00","value":null},{"date":"2013-06-03 00:00:00","value":null},{"date":"2013-06-04
    00:00:00","value":67313.24}]}}
    """
    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():
        """Debug printing statements so we can see what data is returned"""
        print 'SOLAR EDGE DATA:'
        print json_data

        data_received = {
            'start_date': '',
            'end_date': '',
            'data': []
        }

        for index, each in enumerate(json_data['energy']['values']):
            if index == 0:
                start_date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')
                data_received['start_date'] = start_date

            if each['value']:
                end_date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')
                data_received['end_date'] = end_date

            usage_point = SolarEdgeUsagePoint()
            usage_point.energy_account_id = energy_account_id
            usage_point.time_unit = json_data['energy']['timeUnit']
            usage_point.unit_of_measure = json_data['energy']['unit']
            usage_point.date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')
            usage_point.value = 0 if each['value'] == None else each['value']

            data_received['data'].append(usage_point)

        SolarEdgeUsagePoint.query.filter(
            (SolarEdgeUsagePoint.interval_start >= start_date) &
            (SolarEdgeUsagePoint.interval_start <= end_date) &
            (SolarEdgeUsagePoint.energy_account_id == energy_account_id)
        ).delete()
        db.session.commit()

        for usage in data_received['data']:
            db.session.add(usage)

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

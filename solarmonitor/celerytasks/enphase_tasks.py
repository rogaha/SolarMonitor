from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import SolarEdgeUsagePoint, EnergyAccount
from solarmonitor.enphase.enphase_api import EnphaseApi
import datetime
from datetime import timedelta, date
import time

from solarmonitor.utils import celery


@celery.task(bind=True)
def process_enphase_data(self, energy_account_id, start_date, end_date):
    energy_account = EnergyAccount.query.filter_by(id=energy_account_id).first()
    enphase = EnphaseApi(account)
    json_data = json.loads(enphase.energy_lifetime(start_date, end_date).text)
    print json_data
    """
    {
      "system_id": 66,
      "start_date": "2013-01-01",
      "meter_start_date": "2013-02-15",
      "production": [15422,15421,17118,18505,18511,18487,...],
      "meta": {"status": "normal", "last_report_at": 1445619615, "last_energy_at": 1445619033, "operational_at": 1357023600}
    }
    """
    print json_data
    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():
        if 'reason' in json_data:
            if json_data['reason'] == "409":
                print 'Enphase Throttling!'
                timeout_start = json_data['period_start']
                timeout_end = json_data['period_end']
                time_to_wait = timeout_end - timeout_start
                self.retry(countdown=time_to_wait)
            elif json_data['reason'] == 'Requested date is in the future':
                return

        start_date = datetime.datetime.strptime(json_data['start_date'], ('%Y-%m-%d'))

        for index, each in enumerate(json_data['production']):

            usage_point = SolarEdgeUsagePoint()
            usage_point.energy_account_id = energy_account_id
            usage_point.time_unit = 'DAY'
            usage_point.unit_of_measure = 'Wh'
            usage_point.date = start_date + timedelta(days=index)
            usage_point.value = each

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

        for user in energy_account.users:
            user.log_event(info="Incoming Enphase Data finished processing. Energy Acount: {}".format(energy_account.id))

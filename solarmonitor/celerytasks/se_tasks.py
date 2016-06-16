from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import SolarEdgeUsagePoint
import datetime
from datetime import timedelta

from solarmonitor.utils import celery


@celery.task(bind=True)
def process_se_data(self, json_data):
    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():

        for each in json_data['energy']['values']:

            usage_point = SolarEdgeUsagePoint()
            usage_point.user_id = 1
            usage_point.time_unit = json_data['energy']['timeUnit']
            usage_point.unit_of_measure = json_data['energy']['unit']
            usage_point.date = datetime.datetime.strptime(str(each['date']), '%Y-%m-%d %H:%M:%S')

            if usage_point.date.date() == datetime.today().date():
                duplicate_check = SolarEdgeUsagePoint.query.filter_by(date=usage_point.date).first()
                if duplicate_check:
                    if each['value'] == None:
                        duplicate_check.value = 0
                        db.session.commit()
                    else:
                        duplicate_check.value = each['value']
                        db.session.commit()

            else:
                if each['value'] == None:
                    usage_point.value = 0
                else:
                    usage_point.value = each['value']

                    duplicate_check = SolarEdgeUsagePoint.query.filter_by(date=usage_point.date, value=usage_point.value).first()

                    if duplicate_check:
                        print 'duplicate usage point'
                    else:
                        db.session.add(usage_point)
                        db.session.commit()

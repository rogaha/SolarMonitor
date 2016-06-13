from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import UsagePoint, CeleryTask
import datetime
from datetime import timedelta

from solarmonitor.utils import celery
from jxmlease import parse

@celery.task
def add(x, y):
    print x
    print y
    return x + y


@celery.task(bind=True)
def process_xml(self, xml):

    reading_type = {}
    data = parse(xml)

    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():

        for index, resource in enumerate(data[u'ns1:feed'][u'ns1:entry']):

            if u'ns0:ReadingType' in resource[u'ns1:content']:
                reading_type['commodity_type'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:commodity']
                reading_type['flow_direction'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:flowDirection']
                reading_type['unit_of_measure'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:uom']
                reading_type['measuring_period'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:measuringPeriod']
                reading_type['power_of_ten_multiplier'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:powerOfTenMultiplier']
                reading_type['accumulation_behavior'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:accumulationBehaviour']

            if u'ns0:IntervalBlock' in resource[u'ns1:content']:
                for reading in resource[u'ns1:content'][u'ns0:IntervalBlock'][u'ns0:IntervalReading']:
                    reading_type['interval_start'] = reading[u'ns0:timePeriod'][u'ns0:start']
                    reading_type['interval_duration'] = reading[u'ns0:timePeriod'][u'ns0:duration']
                    reading_type['interval_value'] = reading[u'ns0:value']

                    usage_point = UsagePoint(
                        user_id=50098,
                        commodity_type=reading_type['commodity_type'],
                        measuring_period=reading_type['measuring_period'],
                        interval_value=reading_type['interval_value'],
                        interval_start=datetime.datetime.fromtimestamp(int(reading_type['interval_start'])) - timedelta(hours=7),
                        interval_duration=reading_type['interval_duration'],
                        flow_direction=reading_type['flow_direction'],
                        unit_of_measure=reading_type['unit_of_measure'],
                        power_of_ten_multiplier=reading_type['power_of_ten_multiplier'],
                        accumulation_behavior=reading_type['accumulation_behavior']
                        )

                    duplicate_check = UsagePoint.query.filter_by(
                        user_id=50098,
                        interval_value=usage_point.interval_value,
                        flow_direction=usage_point.flow_direction,
                        interval_start=usage_point.interval_start
                        ).first()

                    if duplicate_check == None:
                        db.session.add(usage_point)
                        db.session.commit()
                    else:
                        print 'usage_point already in database'

                    self.update_state(state='PROGRESS',  meta={'current': index, 'total': len(data[u'ns1:feed'][u'ns1:entry'])})


        celery_task = CeleryTask.query.filter_by(task_id=self.request.id).first()
        celery_task.task_status = 1
        db.session.commit()
    return {'status': 'Task completed!'}

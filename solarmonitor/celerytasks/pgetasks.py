from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import PGEUsagePoint, CeleryTask, EnergyAccount
import datetime
from datetime import timedelta

from solarmonitor.utils import celery
from jxmlease import parse

@celery.task(bind=True)
def process_xml(self, xml):

    print xml

    reading_type = {}
    data = parse(xml)

    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():

        """In this first section, we try to find the identifier. This is something that will link
        the XML to a user's energy_account in the database.
        """

        """Get the identifier from the href attribute of the of the link element. This looks like
        https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Batch/Subscription/202674/UsagePoint/0053420795
        and the value at the end is the identifier. When we were using bulk uploads, this was the
        bulk_id of the user, however now that we are on synchronous data it is the usage point."""

        identifier = data[u'ns1:feed'][u'ns1:link'].get_xml_attr("href").rsplit('/', 1)[-1]

        #Logging purposes
        print identifier

        #Try to get an energy account using the identifier as a bulk_id
        energy_account = EnergyAccount.query.filter_by(pge_bulk_id=identifier).first()

        #If no energy account can be found, then try again but use identifier as a UsagePointID
        if not energy_account:
            energy_account = EnergyAccount.query.filter_by(pge_usage_point=identifier).first()

        #Create a new celery task in the database
        celery_task = CeleryTask(task_id=self.request.id, task_status=0, energy_account_id=energy_account.id)
        db.session.add(celery_task)
        db.session.commit()


        for index, resource in enumerate(data[u'ns1:feed'][u'ns1:entry']):
            """Here we loop through all the entry blocks in the XML, not all of these blocks
            are useful to us, so we check the block on each loop to see if it has the data we need.
            This code assumes that the <entry> blocks will always be in the same order, which although not documented
            by PGE has proven true. The enumerate method allows us to know which loop number we
            are on compared to the total number of loops. We use this data to know how far along we are in processing
            the request. This produces the percent complete bar on the website."""

            if u'ns0:ReadingType' in resource[u'ns1:content']:
                """If a block contains a ReadingType value in its content block, then we know that the next
                <entry> block will have the interval readings. Before we move on though, we'll need to
                save some information from this block so we can record it alongside each interval reading.
                We get the 5 values shown below and save them into the reading_type dictionary"""

                reading_type['commodity_type'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:commodity']
                reading_type['flow_direction'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:flowDirection']
                reading_type['unit_of_measure'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:uom']
                try:
                    reading_type['measuring_period'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:measuringPeriod']
                except:
                    print 'No measuring Period'
                    reading_type['measuring_period'] = 99

                reading_type['power_of_ten_multiplier'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:powerOfTenMultiplier']
                reading_type['accumulation_behavior'] = resource[u'ns1:content'][u'ns0:ReadingType'][u'ns0:accumulationBehaviour']

            if u'ns0:IntervalBlock' in resource[u'ns1:content']:
                """This is the <entry> block that immediately follows the <entry> block that contained the ReadingType
                information. This block has all the interval readings and we save them to the database along with
                some other data that we got in the previous <entry> block and then saved in the reading_type dict."""

                for reading in resource[u'ns1:content'][u'ns0:IntervalBlock'][u'ns0:IntervalReading']:
                    reading_type['interval_start'] = reading[u'ns0:timePeriod'][u'ns0:start']
                    reading_type['interval_duration'] = reading[u'ns0:timePeriod'][u'ns0:duration']
                    reading_type['interval_value'] = reading[u'ns0:value']

                    #Create an object to store in the database
                    usage_point = PGEUsagePoint(
                        energy_account_id=energy_account.id,
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

                    #Before executing the SQL, check to see if the data is already there
                    #Data is considered a dupe if it's the same energy account, interval value, flow direction, and start time
                    duplicate_check = PGEUsagePoint.query.filter_by(
                        energy_account_id=energy_account.id,
                        interval_value=usage_point.interval_value,
                        flow_direction=usage_point.flow_direction,
                        interval_start=usage_point.interval_start
                        ).first()

                    #Add to database
                    if duplicate_check == None:
                        db.session.add(usage_point)
                        db.session.commit()

                    #Update the celery task for polling purposes
                    self.update_state(state='PROGRESS',  meta={'current': index, 'total': len(data[u'ns1:feed'][u'ns1:entry'])})

        #Mark the task as complete. Previously this was only done on the front-end but created
        #rogue uncompleted tasks if someone navigated away from the dashboard before a task ended.
        import time
        time.sleep(5)
        celery_task.task_status = 1
        db.session.commit()

        for user in energy_account.users:
            user.log_event(info="Incoming PGE Data finished processing. Energy Acount: {}".format(energy_account.id))
    return {'status': 'Task completed!'}

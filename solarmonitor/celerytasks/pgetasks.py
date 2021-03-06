from solarmonitor.extensions import db
from solarmonitor.settings import Config, ProdConfig
from solarmonitor.user.models import PGEUsagePoint, CeleryTask, EnergyAccount, AppEvent
from solarmonitor.pge.pge import Api, ClientCredentials, OAuth2
import datetime
from datetime import timedelta

from solarmonitor.utils import celery
from jxmlease import parse

config = ProdConfig()
cc = ClientCredentials(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)
api = Api(config.SSL_CERTS)
oauth = OAuth2(config.PGE_CLIENT_CREDENTIALS, config.SSL_CERTS)


def backoff(attempts):
    """Return a backoff delay, in seconds, given a number of attempts.

    The delay increases very rapidly with the number of attemps:
    1, 2, 4, 8, 16, 32, ...

    """
    return 2 ** attempts


@celery.task(bind=True, max_retries=3, soft_time_limit=6000)
def process_xml(self, energy_account, start_date, end_date, user_id=1):
    self.update_state(state='STARTING',  meta={'current': 0, 'total': 100})
    from solarmonitor.app import create_app
    app = create_app(ProdConfig)
    with app.app_context():

        try:
            event = AppEvent(
                user_id=user_id,
                date_time=datetime.datetime.utcnow(),
                event_type=None,
                level=1,
                info='PGE Data pull started. Date range: {} to {} | celery_task_id:{}'.format(
                                start_date.strftime('%m/%d/%Y'),
                                end_date.strftime('%m/%d/%Y'),
                                self.request.id)
            )
            db.session.add(event)
            db.session.commit()

            energy_account = EnergyAccount.query.filter_by(id=energy_account.id).first()

            # Create a new celery task in the database
            celery_task = CeleryTask.query.filter_by(task_id=self.request.id).first()
            if celery_task is None:
                celery_task = CeleryTask(task_id=self.request.id, task_status=0, energy_account_id=energy_account.id)
            db.session.add(celery_task)
            db.session.commit()

            if energy_account.pge_refresh_token_expiration:
                """If there is an expiration date in the system check if it's expired.
                if it is get a new one and save the new expiration date in the system."""
                if energy_account.pge_refresh_token_expiration < datetime.datetime.now():
                    # Refresh the OAuth token. This token is good for 1 hour.
                    refresh_info = oauth.get_refresh_token(energy_account)
                    print refresh_info
                    energy_account.pge_refresh_token = refresh_info.get(u'refresh_token',
                                                                        energy_account.pge_refresh_token)
                    energy_account.pge_access_token = refresh_info.get(u'access_token', energy_account.pge_access_token)
                    energy_account.pge_refresh_token_expiration = (datetime.datetime.now() + timedelta(hours=1))
                    db.session.commit()
            else:
                """If the expiration date is null, set it to now so we get a new one next time."""
                energy_account.pge_refresh_token_expiration = datetime.datetime.now()
                db.session.commit()
            print 'sending request to PGE'
            # pge_data is an XML document
            pge_data = api.sync_request(
                energy_account,
                start_date,
                end_date,
            )

            # This will add the XML to the heroku logs.
            print pge_data

            if 'error' in pge_data:
                raise ValueError('PGE Api call resulted in the following error- {}'.format(pge_data['error']))

            reading_type = {}
            data = parse(pge_data)

            data_received = {
                'start_date': '',
                'end_date': '',
                'data': []
            }

            for index, resource in enumerate(data[u'ns1:feed'][u'ns1:entry']):
                """Here we loop through all the entry blocks in the XML, not all of these blocks
                are useful to us, so we check the block on each loop to see if it has the data we need.
                This code assumes that the <entry> blocks will always be in the same order, which although not
                documented by PGE has proven true. The enumerate method allows us to know which loop number we
                are on compared to the total number of loops. We use this data to know how far along we are in
                processing the request. This produces the percent complete bar on the website."""

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
                    some other data that we got in the previous <entry> block and then saved in the reading_type dict.
                    """

                    for reading in resource[u'ns1:content'][u'ns0:IntervalBlock'][u'ns0:IntervalReading']:
                        reading_type['interval_start'] = reading[u'ns0:timePeriod'][u'ns0:start']
                        reading_type['interval_duration'] = reading[u'ns0:timePeriod'][u'ns0:duration']
                        reading_type['interval_value'] = reading[u'ns0:value']

                        # Create an object to store in the database
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

                        """This function begins with a start_date and and end_date that is provided by the user
                        (or system). However the start and end values for `pge_first_date` and `pge_last_date`
                        should not be set by user input. Instead we will check for what data actually comes back and
                        set the first and last dates according to that data. On the first loop, we will set the first_date equal
                        to the first date that comes in from PGE every subsequent loop will increment the end_date which
                        will get updated and saved to the DB during the cleanup phase of this task."""
                        if index == 0:
                            start_date = usage_point.interval_start
                            data_received['start_date'] = usage_point.interval_start
                            print start_date

                        end_date = usage_point.interval_start
                        data_received['end_date'] = usage_point.interval_start

                        data_received['data'].append(usage_point)

                        # Before executing the SQL, check to see if the data is already there
                        # Data is considered a dupe if it's the same energy account, interval value, flow direction, and start time
                        # duplicate_check = PGEUsagePoint.query.filter_by(
                        #     energy_account_id=energy_account.id,
                        #     interval_value=usage_point.interval_value,
                        #     flow_direction=usage_point.flow_direction,
                        #     interval_start=usage_point.interval_start
                        #     ).first()

                        # Add to database
                        # if duplicate_check is None:
                        #     db.session.add(usage_point)

                        # Update the celery task for polling purposes
                        self.update_state(state='PROGRESS',  meta={'current': index, 'total': len(data[u'ns1:feed'][u'ns1:entry'])})

            PGEUsagePoint.query.filter(
                (PGEUsagePoint.interval_start >= start_date) &
                (PGEUsagePoint.interval_start <= end_date) &
                (PGEUsagePoint.energy_account_id == energy_account.id)
            ).delete()
            db.session.commit()

            for usage in data_received['data']:
                db.session.add(usage)

            db.session.commit()
            # Mark the task as complete. Previously this was only done on the front-end but created
            # rogue uncompleted tasks if someone navigated away from the dashboard before a task ended.
            if energy_account.pge_last_date:
                if energy_account.pge_last_date < end_date:
                    energy_account.pge_last_date = end_date
            else:
                energy_account.pge_last_date = end_date

            if energy_account.pge_first_date:
                if energy_account.pge_first_date > start_date:
                    energy_account.pge_first_date = start_date
            else:
                energy_account.pge_first_date = start_date

            celery_task.task_status = 1
            event = AppEvent(
                user_id=user_id,
                date_time=datetime.datetime.utcnow(),
                event_type=None,
                level=1,
                info='SUCCESS - PGE Data pull. data: {} | celery_task_id:{}'.format(pge_data[:65], self.request.id)
            )
            db.session.add(event)
            db.session.commit()
        except Exception as exc:
            print exc
            db.session.rollback()
            event = AppEvent(
                user_id=user_id,
                date_time=datetime.datetime.utcnow(),
                event_type=None,
                level=1,
                info='RETRY - PGE Data pull. Error- {} | celery_task_id:{} retrying in {} seconds'.format(
                    exc,
                    self.request.id,
                    backoff(self.request.retries)
                )
            )
            db.session.add(event)

            if self.request.retries == 3:
                celery_task.task_status = 2

            db.session.commit()
            self.retry(countdown=backoff(self.request.retries), exc=exc)

    return {'status': 'Task completed!'}

from solarmonitor.user.models import PGEUsagePoint
from solarmonitor.extensions import db
import datetime
from datetime import timedelta, date
from jxmlease import parse


def get_usage_point_from_xml(xml):
    data = parse(xml, xml_attribs=True)
    try:
        """If a user only has one type of energy usage, we can query the kind directly.
        If they have both gas and electric, this will fail with a key error,
        and in the except block, we'll loop through the entry feeds looking for
        the Electricity UsagePoint which is ns0:kind == 0"""
        if data[u'ns1:feed'][u'ns1:entry'][u'ns1:content'][u'ns0:UsagePoint'][u'ns0:ServiceCategory'][u'ns0:kind'] == u'0':
            for link in data[u'ns1:feed'][u'ns1:entry'][u'ns1:link']:
                if link.get_xml_attr("rel") == u'self':
                    return link.get_xml_attr("href").rsplit('/', 1)[-1]
    except:
        for resource in data[u'ns1:feed'][u'ns1:entry']:
            if resource[u'ns1:content'][u'ns0:UsagePoint'][u'ns0:ServiceCategory'][u'ns0:kind'] == u'0':
                for link in resource[u'ns1:link']:
                    if link.get_xml_attr("rel") == u'self':
                        return link.get_xml_attr("href").rsplit('/', 1)[-1]


def generate_random_pge_data(
        number_of_data_rows=10,
        account_id=1,
        numbers_of_days_ago=4):
    import random
    from datetime import datetime, timedelta
    flow_direction = [19, 1]
    energy_value = [0, 500, 7900, 543700, 1034600,
                    1444300, 1404700, 1297200, 850204, 839500, 374400, 116900]
    start_date = datetime.today() - timedelta(days=numbers_of_days_ago)
    n = 0
    while n < number_of_data_rows:
        pge_usage_point = PGEUsagePoint(
            energy_account_id=account_id,
            commodity_type=1,
            measuring_period=3,
            interval_start=start_date + timedelta(hours=n),
            interval_duration=1,
            interval_value=random.choice(energy_value),
            flow_direction=random.choice(flow_direction),
            unit_of_measure=5,
            power_of_ten_multiplier=-3,
            accumulation_behavior=4
            )
        db.session.add(pge_usage_point)
        db.session.commit()
        n += 1


class PGEHelper:

    def __init__(self, start_date, end_date, energy_account_id):
        self.start_date = start_date
        self.end_date = end_date
        self.energy_account_id = energy_account_id

    def get_daily_data_and_labels(self):
        """This next section will grab the data and organize it
        into usage by day."""
        incoming_electric_daily_data = []
        incoming_electric_daily_label = []
        outgoing_electric_daily_data = []
        outgoing_electric_daily_label = []

        delta = self.end_date - self.start_date
        n = 0
        while n < delta.days:
            incoming_electric_daily = PGEUsagePoint.query.filter(
                (PGEUsagePoint.flow_direction == 1) &
                (PGEUsagePoint.energy_account_id == self.energy_account_id) &
                (PGEUsagePoint.interval_start >= (self.start_date + timedelta(days=n))) &
                (PGEUsagePoint.interval_start < (self.start_date + timedelta(days=n+1)))
                ).order_by(PGEUsagePoint.interval_start.asc()).all()

            outgoing_electric_daily = PGEUsagePoint.query.filter(
                (PGEUsagePoint.flow_direction == 19) &
                (PGEUsagePoint.energy_account_id == self.energy_account_id) &
                (PGEUsagePoint.interval_start >= (self.start_date + timedelta(days=n))) &
                (PGEUsagePoint.interval_start < (self.start_date + timedelta(days=n+1)))
                ).order_by(PGEUsagePoint.interval_start.asc()).all()

            incoming_interval_value = 0
            outgoing_interval_value = 0

            for datapoint in incoming_electric_daily:
                incoming_interval_value += datapoint.interval_value

            for datapoint in outgoing_electric_daily:
                outgoing_interval_value += datapoint.interval_value

            incoming_electric_daily_data.append(incoming_interval_value)
            incoming_electric_daily_label.append((self.start_date + timedelta(days=n)))

            outgoing_electric_daily_data.append(outgoing_interval_value)
            outgoing_electric_daily_label.append((self.start_date + timedelta(days=n)))
            n += 1

        return incoming_electric_daily_data, incoming_electric_daily_label, \
            outgoing_electric_daily_data, outgoing_electric_daily_label

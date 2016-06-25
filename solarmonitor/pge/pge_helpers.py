from solarmonitor.user.models import PGEUsagePoint
from solarmonitor.extensions import db
import datetime
from datetime import timedelta, date

class PGEHelper:

    def __init__(self, start_date, end_date, energy_account_id):
        self.start_date = start_date
        self.end_date = end_date
        self.energy_account_id = energy_account_id

    def get_daily_data_and_labels(self):
        """This next section will grab the data and organize it into usage by day."""
        incoming_electric_daily_data = []
        incoming_electric_daily_label = []
        outgoing_electric_daily_data = []
        outgoing_electric_daily_label = []


        delta = self.end_date - self.start_date
        n = 0
        while n < delta.days:
            incoming_electric_daily = PGEUsagePoint.query.filter(
                (PGEUsagePoint.flow_direction==1)&
                (PGEUsagePoint.energy_account_id==self.energy_account_id)&
                (PGEUsagePoint.interval_start>=(self.start_date + timedelta(days=n)))&
                (PGEUsagePoint.interval_start<(self.start_date + timedelta(days=n+1)))
                ).order_by(PGEUsagePoint.interval_start.asc()).all()

            outgoing_electric_daily = PGEUsagePoint.query.filter(
                (PGEUsagePoint.flow_direction==19)&
                (PGEUsagePoint.energy_account_id==self.energy_account_id)&
                (PGEUsagePoint.interval_start>=(self.start_date + timedelta(days=n)))&
                (PGEUsagePoint.interval_start<(self.start_date + timedelta(days=n+1)))
                ).order_by(PGEUsagePoint.interval_start.asc()).all()

            incoming_interval_value = 0
            outgoing_interval_value = 0

            for datapoint in incoming_electric_daily:
                incoming_interval_value += (datapoint.interval_value * (10**(datapoint.power_of_ten_multiplier -3)))

            for datapoint in outgoing_electric_daily:
                outgoing_interval_value += (datapoint.interval_value * (10**(datapoint.power_of_ten_multiplier -3)))

            incoming_electric_daily_data.append(incoming_interval_value)
            incoming_electric_daily_label.append((self.start_date + timedelta(days=n)).strftime('%m/%d'))

            outgoing_electric_daily_data.append(outgoing_interval_value)
            outgoing_electric_daily_label.append((self.start_date + timedelta(days=n)).strftime('%m/%d'))
            n += 1

        return  incoming_electric_daily_data, incoming_electric_daily_label, outgoing_electric_daily_data, outgoing_electric_daily_label

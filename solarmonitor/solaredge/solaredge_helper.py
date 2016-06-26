from solarmonitor.user.models import User, SolarEdgeUsagePoint
from solarmonitor.extensions import db
import datetime
from datetime import timedelta, date



def generate_random_solar_edge_data(number_of_data_rows=10, account_id=1, numbers_of_days_ago=4):
    import random
    from datetime import datetime, timedelta
    energy_value = [0, 39000, 53000, 42000, 41000, 37000, 54000, 47000, 49000, 51000, 55000, 28000]
    start_date = datetime.today() - timedelta(days=numbers_of_days_ago)
    n = 0
    while n < number_of_data_rows:
        se_usage_point = SolarEdgeUsagePoint(
            energy_account_id=account_id,
            time_unit='Wh',
            unit_of_measure='DAY',
            date=start_date + timedelta(days=n),
            value=random.choice(energy_value)
            )
        db.session.add(se_usage_point)
        db.session.commit()
        n += 1

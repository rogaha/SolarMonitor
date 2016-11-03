# -*- coding: utf-8 -*-
import requests
from solarmonitor.settings import Config

class EnphaseApi:
    """Throttling rules:
     If a request is rejected because one of these limits has been exceeded,
     the response includes information about why the request was rejected:
     < Status: 409
     < { "reason": "409", "message": ["Usage limit exceeded for plan Watt"],
       "period": "minute", "period_start": 1401742440, "period_end": 1401742500, "limit": 10}

       “period” tells you how long to wait.
    Additional rules:
    The API accepts a number of parameters. Parameter order does not matter in any request.
    Unrecognized parameters are ignored. Clients of the API are expected to do the same:
    Be order-agnostic, and ignore unknown response values.

    API returns JSON only

    Dates and Times in Requests and Responses:
    Endpoints that receive dates expect the format YYYY-mm-dd. All dates are in the timezone of the requested system.
    """
    def __init__(self, energy_account):
        self.api_key = Config.ENPHASE_API_KEY
        self.user_id = energy_account.enphase_user_id
        self.system_id = energy_account.enphase_system_id
        self.app_id = Config.ENPHASE_APP_ID
        self.base_url = 'https://api.enphaseenergy.com/api/v2'

    def __repr__(self):
        return '<EnphaseApi>'

    def systems(self):
        """Returns a list of systems for which the user can make API requests.
        Sample response:
        {
          "systems": [
            {
              "system_id": 67,
              "system_name": "Eich Residence",
              "system_public_name": "Eich Residence",
              "status": "normal",
              "timezone": "America/Los_Angeles",
              "country": "US",
              "state": "CA",
              "city": "Sebastopol",
              "postal_code": "95472",
              "connection_type": "ethernet",
              "meta": {"status": "normal", "last_report_at": 1445619615, "last_energy_at": 1445619033, "operational_at": 1357023600}
            }
          ]
        """
        return requests.get(
            "{}/systems".format(self.base_url),
            params={
                'key': self.api_key,
                'user_id': self.user_id,
                'limit': 1
            }
        )

    def energy_lifetime(self, start_date=None, end_date=None):
        """Returns a time series of energy produced on the system over its lifetime. All measurements are in Watt hours

        The time series includes one entry for each day from the start_date to the end_date.
        There are no gaps in the time series. If the response includes trailing zeroes, such as [909, 4970, 0, 0, 0],
        then no energy has been reported for the last days in the series.

        start_date
        The date on which to start the time series. Defaults to the system’s operational date.

        end_date
        The last date to include in the time series. Defaults to yesterday or the last day the system reported, whichever is earlier.

        dates passed to this function must be python datetime objects.

        Sample response:
        {
          "system_id": 66,
          "start_date": "2013-01-01",
          "meter_start_date": "2013-02-15",
          "production": [15422,15421,17118,18505,18511,18487,...],
          "meta": {"status": "normal", "last_report_at": 1445619615, "last_energy_at": 1445619033, "operational_at": 1357023600}
        }
        """
        parameters = {
            'key': self.api_key,
            'user_id': self.user_id,
        }
        if start_date:
            parameters['start_date'] = start_date.strftime('%Y-%m-%d')

        if end_date:
            parameters['end_date'] = end_date.strftime('%Y-%m-%d')

        return requests.get(
            "{}/systems/{}/energy_lifetime".format(self.base_url, self.system_id),
            params=parameters
        )

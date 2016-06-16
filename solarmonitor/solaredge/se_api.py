import requests
from solarmonitor.settings import Config

config = Config()

"""
When using special characters or spaces in URL, they must be url encoded.
The monitoring server data can be in different languages therefore data is retrieved using UTF-8.
Date and time formats in all APIs are:
Date and time: YYYY-MM-DD hh:mm:ss
Date only: YYYY-MM-DD
Dates are always in the time zone of the site.
All physical measures are in the metric units system.
Temperature values are always in Celsius degrees.
"""

class SolarEdgeApi:

    def __init__(self):
        self.api_key = config.SOLAREDGE_API_KEY
        self.base_url = 'https://monitoringapi.solaredge.com'

    def __repr__(self):
        return '<SolarEdgeApi>'

    def site_list(self, size=100, start_index=0, sort_order='ASC'):
        """Sample Output: {"sites":{"count":1,"site":[{"id":237846,"name":"Pirtle, Brad","accountId":49260,"status":"Active","peakPower":9.62,"lastUpdateTime":"2016-06-15","installationDate":"2016-03-25","notes":"","type":"Optimizers & Inverters","location":{"country":"United States","state":"California","city":"Walnut Creek","address":"Venado Camino 2616","address2":"","zip":"94598","timeZone":"America/Los_Angeles","countryCode":"US","stateCode":"CA"},"primaryModule":{"manufacturerName":"Canadian Solar","modelName":"CS6P-260P","maximumPower":260.0},"uris":{"DATA_PERIOD":"/site/237846/dataPeriod","OVERVIEW":"/site/237846/overview","DETAILS":"/site/237846/details"},"publicSettings":{"isPublic":false}}]}}
        """
        return requests.get(
            "{}/sites/list".format(self.base_url),
            params={
            'api_key': self.api_key,
            'size': size,
            'start_index': start_index,
            'sort_order': sort_order
            }
        )

    def accounts_list(self, size=100, start_index=0, sort_order='ASC'):
        """Description: Return the account and list of sub-accounts related to the given token. This API accepts parameters for convenient search, sorting and pagination.
        """
        return requests.get(
            "{}/accounts/list".format(self.base_url),
            params={
            'api_key': self.api_key,
            'size': size,
            'start_index': start_index,
            'sort_order': sort_order
            }
        )

    def site_details(self, site_id):
        """Sample Output: {"details":{"id":0,"name":"site name","accountId":0,"status":"Active","peakPower":9.8,"currency":"EUR","installationDate":"2012-08-16 00:00:00","notes":"my notes","type":"Optimizers & Inverters","location":{"country":"my country","state":"my state","city":"my city","address":"my address","address2":"","zip":"0000", "timeZone":"GMT"},"alertQuantity":0,"alertSeverity":"NONE","uris":{"IMAGE_URI":"site image uri"},"publicSettings":{"name":null,"isPublic":false}}}
        """
        return requests.get(
            "{}/site/{}/details".format(self.base_url, site_id),
            params={
            'api_key': self.api_key
            }
        )

    def site_sensors_list(self, site_id):
        """Returns a list of all the sensors in the site, and the device to which they are connected.
        """
        return requests.get(
            "{}/equipment/{}/sensors".format(self.base_url, site_id),
            params={
            'api_key': self.api_key
            }
        )

    def site_sensors_data(self, site_id, start_date, end_date):
        """Returns the data of all the sensors in the site, by the gateway they are connected to.
        """
        return requests.get(
            "{}/site/{}/sensors".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startDate': start_date,
            'endDate': end_date,
            }
        )

    def site_data_start_end_dates(self, *site_ids):
        """Description: Returns the energy production start and end dates for the site_id in question.

        Sample output: {"dataPeriod":{"startDate":"2013-05-05 12:00:00","endDate":"2013-05-28 23:59:59"}}
        """
        return requests.get(
            "{}/site/{}/dataPeriod".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key
            }
        )

    def site_energy_measurements(self, start_date, end_date, site_id, time_unit='DAY'):
        """Description: Return the site energy measurements. This API is limited to one year when using timeUnit=DAY (i.e., daily resolution) and to one month when using timeUnit=QUARTER_OF_AN_HOUR or timeUnit=HOUR.

        Sample output: {"energy":{"timeUnit":"DAY","unit":"Wh","values":[{"date":"2013-06-01 00:00:00","value":null},{"date":"2013-06-02 00:00:00","value":null},{"date":"2013-06-03 00:00:00","value":null},{"date":"2013-06-04 00:00:00","value":67313.24}]}}
        """
        return requests.get(
            "{}/site/{}/energy".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startDate': start_date,
            'endDate': end_date,
            'timeUnit': time_unit
            }
        )

    def site_energy_measurements_detailed(self, start_time, end_time, site_id, time_unit='DAY', meters='PRODUCTION,CONSUMPTION'):
        """Description: Return the site energy measurements. This API is limited to one year when using timeUnit=DAY (i.e., daily resolution) and to one month when using timeUnit=QUARTER_OF_AN_HOUR or timeUnit=HOUR.

        Sample output: {"energy":{"timeUnit":"DAY","unit":"Wh","values":[{"date":"2013-06-01 00:00:00","value":null},{"date":"2013-06-02 00:00:00","value":null},{"date":"2013-06-03 00:00:00","value":null},{"date":"2013-06-04 00:00:00","value":67313.24}]}}
        """
        return requests.get(
            "{}/site/{}/energyDetails".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startTime': start_time,
            'endTime': end_time,
            'timeUnit': time_unit,
            'meters': meters
            }
        )

    def site_total_energy(self, start_date, end_date, site_id):
        """Description: Description: Return the site total energy produced for a given period.

        Sample output: {"timeFrameEnergy":{"energy":761985.8,"unit":"Wh"}}
        """
        return requests.get(
            "{}/site/{}/timeFrameEnergy".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startDate': start_date,
            'endDate': end_date,
            }
        )

    def site_power_measurements(self, start_time, end_time, site_id):
        """Description: Return the site power measurements in 15 minutes resolution. This API is limited to one-month period.
        startTime=2013-05-5%2011:00:00
        endTime=2013-05-05%2013:00:00
        Sample output: {"timeFrameEnergy":{"energy":761985.8,"unit":"Wh"}}
        """
        return requests.get(
            "{}/site/{}/power".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startTime': start_time,
            'endTime': end_time,
            }
        )

    def site_power_details(self, start_time, end_time, site_id, meters='PRODUCTION,CONSUMPTION'):
        """Detailed site power measurements from meters such as consumption, export (feed-in), import (purchase), etc.
        Note: Calculated meter readings (also referred to as "virtual meters"), such as self-consumption, are calculated using the data measured by the meter and the inverters.
        """
        return requests.get(
            "{}/site/{}/powerDetails".format(self.base_url, site_id),
            params={
            'api_key': self.api_key,
            'startTime': start_time,
            'endTime': end_time,
            'meters': meters
            }
        )

    def site_overview(self, *site_ids):
        """Description: Display the site overview data.

        Sample output: {"overview":{"lastUpdateTime":"2013-10-01 02:37:47","lifeTimeData":{"energy":761985.75,"revenue":946.13104},"lastYearData":{"energy":761985.8,"revenue":0.0},"lastMonthData":{"energy":492736.7,"revenue":0.0},"lastDayData":{"energy":0.0,"revenue":0.0},"currentPower":{"power":0.0}}}
        """
        return requests.get(
            "{}/site/{}/overview".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key,
            }
        )

    def site_power_flow(self, *site_ids):
        """Description: Retrieves the current power flow between all elements of the site including PV array, storage (battery), loads (consumption) and grid.
        """
        return requests.get(
            "{}/site/{}/currentPowerFlow".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key,
            }
        )

    def site_storage_information(self, start_time, end_time, *site_ids):
        """Description: Get detailed storage information from batteries: the state of energy, power and lifetime energy.
        Note: Applicable to systems with batteries.
        """
        return requests.get(
            "{}/site/{}/storageData".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key,
            'startTime': start_time,
            'endTime': end_time,
            }
        )

    def site_image(self, name, max_width, max_height, img_hash, *site_ids):
        """Description: Get detailed storage information from batteries: the state of energy, power and lifetime energy.
        Note: Applicable to systems with batteries.

        """
        return requests.get(
            "{}/site/{}/siteImage/{}".format(self.base_url, ",".join(site_ids), name),
            params={
            'api_key': self.api_key,
            'maxWidth': max_width,
            'maxHeight': max_height,
            'hash': img_hash
            }
        )

    def site_components_list(self, *site_ids):
        """Description: Return a list of inverters/SMIs in the specific site.

        Sample Output: {"list":[{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00 "},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-65"}]}
        """
        return requests.get(
            "{}/equipment/{}/list".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key
            }
        )

    def site_equipment_inventory(self, *site_ids):
        """Description: Return the inventory of SolarEdge equipment in the site, including: inverters/SMIs, batteries, meters, gateways and sensors.

        Sample Output: {"list":[{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00 "},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-65"}]}
        """
        return requests.get(
            "{}/site/{}/Inventory".format(self.base_url, ",".join(site_ids)),
            params={
            'api_key': self.api_key
            }
        )

    def site_inverter_data(self, serial_number, start_time, end_time, *site_ids):
        """Description: Return specific inverter data for a given timeframe.

        Sample Output: {"list":[{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00 "},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-00"},{"name":"Inverter 1","manufacturer":"SolarEdge","model":"SE16K","serialNumber":"12345678-65"}]}
        """
        return requests.get(
            "{}/equipment/{}/{}/data".format(self.base_url, ",".join(site_ids), serial_number),
            params={
            'api_key': self.api_key,
            'startTime': start_time,
            'endTime': end_time,
            }
        )

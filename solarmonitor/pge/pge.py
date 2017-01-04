import requests
import json
from base64 import b64encode
from solarmonitor.extensions import db
from solarmonitor.pge.pge_helpers import get_usage_point_from_xml
from flask_login import current_user


class Api:
    """
    This API for the  synchronous and Asynchronous XML data to get from the PG&E.
    This is used by PG&E thrid parties.
    :Author: Bharati V
    """
    def __init__(self, cert_params_hash):
        self.cert = (cert_params_hash["crt"], cert_params_hash["key"])

    # API sync request using Oauth2 access token
    def simple_request(self, url, access_token):
        header_params = {'Authorization': 'Bearer ' + access_token}
        request = requests.get(url, data={},  headers=header_params, cert=self.cert)
        if str(request.status_code) == "200":
            response = {"status": request.status_code, "data": request.text}
            return response
        response = {"status": request.status_code, "error": request.text}
        return response

    # API sync request using Oauth2 access token
    def sync_request(self, energy_account, published_min, published_max):
        """Times need to be input as datetime objects"""
        url = 'https://api.pge.com/GreenButtonConnect/espi/1_1/resource'
        url = url + '/Batch/Subscription/{}/UsagePoint/{}?published-max={}&published-min={}'.format(
            energy_account.pge_subscription_id,
            energy_account.pge_usage_point,
            published_max.strftime('%Y-%m-%dT%H:%m:%SZ'),
            published_min.strftime('%Y-%m-%dT%H:%m:%SZ')
        )
        header_params = {'Authorization': 'Bearer ' + energy_account.pge_access_token}
        request = requests.get(url, data={},  headers=header_params, cert=self.cert)
        if str(request.status_code) == "200":
            response = {"status": request.status_code, "data": request.text}
            """
            current_user.log_event(info='SUCCESS - PGE Data Pull by {}. Response Code: {} Response Message: {} Dates:{}-{}'.format(
                current_user.full_name,
                response['status'],
                response['data'][:65],
                published_min,
                published_max
                )
            )
            """
            return response['data']
        response = {"status": request.status_code, "error": request.text}
        """
        current_user.log_event(info='FAILURE - PGE Data Pull by {}. Response Code: {} Error Message: {} Dates:{}-{}'.format(
            current_user.full_name,
            response['status'],
            response.get('error', None),
            published_min,
            published_max
            )
        )
        """
        return response

    def sync_simple_request(self, url, energy_account):
        """Times need to be input as datetime objects"""
        header_params = {'Authorization': 'Bearer ' + energy_account.pge_access_token}
        request = requests.get(url, data={},  headers=header_params, cert=self.cert)
        if str(request.status_code) == "200":
            response = {"status": request.status_code, "data": request.text}
            return response['data']
        response = {"status": request.status_code, "error": request.text}
        return response

    # API async request using Oauth2 access token
    def async_request(self, url, subscription_id, published_min, published_max, access_token):
        url = url + "/Subscription/" + subscription_id
        url += "?published-max=" + published_max + "&published-min=" + published_min
        header_params = {'Authorization': 'Bearer ' + access_token}
        request = requests.get(url, data={},  headers=header_params, cert=self.cert)
        if str(request.status_code) == "202":
            response = {"status": request.status_code, "data": request.text}
            return response
        response = {"status": request.status_code, "error": request.text}
        return response


class ClientCredentials:
    """
    This API for  to get client_credentials from PG&E
    This is used by PG&E thrid parties.
    :Author: Bharati V
    """
    def __init__(self, client_credentials_hash, cert_params_hash):
        client_key = client_credentials_hash["client_key"]
        client_secret_key = client_credentials_hash["client_secret_key"]
        self.cert = (cert_params_hash["crt"], cert_params_hash["key"])
        self.base64code = 'Basic ' + bytes.decode(b64encode(('%s:%s' % (client_key, client_secret_key)).encode('latin1')).strip())

    # To get client_credentials    from PG&E
    def get_client_access_token(self, url):
        request_params = {'grant_type': 'client_credentials'}
        header_params = {'Authorization': self.base64code}
        response = requests.post(url, data=request_params, headers=header_params, cert=self.cert)
        if str(response.status_code) == "200":
            res = response.json()
            res.update({"status": response.status_code})
            return res
        return {"status": response.status_code, "error": response.text}


class OAuth2:
    """
    For safe Authentication OAuth2 is defined.
    This API's provides the  OAuth2 access token from PG&E.
    This is used by PG&E thrid parties.
    :Author: Bharati V
    """
    def __init__(self, client_credentials_hash, cert_params_hash):
        client_key = client_credentials_hash["client_key"]
        client_secret_key = client_credentials_hash["client_secret_key"]
        self.cert = (cert_params_hash["crt"], cert_params_hash["key"])
        self.base64code = 'Basic ' + bytes.decode(b64encode(('%s:%s' % (client_key, client_secret_key)).encode('latin1')).strip())

    # Get Acces Token
    def get_access_token(self, url, code, redirect_uri, energy_account):
        request_params = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
        header_params = {'Authorization': self.base64code}
        request = requests.post(url, data=request_params,  headers=header_params, cert=self.cert)
        if str(request.status_code) == "200":
            res = request.json()
            res.update({"status": request.status_code})

            subscription_id = res[u'resourceURI'].rsplit('/', 1)[-1]

            usage_point_xml = requests.get(
                'https://api.pge.com/GreenButtonConnect/espi/1_1/resource/Subscription/{}/UsagePoint'.format(subscription_id),
                data=request_params,
                headers={'Authorization': 'Bearer {}'.format(res.get('access_token', None))},
                cert=self.cert
            )
            print usage_point_xml.text

            # Save the access and refresh token to DB
            energy_account.pge_refresh_token = res.get('refresh_token', None)
            energy_account.pge_access_token = res.get('access_token', None)
            energy_account.pge_subscription_id = subscription_id
            try:
                from jxmlease import parse
                print parse(usage_point_xml.text, xml_attribs=True).prettyprint()
                energy_account.pge_usage_point = get_usage_point_from_xml(usage_point_xml.text)
            except:
                energy_account.pge_usage_point = 'Not found.'

            db.session.commit()

            return res

        response = {"status": request.status_code, "error": request.text}
        return response

    # Refresh token will collect back the new access token
    def get_refresh_token(self, energy_account):
        url = 'https://api.pge.com/datacustodian/oauth/v2/token'
        request_params = {"grant_type": "refresh_token", "refresh_token": energy_account.pge_refresh_token}
        header_params = {"Authorization": self.base64code}
        request = requests.post(url, data=request_params,  headers=header_params, cert=self.cert)
        if str(request.status_code) == "200":
            res = request.json()
            energy_account.pge_refresh_token = res[u'refresh_token']
            energy_account.pge_access_token = res[u'access_token']
            db.session.commit()
            res.update({"status": request.status_code})
            return res
        response = {"status": request.status_code, "error": request.text}
        return response

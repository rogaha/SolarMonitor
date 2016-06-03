import requests
import json
from base64 import b64encode

class Api:
	"""
    api.py
    ~~~~~~~~~~~~~
	This API for the  synchronous and Asynchronous XML data to get from the PG&E.
    This is used by PG&E thrid parties.
	:Author: Bharati V
	"""
	def __init__(self, cert_params_hash):
			self.cert = (cert_params_hash["crt"], cert_params_hash["key"])

	#API sync request using Oauth2 access token
	def sync_request(self, url,subscription_id,usage_point, published_min, published_max, access_token):
		url = url + "/Subscription/" + subscription_id + "/UsagePoint/"+usage_point
		url = url + "?published-max=" +published_max+ "&published-min="+published_min
		header_params = {'Authorization' : 'Bearer ' + access_token}
		request = requests.get(url, data = {},  headers = header_params, cert = self.cert)
		if str(request.status_code) == "200":
			response = {"status": request.status_code, "data": request.text}
			return response
		response = {"status": request.status_code, "error": request.text}
		return response


	#API async request using Oauth2 access token
	def async_request(self, url, subscription_id,published_min,published_max, access_token):
		url = url +"/Subscription/" + subscription_id
		url +=  "?published-max=" +published_max+ "&published-min="+published_min
		header_params = {'Authorization' : 'Bearer ' + access_token}
		request = requests.get(url, data = {},  headers = header_params, cert = self.cert)
		if str(request.status_code) == "202":
			response = {"status": request.status_code, "data": request.text}
			return response
		response = {"status": request.status_code, "error": request.text}
		return response


class ClientCredentials:
    """
    ClientCredentials.py
    ~~~~~~~~~~~~~~~~~~~~
	This API for  to get client_credentials from PG&E
    This is used by PG&E thrid parties.
	:Author: Bharati V
    """
	def __init__(self, client_credentials_hash, cert_params_hash):
		client_key = client_credentials_hash["client_key"]
		client_secret_key = client_credentials_hash["client_secret_key"]
		self.cert = (cert_params_hash["crt"], cert_params_hash["key"])
		self.base64code = 'Basic ' + bytes.decode(b64encode(('%s:%s' %(client_key,client_secret_key)).encode('latin1')).strip())

	# To get client_credentials	from PG&E
	def get_client_access_token(self, url):
		request_params = {'grant_type': 'client_credentials'}
		header_params = {'Authorization' : self.base64code}
		response = requests.post(url, data = request_params, headers = header_params, cert = self.cert)
		if str(response.status_code) == "200":
			res = response.json()
			res.update({"status": response.status_code})
			return res
		return {"status": response.status_code, "error": response.text}

class OAuth2:
    """
    OAuth2.py
    ~~~~~~~~~~~~~
	For safe Authentication OAuth2 is defined.
	This API's provides the  OAuth2 access token from PG&E.
    This is used by PG&E thrid parties.
	:Author: Bharati V
    """
	def __init__(self, client_credentials_hash, cert_params_hash):
		client_key = client_credentials_hash["client_key"]
		client_secret_key = client_credentials_hash["client_secret_key"]
		self.cert = (cert_params_hash["crt"], cert_params_hash["key"])
		self.base64code = 'Basic ' + bytes.decode(b64encode(('%s:%s' %(client_key,client_secret_key)).encode('latin1')).strip())


	#Get Acces Token
	def get_access_token(self, url, code, redirect_uri):
		request_params = {"grant_type":"authorization_code", "code": code , "redirect_uri":redirect_uri}
		header_params = {'Authorization' : self.base64code}
		request = requests.post(url, data = request_params,  headers = header_params, cert = self.cert)
		if str(request.status_code) == "200":
			res = request.json()
			res.update({"status": request.status_code})
			return res
		response = {"status": request.status_code, "error": request.text}
		return response


	# Refresh token will collect back the new access token
	def get_refresh_token(self, url, refresh_token):
		request_params = {"grant_type":"refresh_token", "refresh_token": refresh_token}
		header_params = {"Authorization":self.base64code}
		request = requests.post(url, data = request_params,  headers = header_params, cert = self.cert)
		if str(request.status_code) == "200":
			res = request.json()
			res.update({"status": request.status_code})
			return res
		response = {"status": request.status_code, "error": request.text}
		return response

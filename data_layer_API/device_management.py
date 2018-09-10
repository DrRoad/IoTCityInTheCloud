import falcon
import json
import logging
import sys
from ruamel.yaml import YAML
from aux_functions import *
import smartIoT_Interface as sm

config_file = "configurations.yml"

try:
	with open(config_file) as f:
		configuration_file = f.read()
except Exception as e:
	logging.error('Could not read the configuration file %s', config_file)
	sys.exit(1)

try:
	yaml=YAML(typ='safe')
	configurations = yaml.load(configuration_file)
except Exception as e:
	logging.error('Could not parse the configuraiton file')
	sys.exit(1)

try:
	url = configurations["url"]
except KeyError as e:
	logging.error('Configuration file does not have the url of the smartIoT service')
	sys.exit(1)


# Register a device on smartIoT
class RegisterDevice():

	def on_post(self, req, resp):

		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not decode the request body")
 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. Malformed JSON.')

		if not set(["name"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'The request does not have all the required fields')


		name = result_json["name"]
		logging.info("Registering device %s from %s...", name, account_id)

		device_id = None
		if "id" in result_json:
			device_id = result_json["id"]

		device_secret = None
		if "secret" in result_json:
			device_secret = result_json["secret"]

		description = None
		if "description" in result_json:
			description = result_json["description"]

		# Authenticate
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)


		token = content

		# Register device
		response = sm.register_device(url=url, token=token, name=name, device_id=device_id, secret=device_secret, description=description)
		
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_201
		resp.body = device_info
		logging.info("Registering device %s from %s done: %s", name, account_id, device_info)



class Device():

	# Update a device on SmartIoT
	def on_put(self, req, resp, device_id):
		
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not decode the request body.")
	 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,	'Malformed JSON', 'Could not decode the request body. Malformed JSON.')


		if not set(["name"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
			'Malformed JSON', 'The request does not have all the required fields')

		name = result_json["name"]
		logging.info("Update device %s from %s...", name, account_id)

		device_secret = None
		if "secret" in result_json:
			device_secret = result_json["secret"]

		description = None
		if "description" in result_json:
			description = result_json["description"]

		# Authenticate
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error updating device %s from %s: %s", name, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		# Update device information
		response = sm.update_device(url=url, id=device_id, token=token, new_name=name, new_description=description, new_secret=device_secret)

		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error updating device %s from %s: %s", name, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			elif status_code == 404:
				raise falcon.HTTPError(falcon.HTTP_404)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_204
		logging.info("Update device %s from %s done.", name, account_id)

	# Remove a device on SmartIoT
	def on_delete(self, req, resp, device_id):

		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Remove device %s from %s...", device_id, account_id)

		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error deleting device %s from %s: %s", device_id, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		# Remove device information
		response = sm.remove_device(url, device_id, token)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error deleting device %s from %s: %s", device_id, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			elif status_code == 404:
				raise falcon.HTTPError(falcon.HTTP_404)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_204
		logging.info("Deleting device %s from %s done.", device_id, account_id)

	# Get Device Details
	def on_get(self, req, resp, device_id):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")


		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Get device details %s from %s...", device_id, account_id)

		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error getting device details %s from %s: %s", device_id, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.device_details(url, device_id, token)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error getting device details %s from %s: %s", device_id, account_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			elif status_code == 404:
				raise falcon.HTTPError(falcon.HTTP_404)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_200
		resp.body = device_info
		logging.info("Getting details of device %s of %s done.", device_id, account_id)
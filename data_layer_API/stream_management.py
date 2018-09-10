import falcon
import json
import logging
import sys
from aux_functions import *
from ruamel.yaml import YAML
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


class CreateDeleteStream():

	# Create a device data stream
	def on_put(self, req, resp, device_id, stream_name):

		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Registering stream from device %s with name %s...", device_id, stream_name)
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error registering stream from device %s with name %s: %s", device_id, stream_name, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.create_stream(url, token, device_id, stream_name)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error registering stream from device %s with name %s: %s", device_id, stream_name, response)
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
		logging.info("Registering stream from device %s with name %s successfully done", device_id, stream_name)

	# Remove device stream
	def on_delete(self, req, resp, device_id, stream_name):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Removing stream %s from device %s.", stream_name, device_id)
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error removing stream from device %s with name %s: %s", device_id, stream_name, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)


		token = content
		response = sm.remove_stream(url, token, device_id, stream_name)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error removing stream from device %s with name %s: %s", device_id, stream_name, response)
			if status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			elif status_code == 404:
				raise falcon.HTTPError(falcon.HTTP_404)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_204
		logging.info("Removed stream %s from device %s successfully.", stream_name, device_id)


class PublishIntoStream():

	# Publish into a device data stream
	def on_post(self, req, resp, device_id, stream_name):
		if "DEVICE-ID" not in req.headers or "DEVICE-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of device.")

		device_id = req.headers["DEVICE-ID"]
		device_secret = req.headers["DEVICE-SECRET"]

		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not decode the request body.")
	 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,	'Malformed JSON', 'Could not decode the request body. Malformed JSON.')


		if not set(["value", "timestamp"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
			'Malformed JSON', 'The request does not have all the required fields')

		value = result_json["value"]
		timestamp = result_json["timestamp"]

		logging.info("Publishing value %s with timestamp %s in stream %s...", value, timestamp, stream_name)
		response  = sm.device_authentication(url, device_id, device_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error publishing value %s with timestamp %s in stream %s: %s", value, timestamp, stream_name, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)


		token = content
		response = sm.publish_into_stream(url, token, device_id, stream_name, timestamp, value)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.error("Error publishing value %s with timestamp %s in stream %s: %s", value, timestamp, stream_name, response)
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

		resp.status = falcon.HTTP_201
		logging.info("Publishing value %s with timestamp %s in stream %s done.", value, timestamp, stream_name)


class ListStreams():

	# List device streams
	def on_get(self, req, resp, device_id):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Listing all streams of device %s...", device_id)
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.info("Error listing all streams of device %s.", device_id)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.list_streams(url, token, device_id)
		status_code = response[0]
		device_info = response[1]

		if status_code >= 300:
			logging.info("Error listing all streams of device %s.", device_id)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			elif status_code == 403:
				raise falcon.HTTPError(falcon.HTTP_403)
			elif status_code == 404:
				raise falcon.HTTPError(falcon.HTTP_404)
			else:
				print(response)
				raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_200
		resp.body = device_info
		logging.info("List all streams of device %s done.", device_id)

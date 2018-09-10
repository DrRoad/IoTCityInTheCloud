import falcon
import json
import logging
import sys
from aux_functions import *
from ruamel.yaml import YAML
import smartIoT_Interface as sm
from subscriptions_db_interface import *
from tasks import distribute_data

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
	database_configs = configurations["database"]
except KeyError as e:
	logging.error('Configuration file does not have the password of the device')
	sys.exit(1)

try:
	database_name = database_configs["dbname"]
except KeyError as e:
	logging.error('Configuration file does not have the name of the database')
	sys.exit(1)

try:
	database_user = database_configs["user"]
except KeyError as e:
	logging.error('Configuration file does not have the username of the database')
	sys.exit(1)

try:
	database_pass = database_configs["password"]
except KeyError as e:
	logging.error('Configuration file does not have the password of the user to access the database')
	sys.exit(1)

try:
	database_host = database_configs["host"]
except KeyError as e:
	logging.error('Configuration file does not have the host of the database')
	sys.exit(1)

try:
	url = configurations["url"]
except KeyError as e:
	logging.error('Configuration file does not have the url of the smartIoT service')
	sys.exit(1)

try:
	service_url = configurations["service_url"]
except KeyError as e:
	logging.error('Configuration file does not have the service url')
	sys.exit(1)

try:
	prefix_point_of_contact = configurations["prefix_point_of_contact"]
except KeyError as e:
	logging.error('Configuration file does not have the prefix point of contact')
	sys.exit(1)

try:
	postfix_point_of_contact = configurations["postfix_point_of_contact"]
except KeyError as e:
	logging.error('Configuration file does not have the postfix point of contact')
	sys.exit(1)

try:
	receivers = configurations["receivers"]
except KeyError as e:
	logging.error('Configuration file does not have any receiver configured')
	sys.exit(1)

try:
	db = SubscriptionsDBInterface(database_host, database_name, database_user, database_pass)
except Exception as e:
	logging.error("Could not connect to database")
	sys.exit(1)

class SubscribeStream():

	# Create subscription
	def on_post(self, req, resp):

		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]
		
		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Error',
				ex.message)
 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The '
				'JSON was incorrect.')

		if not set(["subscriber_id", "name", "device_id", "stream_name", "device_secret"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The request does not have all the required fields')
		else:
			subscription_name = result_json["name"]
			subscriber_id = result_json["subscriber_id"]
			stream_name = result_json["stream_name"]
			device_id = result_json["device_id"]
			device_secret = result_json["device_secret"]

			description = None
			state = None
			polling = False
			point_of_contact = None

			if "description" in result_json:
				description = result_json["description"]

			if "state" in result_json:
				state = result_json["state"]

			if "method" in result_json:
				if result_json["method"] == "pull":
					polling = True

			logging.info("Subscribing stream %s from device with name %s for device ...", stream_name, device_id, subscription_name, subscriber_id)

			response = sm.authenticate(url, account_id, account_secret)
			status_code = response[0]
			content = response[1]

			if status_code >= 300:
				logging.error("Error subscribing stream %s from device with name %s for device: %s", stream_name, device_id, subscription_name, subscriber_id, response)
				if status_code == 400:
					raise falcon.HTTPError(falcon.HTTP_400)
				elif status_code == 401:
					raise falcon.HTTPError(falcon.HTTP_401)
				else:
					raise falcon.HTTPError(falcon.HTTP_500)

			token = content
			response = sm.create_subscription(url=url, account_token=token, name=subscription_name, subs_id=subscriber_id, device_id=device_id, 
				stream_name=stream_name, retry_policy="30,45,60", description=description, state=state, point_of_contact=point_of_contact)

			if status_code >= 300:
				logging.error("Error subscribing stream %s from device with name %s for device: %s", stream_name, device_id, subscription_name, subscriber_id, response)
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

			if "id" not in json.loads(response[1]):
				logging.error(json.loads(response[1]))
				raise falcon.HTTPError(falcon.HTTP_400)
			
			sub_id = json.loads(response[1])["id"]

			# Now that we have got the ID, update the subscription with point of contact
			if not polling:
				point_of_contact = service_url+prefix_point_of_contact+"/"+str(sub_id)+postfix_point_of_contact
				response = sm.update_subscription(url=url, account_token=token, subs_id=sub_id, new_name=subscription_name, retry_policy="30,45,60", new_desc=description, new_state=state, point_of_contact=point_of_contact)
				status_code = response[0]
				content = response[1]

				if status_code >= 300:
					logging.error("Error updating the subscription %s: %s", subscription_name, response)
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

			try:
				db.insert_subscription(sub_id, device_id, device_secret, polling)
			except Exception as e:
				logging.error("Could not insert subscription on the DB: %s", e)
				raise falcon.HTTPError(falcon.HTTP_500)

			resp.body = json.dumps({"subscription_id": sub_id})
			resp.status = falcon.HTTP_201
			logging.info("Subscribed stream %s from device with name %s for device successfully.", stream_name, device_id, subscription_name, subscriber_id)


class SubscriptionManagement():

	# Update subscription
	def on_put(self, req, resp, subscription_id):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]
		
		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Error',
				ex.message)
 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The '
				'JSON was incorrect.')

		if not set(["name"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The request does not have all the required fields')

		subscription_name = result_json["name"]

		description = None
		state = None
		polling = False
		point_of_contact = prefix_point_of_contact+"/"+str(subscription_id)+postfix_point_of_contact


		if "description" in result_json:
			description = result_json["description"]

		if "state" in result_json:
			state = result_json["state"]

		if "method" in result_json:
			if result_json["method"] == "pull":
				point_of_contact = None
				polling = True

		logging.info("Updating subscription %s...", subscription_name)

		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error updating the subscription %s: %s", subscription_name, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.update_subscription(url=url, account_token=token, subs_id=subscription_id, new_name=subscription_name, retry_policy="30,45,60", new_desc=description, new_state=state, point_of_contact=point_of_contact)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error updating the subscription %s: %s", subscription_name, response)
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

		try:
			db.update_polling(subscription_id, polling)
		except Exception as e:
			logging.error("Could not update the DB: %s", e)
			raise falcon.HTTPError(falcon.HTTP_500)

		resp.status = falcon.HTTP_204
		logging.info("Subscription %s was successfully updated.", subscription_name)


	# Retrieve subscription details
	def on_get(self, req, resp, subscription_id):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Getting the information of the subscription %s...", subscription_id)
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error getting information about subscription %s: %s", subscription_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.get_subscription_details(url, token, subscription_id)
		status_code = response[0]
		content = response[1]
		if status_code >= 300:
			logging.error("Error getting information about subscription %s: %s", subscription_id, response)
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

		return_response = json.loads(response[1])

		if "retry_policy" in return_response:
			del return_response["retry_policy"]

		if "retries" in return_response:
			del return_response["retries"]

		if "point_of_contact" in return_response:
			if return_response["point_of_contact"] == None:
				return_response["method"] = "pull"
				del return_response["point_of_contact"]
			else:
				del return_response["point_of_contact"]
				return_response["method"] = "push"


		resp.status = falcon.HTTP_200
		resp.body = json.dumps(return_response)
		logging.info("Done getting the information of the subscription %s.", subscription_id)


	# Remove subscription
	def on_delete(self, req, resp, subscription_id):
		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]

		logging.info("Deleting subscription %s...", subscription_id)
		response = sm.authenticate(url, account_id, account_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error deleting subscription %s: %s", subscription_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.remove_subscription(url, token, subscription_id)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error deleting subscription %s: %s", subscription_id, response)
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

		try:
			db.remove_subscription(subscription_id)
		except Exception as e:
			logging.error("Could not remove subscription from the DB: %s", e)
			raise falcon.HTTPError(falcon.HTTP_500)
	
		resp.status = falcon.HTTP_204
		logging.info("Subscription %s deleted.", subscription_id)



class SubscriptionValues():

	# Retrieve subscription values
	def on_get(self, req, resp, subscription_id):
		if "DEVICE-ID" not in req.headers or "DEVICE-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		device_id = req.headers["DEVICE-ID"]
		device_secret = req.headers["DEVICE-SECRET"]

		logging.info("Fetching values from subscription %s.", subscription_id)

		response  = sm.device_authentication(url, device_id, device_secret)
		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error fetching values from subscription %s: %s", subscription_id, response)
			if status_code == 400:
				raise falcon.HTTPError(falcon.HTTP_400)
			elif status_code == 401:
				raise falcon.HTTPError(falcon.HTTP_401)
			else:
				raise falcon.HTTPError(falcon.HTTP_500)

		token = content
		response = sm.retrieve_subscription_values(url, token, subscription_id)

		status_code = response[0]
		content = response[1]

		if status_code >= 300:
			logging.error("Error fetching values from subscription %s: %s", subscription_id, response)
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

		values = []

		if "values" in json.loads(response[1]):
			for value in json.loads(response[1])["values"]:
				del value["timeToLive"]
				values.append(json.dumps(value))

		return_response = json.loads("{\"Values\":["+", ".join(values)+"]}")

		resp.status = falcon.HTTP_200
		resp.body = json.dumps(return_response)
		logging.info("Values from subscription %s successfully fetched.", subscription_id)



class PointOfContact():

	# Subscription point-of-contact
	def on_post(self, req, resp, subscription_id):

		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Error',
				ex.message)
 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The '
				'JSON was incorrect.')

		if not set(["data", "streamId", "id", "deviceId", "createdAt"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The request does not have all the required fields')
		else:
			
			exists = False
			
			try:
				exists = db.check_exists_subscription_with_push(subscription_id)
			except Exception as e:
				logging.error("Could not access the DB: %s", e)
				raise falcon.HTTPError(falcon.HTTP_500)

			if not exists:
				logging.error("Subscription ID could not be found in the local database: %s", subscription_id)
				raise falcon.HTTPError(falcon.HTTP_401)

			result_json["subscriptionId"] = subscription_id
			resp.status = falcon.HTTP_204
			distribute_data([result_json], receivers)
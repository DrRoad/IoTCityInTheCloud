import logging, falcon, json, datetime, pytz
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import requests
from alert_db_interface import *
from aux_functions import *
import sys


prometheus_url = "0.0.0.0:9091"
database_host = "0.0.0.0"
database_port = 5435
database_name = "alerts"
database_user = "alertManager"
database_pass = "alertManager"
zone = 'Europe/Lisbon'
SERVICE_LAYER_URL = "http://localhost:8000"

try:
	db = AlertDBInterface(database_host, database_port, database_name, database_user, database_pass)
except Exception as e:
	logging.error("Could not connect to database: %s", e)
	sys.exit(1)

class DataReceiver(object):

	def on_post(self, req, resp):
		logging.info("Received data...")
		
		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error('Data received not in the right format: %s', bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"Status": "error"})
			return

		if "subscriptionId" not in parsed_data or "data" not in parsed_data:
			logging.error('Data received not in the right format: %s', bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"Status": "error"})
			return

		topic = parsed_data["subscriptionId"]
		value = float(parsed_data["data"])

		'''
		return_code = self.push_gateway(topic, value)

		if return_code == False:
			logging.error('Could not save the data on the database')
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "error"})
			return
		'''

		alerts = db.get_alerts_by_subscription(topic)
		for a in alerts:
			if (a[2]=="MAX" and a[1]<value):
				logging.info("Find a new maximum alert to the alert ID %s", a[0])
				db.insert_triggered_alert(a[0])
				self.check_actuators(a[0])
			elif (a[2]=="MIN" and a[1]>value):
				logging.info("Find a new minimum alert to the alert ID %s", a[0])
				db.insert_triggered_alert(a[0])
				self.check_actuators(a[0])

		logging.info("Done receiving new data")
		resp.status = falcon.HTTP_202
		resp.body = json.dumps({"Status": "OK"})


	def check_actuators(self, alert_id):
		logging.info("Checking actuators for alert %s...", alert_id)

		actuators = db.get_actuators_by_alert(alert_id)

		for act in actuators:
			headers = {"Content-Type":"application/json", "ACCOUNT-ID": act[1], "ACCOUNT-SECRET": act[2]}
			data = {"value": act[3], "timestamp": (datetime.datetime.now(pytz.timezone(zone))+datetime.timedelta(hours=1)).isoformat()}

			try:
				r = requests.post(SERVICE_LAYER_URL+"/device/"+act[4]+"/stream/"+act[5], headers=headers, data=json.dumps(data))
			except requests.exceptions.RequestException as e:
				logging.error("Could not post value %s to stream %s of device %s: %s", act[3], act[5], act[4], e)


	def push_gateway(self, topic, message):
		logging.info("Pushing data: %s-%s...", topic, message)
		registry = CollectorRegistry()
		g = Gauge(topic, message, registry=registry)
		g.set_to_current_time()
		g.set(message)
		try:
			push_to_gateway(prometheus_url, job='batchA', registry=registry)
		except Exception as e:
			logging.error("Could not connect to prometheus: %s", e)
			return False
		logging.info("Data pushed successfully!")
		return True


class TriggeredAlert(object):

	# Dismiss the triggered alert
	def on_put(self, req, resp, triggered_alert_id):
		logging.info("Dismissing the alert...")

		try:
			db.dismiss_triggered_alert(triggered_alert_id)
		except Exception as e:
			logging.error("Could not dismiss triggered alert: %s", e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Internal Server Error"})
			return

		logging.info("Triggered alert successfully dismissed.")
		resp.status = falcon.HTTP_204


class AlertsManagement(object):

	# Create a new alert
	def on_post(self, req, resp):
		logging.info("Create a new alert...")

		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error('Data received not in the right format: %s', bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"Status": "error"})
			return

		if "subscriptionId" not in parsed_data or "threshold" not in parsed_data or "alarm_type" not in parsed_data:
			logging.error('Data received not in the right format: %s', bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"Status": "error"})
			return

		subscription_id = parsed_data["subscriptionId"]
		threshold = parsed_data["threshold"]
		alarm_type = parsed_data["alarm_type"]

		try:
			db.insert_alert(subscription_id, threshold, alarm_type)
		except Exception as e:
			logging.error("Could not save alert: %s", e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Internal Server Error"})
			return

		logging.info("Alert successfully inserted.")
		resp.status = falcon.HTTP_201
		resp.body = json.dumps({"Status": "Created"})

	# Get information about all alerts
	def on_get(self, req, resp):
		logging.info("Fetching all alerts...")

		alerts = []

		try:
			alerts = db.get_all_alerts()
		except Exception as e:
			logging.error("Could not get all alerts %s", e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Internal Server Error"})
			return

		alerts = [{"id": al_elem[0], "subscription_id": al_elem[1], "threshold": al_elem[2], "alarm_type": al_elem[3]} for al_elem in alerts]


		logging.info("All alerts fetched and returned successfully")
		resp.status = falcon.HTTP_200
		resp.body = json.dumps(alerts)


class AlertManagement(object):
	# Delete an alert
	def on_delete(self, req, resp, alert_id):

		logging.info("Deleting the alert %s...", alert_id)
		try:
			db.remove_alert(alert_id)
		except Exception as e:
			logging.error("Could not remove the alert %s: %s", alert_id, e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Internal Server Error"})
			return

		logging.info("Alert %s removed successfully", alert_id)
		resp.status = falcon.HTTP_204

class TriggeredAlertsManagement(object):
	def on_get(self, req, resp):
		logging.info("Fetching all triggered alerts...")

		triggered_alerts = []

		try:
			triggered_alerts = db.get_all_triggered_alerts_not_dismissed()
		except Exception as e:
			logging.error("Could not get triggered alerts %s", e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Internal Server Error"})
			return

		triggered_alerts = [{"id": al_elem[0], "alert_id": al_elem[1], "trigger_time": al_elem[2].strftime("%Y-%m-%d %H:%M:%S")} for al_elem in triggered_alerts]


		logging.info("All triggered alerts fetched and returned successfully")
		resp.status = falcon.HTTP_200
		resp.body = json.dumps(triggered_alerts)


class ActuatorManagement(object):
	
	def on_post(self, req, resp):
		logging.info("Adding actuator...")

		if "ACCOUNT-ID" not in req.headers or "ACCOUNT-SECRET" not in req.headers:
			raise falcon.HTTPError(falcon.HTTP_400, 'Error', "Could not get the ID and secret of account.")

		account_id = req.headers["ACCOUNT-ID"]
		account_secret = req.headers["ACCOUNT-SECRET"]
		
		try:
			raw_json = bytes_to_string(req.stream.read())
		except Exception as ex:
			raise falcon.HTTPError(falcon.HTTP_400,	'Error', ex.message)
 
		try:
			result_json = json.loads(raw_json)
		except ValueError:
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The '
				'JSON was incorrect.')

		if not set(["alertId", "value", "deviceId", "streamName"]).issubset(result_json):
			raise falcon.HTTPError(falcon.HTTP_400,
				'Malformed JSON',
				'Could not decode the request body. The request does not have all the required fields')

		alert_id = result_json["alertId"]
		value = result_json["value"]
		device_id = result_json["deviceId"]
		stream_name = result_json["streamName"]

		try:
			db.insert_actuator(alert_id, account_id, account_secret, value, device_id, stream_name)
		except Exception as e:
			logging.error("Could not save actuator: %s", e)
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"Status": "Alarm not Found"})
			return

		logging.info("The actuator was successfully added")
		resp.status = falcon.HTTP_201
		resp.body = json.dumps({"Status": "OK"})


class ActuatorDelete(object):

	def on_delete(self, req, resp, actuator_id):
		logging.info("Deleting actuator %s", actuator_id)

		try:
			db.remove_actuator(actuator_id)
		except Exception as e:
			logging.error("Could not delete actuator %s: %s", actuator_id, e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Actuator could not be removed."})
			return

		logging.info("Actuator %s removed successfully", actuator_id)
		resp.status = falcon.HTTP_204
		resp.body = json.dumps({"Status": "OK"})

class ListAlertActuators(object):

	def on_get(self, req, resp, alert_id):
		logging.info("Listing all actuators from alert %s", alert_id)

		try:
			actuators = db.get_actuators_by_alert(alert_id)
		except Exception as e:
			logging.error("Could not fetch the actuators from the alert %s: %s", alert_id, e)
			resp.status = falcon.HTTP_500
			resp.body = json.dumps({"Status": "Actuators could not be listed"})
			return

		actuator_list = [{"id": act[0], "account_id": act[1], "account_secret": act[2], "value": act[3], "device_id": act[4], "stream_name": act[5]} for act in actuators]
		logging.info("Actuators from alert %s successfully listed", alert_id)
		resp.status = falcon.HTTP_200
		resp.body = json.dumps(actuator_list)


app = falcon.API()
data_receiver = DataReceiver()
alerts_management = AlertsManagement()
alert_management = AlertManagement()
triggered_alerts = TriggeredAlertsManagement()
dismiss_triggered_alert = TriggeredAlert()
actuator_management = ActuatorManagement()
actuator_delete = ActuatorDelete()
get_actuators = ListAlertActuators()

app.add_route('/push_data', data_receiver)
app.add_route('/alerts', alerts_management)
app.add_route('/alert/{alert_id}', alert_management)
app.add_route('/triggered', triggered_alerts)
app.add_route('/triggered/{triggered_alert_id}/dismiss', dismiss_triggered_alert)
app.add_route('/actuator', actuator_management)
app.add_route('/actuator/{actuator_id}', actuator_delete)
app.add_route('/alert/{alert_id}/actuators', get_actuators)

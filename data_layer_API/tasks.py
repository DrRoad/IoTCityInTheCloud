import smartIoT_Interface as sm
import logging, json, requests
from ruamel.yaml import YAML
from _celery import app
from requests.exceptions import ConnectionError



@app.task
def get_data_from_smartIoT(subscription_id_list, service_url, device_id, device_password):
	logging.info('Getting data from smartIoT...')
	data = []

	# Authentication
	auth = sm.device_authentication(service_url, device_id, device_password)

	if auth[0] != 201:
		logging.error('Error on authentication on SmartIoT: %s' % auth)
		return []

	# For all the subscriptions on the list, get the values and save them on a list
	for subscription_id in subscription_id_list:
		ret = sm.retrieve_subscription_values(service_url, auth[1], subscription_id)
		
		if ret[0]==200:
			
			try:
				values_list = json.loads(ret[1])["values"]
				for value in values_list:
					logging.info('Received value from SmartIoT: %s' % value)
					del value["timeToLive"]
					value["subscriptionId"] = subscription_id
					data += [value]
			except ConnectionError as e:
				logging.error('Could not load the values from the message received from SmartIoT: %s' % e)

		else:
			logging.error('Could not get the values from SmartIoT.')
			return []

	return data


@app.task
def distribute_data(data_list, receiver_list):
	logging.info("Distributing data...")

	# Send the data received to all the receivers configured
	for receiver in receiver_list:
		for data in data_list:
			try:
				r = requests.post(receiver, json=data)
			except ConnectionError as e:
				logging.error("Connection error when sending %s to %s", data, receiver)


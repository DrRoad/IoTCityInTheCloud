import logging
import json
import argparse
import time
from celery import Celery
from tasks import *
from subscriptions_db_interface import SubscriptionsDBInterface


class DataFetcher():

	def __init__(self, config_file):
		self.config_file = config_file
		config_state = self.read_configuration_file(config_file)

		if config_state == False:
			raise Exception

	'''
		Returns all subscriptions to fetch the data from SmartIoT
	'''
	def get_all_subscriptions(self):
		db = SubscriptionsDBInterface(self.database_host, self.database_name, self.database_user, self.database_pass)
		subscriptions = db.get_all_subscriptions_and_devices()

		return subscriptions

	'''
		Gets all data from SmartIoT and sends it to the receivers
	'''
	def fetch_data(self):
		logging.info("Start fetching data...")

		done = False

		while not done:
			try:
				all_subscriptions = self.get_all_subscriptions()
				done = True
			except:
				time.sleep(1)
				done = False

		# Executes two function pipelined asynchronously
		for subscription in all_subscriptions:
			c1 = (get_data_from_smartIoT.s(self.service_url, subscription[1], subscription[2]) | distribute_data.s(self.receivers))
			res = c1([subscription[0]])

		logging.info("Data fetching done!")



	'''
		Read the configurations from a file
	'''
	def read_configuration_file(self, config_file):

		# Read the configurations for the smartIoT_receiver

		try:
			with open(config_file) as f:
				configuration_file = f.read()
		except Exception as e:
			logging.error('Could not read the configuration file %s', config_file)
			return False

		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(configuration_file)
		except Exception as e:
			logging.error('Could not parse the configuraiton file')
			return False

		try:
			self.period = configurations["period"]
		except KeyError as e:
			logging.error('Configuration file does not have the period')
			return False

		try:
			database_configs = configurations["database"]
		except KeyError as e:
			logging.error('Configuration file does not have the password of the device')
			return False

		try:
			self.database_name = database_configs["dbname"]
		except KeyError as e:
			logging.error('Configuration file does not have the name of the database')
			return False

		try:
			self.database_user = database_configs["user"]
		except KeyError as e:
			logging.error('Configuration file does not have the username of the database')
			return False

		try:
			self.database_pass = database_configs["password"]
		except KeyError as e:
			logging.error('Configuration file does not have the password of the user to access the database')
			return False

		try:
			self.database_host = database_configs["host"]
		except KeyError as e:
			logging.error('Configuration file does not have the host of the database')
			return False

		try:
			self.receivers = configurations["receivers"]
		except KeyError as e:
			logging.error('Configuration file does not have any receiver configured')
			return False

		try:
			self.service_url = configurations["url"]
		except KeyError as e:
			logging.error('Configuration file does not have the url of the smartIoT service')
			return False

		return True


if __name__ == "__main__":
	
	logging.basicConfig(
		format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
		level=logging.INFO
	)

	parser = argparse.ArgumentParser()
	parser.add_argument('config_file', help='Configuration file path in YAML format')
	config_file = parser.parse_args().config_file
	
	
	fetcher = DataFetcher(config_file)


	while(True):
		fetcher.fetch_data()
		time.sleep(fetcher.period)


import logging, falcon, json
from aux_functions import *
from pymongo import MongoClient

mongo_url = 'localhost'

class DataReceiver(object):

	def __init__(self):
		self.client = MongoClient(mongo_url, 27017)
		self.db = self.client.data

	def on_post(self, req, resp):
		logging.info("POST to database received")
		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error('Data received not in the right format: %s', bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps("{Status: Error}")
			return

		inserted_id = self.db.metrics.insert_one(parsed_data)
		logging.info("Correctly inserted with id %s", inserted_id)
		resp.status = falcon.HTTP_202
		resp.body = json.dumps("{Status: OK}")

class RetrieveData(object):
	def __init__(self):
		self.client = MongoClient(mongo_url, 27017)
		self.db = self.client.data

	def on_get(self, req, resp, subscription_id):
		values = [res for res in self.db.metrics.find({"createdAt": {"$exists": True}, "subscriptionId": subscription_id, "data": {"$exists": True}}, {'_id': False}).sort("createdAt")]
		resp.content_type = "application/json"
		resp.body = json.dumps({'Values': values})
		resp.status = falcon.HTTP_200

app = falcon.API()
data_receiver = DataReceiver()
retrieve_data = RetrieveData()

app.add_route('/push_data', data_receiver)
app.add_route('/values/{subscription_id}', retrieve_data)

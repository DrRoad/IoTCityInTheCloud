import psycopg2
import logging

'''

	Class that creates the connection to the database

'''
class SubscriptionsDBInterface:

	def __init__(self, host, dbname, user, password):

		try:
			self.conn = psycopg2.connect(host=host, dbname=dbname, user=user, password=password)
			self.cur = self.conn.cursor()
		except Exception as e:
			logging.warning("Could not create connection to database: %s", e)
			exit(1)

	def get_all_subscriptions_and_devices(self):
		self.cur.execute("SELECT * FROM get_all_subscriptions_with_devices_for_pooling();")
		res = self.cur.fetchall()
		return [(sub[0], sub[1], sub[2]) for sub in res]

	def insert_subscription(self, subscription_id, device_id, device_secret, pooling):
		self.cur.execute("SELECT * FROM insert_subscription_and_device(%(subscription_id)s, %(device_id)s, %(device_secret)s, %(pooling)s);", {"subscription_id":subscription_id, "device_id": device_id, "device_secret": device_secret, "pooling": pooling})
		self.conn.commit()

	def update_pooling(self, subscription_id, pooling):
		self.cur.execute("SELECT * FROM update_pooling(%(subscription_id)s, %(pooling)s);", {"subscription_id":subscription_id, "pooling": pooling})
		self.conn.commit()

	def remove_subscription(self, subscription_id):
		self.cur.execute("SELECT * FROM remove_subscription(%(subscription_id)s);", {"subscription_id":subscription_id})
		self.conn.commit()

	def check_exists_subscription_with_push(self, subscription_id):
		self.cur.execute("SELECT * FROM exists_subscription_push(%(subscription_id)s);", {"subscription_id":subscription_id})
		res = self.cur.fetchone()
		return res[0]


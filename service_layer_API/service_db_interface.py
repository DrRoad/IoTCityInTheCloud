import psycopg2
import logging

'''

	Class that creates the connection to the database

'''

class ServiceDBInterface:

	def __init__(self, host, port, dbname, user, password):

		try:
			self.conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
			self.cur = self.conn.cursor()
		except Exception as e:
			logging.warning("Could not create connection to database: %s", e)
			exit(1)

	def list_all_verticals(self):
		self.cur.execute("SELECT * FROM get_all_verticals();")
		res = self.cur.fetchall()
		return [sub[0] for sub in res]

	def insert_vertical(self, vertical_name):
		self.cur.execute("SELECT * FROM insert_vertical(%(vertical)s);", {"vertical":vertical_name})
		self.conn.commit()

	def remove_vertical(self, vertical_name):
		self.cur.execute("SELECT * FROM remove_vertical(%(vertical)s);", {"vertical": vertical_name})
		self.conn.commit()

	def insert_device(self, name, vertical, description, location, id, secret):
		self.cur.execute("SELECT * FROM insert_device( %(name)s, %(vertical)s, %(description)s, %(location)s, %(id)s, %(secret)s)", {"name": name, "vertical": vertical, "description": description, "location": location, "id": id, "secret": secret})
		self.conn.commit()

	def list_all_devices(self):
		self.cur.execute("SELECT * FROM get_all_devices();")
		res = self.cur.fetchall()
		return [(dev[0], dev[1], dev[2], dev[3], dev[4], dev[5]) for dev in res]

	def delete_device(self, id):
		self.cur.execute("SELECT * FROM remove_device(%(id)s);", {"id": id})
		self.conn.commit()

	def get_id_all_devices(self):
		self.cur.execute("SELECT * FROM get_id_all_devices();")
		res = self.cur.fetchall()
		return [sub[0] for sub in res]

	def insert_stream(self, name, device_id, description=None, actuator=False):
		self.cur.execute("SELECT * FROM insert_stream( %(name)s, %(device_id)s, %(description)s, %(actuator)s)", {"name": name, "device_id": device_id, "description": description, "actuator": actuator})
		self.conn.commit()

	def get_streams_of_device(self, device_id):
		self.cur.execute("SELECT * FROM get_streams_of_device(%(device_id)s)", {"device_id": device_id})
		res = self.cur.fetchall()
		return [(st[0], st[1], st[2], st[3]) for st in res]

	def delete_stream(self, device_id, stream_name):
		self.cur.execute("SELECT * FROM remove_stream(%(device_id)s, %(stream_name)s);", {"device_id": device_id, "stream_name": stream_name})
		self.conn.commit()

	def subscribe_stream(self, subscription_id, name, subscriber_id, device_id, device_secret, stream_name, description, state, method):
		self.cur.execute("SELECT * FROM insert_subscription(%(subscription_id)s, %(name)s, %(subscriber_id)s, %(device_id)s, %(device_secret)s, %(stream_name)s, %(description)s, %(state)s, %(method)s);", {"subscription_id": subscription_id, "name": name, "subscriber_id": subscriber_id, "device_id": device_id, "device_secret": device_secret, "stream_name": stream_name, "description": description, "state": state, "method": method})
		self.conn.commit()

	def list_all_subscriptions(self):
		self.cur.execute("SELECT * FROM get_all_subscriptions();")
		res = self.cur.fetchall()
		return [(sub[0], sub[1], sub[2], sub[3], sub[4], sub[5], sub[6], sub[7], sub[8]) for sub in res]

	def delete_subscription(self, subscription_id):
		self.cur.execute("SELECT * FROM remove_subscription(%(subscription_id)s);", {"subscription_id": subscription_id})
		self.conn.commit()

	def get_device_password_to_actuate(self, device_id, stream_name):
		self.cur.execute("SELECT * FROM get_device_password_to_actuate(%(device_id)s, %(stream_name)s)", {"device_id": device_id, "stream_name": stream_name})
		res = self.cur.fetchall()
		return [dev[0] for dev in res]

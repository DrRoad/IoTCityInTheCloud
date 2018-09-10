import psycopg2
import logging

'''

	Class that creates the connection to the database

'''

class AlertDBInterface:

	def __init__(self, host, port, dbname, user, password):

		try:
			self.conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
			self.cur = self.conn.cursor()
		except Exception as e:
			logging.warning("Could not create connection to database: %s", e)
			exit(1)

	def get_all_alerts(self):
		self.cur.execute("SELECT * FROM get_all_alerts();")
		res = self.cur.fetchall()
		return [[sub[0], sub[1], sub[2], sub[3]] for sub in res]

	def get_alert_by_id(self, alert_id):
		self.cur.execute("SELECT * FROM get_alert_by_id(%(alert_id)s);", {"alert_id": alert_id})
		res = self.cur.fetchall()
		return [[sub[0], sub[1], sub[2]] for sub in res]

	def get_alerts_by_subscription(self, subscription_id):
		self.cur.execute("SELECT * FROM get_subscription_alerts(%(subscription_id)s);", {"subscription_id": subscription_id})
		res = self.cur.fetchall()
		return [[sub[0], sub[1], sub[2]] for sub in res]

	def insert_alert(self, subscription_id, threshold, alert_type):
		self.cur.execute("SELECT * FROM insert_alert(%(subscription_id)s, %(threshold)s, %(alert_type)s);", 
			{"subscription_id":subscription_id, "threshold":threshold, "alert_type":alert_type})
		self.conn.commit()

	def update_alert(self, alert_id, threshold, alarm_type):
		self.cur.execute("SELECT * FROM update_alert(%(alert_id)s, %(threshold)s, %(alarm_type)s);", {"alert_id":alert_id, "threshold":threshold, "alarm_type":alarm_type})
		self.conn.commit()

	def remove_alert(self, alert_id):
		self.cur.execute("SELECT * FROM remove_alert(%(alert_id)s);", {"alert_id":alert_id})
		self.conn.commit()

	def get_all_triggered_alerts_not_dismissed(self):
		self.cur.execute("SELECT * FROM get_all_triggered_alerts_not_dismissed();")
		res = self.cur.fetchall()
		return [[sub[0], sub[1], sub[2]] for sub in res]

	def insert_triggered_alert(self, alert_id):
		self.cur.execute("SELECT * FROM insert_triggered_alert(%(alert_id)s);", {"alert_id":alert_id})
		self.conn.commit()

	def dismiss_triggered_alert(self, triggered_alert_id):
		self.cur.execute("SELECT * FROM dismiss_triggered_alert(%(triggered_alert_id)s);", {"triggered_alert_id":triggered_alert_id})
		self.conn.commit()

	def insert_actuator(self, alert_id, account_id, account_secret, value, device_id, stream_name):
		self.cur.execute("SELECT * FROM insert_actuator(%(alert_id)s, %(account_id)s, %(account_secret)s, %(value)s, %(device_id)s, %(stream_name)s);", 
			{"alert_id":alert_id, "account_id": account_id, "account_secret": account_secret,
			"value": value, "device_id": device_id, "stream_name": stream_name})
		self.conn.commit()

	def remove_actuator(self, id):
		self.cur.execute("SELECT * FROM delete_actuator(%(id)s);", {"id":id})
		self.conn.commit()

	def get_actuators_by_alert(self, alert_id):
		self.cur.execute("SELECT * FROM get_actuators_of_alert(%(alert_id)s);", {"alert_id": alert_id})
		res = self.cur.fetchall()
		return [[act[0], act[1], act[2], act[3], act[4], act[5]] for act in res]

	
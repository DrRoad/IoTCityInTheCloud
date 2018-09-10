from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
import gevent
from gevent.monkey import patch_all
patch_all()

from flask import Flask, jsonify, request, g, render_template, send_from_directory
from flask_sockets import Sockets
from flask_cors import CORS, cross_origin
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from passlib.apps import custom_app_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from sqlalchemy_utils import database_exists, create_database, drop_database

import time
import threading
import random
import webbrowser
import os
import random
import logging
import requests
import json
import datetime
import pytz

from service_db_interface import *

application = Flask(__name__)
sockets = Sockets(application)
cors = CORS(application)
swagger = Swagger(application)

application.config['SECRET_KEY'] = 'super-secret'
application.config['DEBUG'] = True
application.config['CORS_HEADERS'] = 'Content-Type'

DELAY = 5
zone = 'Europe/Lisbon'
DATA_LAYER_URL = "http://localhost:8002"
LONG_TERM_PERSISTENCE_URL = "http://localhost:8010"
ALERTS_MODULE_URL = "http://localhost:8004"
db = ServiceDBInterface("0.0.0.0", 5433, "iotcdb", "serviceLayer", "serviceLPass")

########################## Accounts Configuration #################################

# Database
POSTGRES_USER="accounts"
POSTGRES_PW="accountspw"
POSTGRES_URL="127.0.0.1:5434"
POSTGRES_DB="accountsdb"

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER,pw=POSTGRES_PW,url=POSTGRES_URL,db=POSTGRES_DB)

application.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
application.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db_accounts = SQLAlchemy(application)

# Extensions
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth('Bearer')
multi_auth = MultiAuth(basic_auth, token_auth)

# Global
token_duration = 18000


# Database initial configuratuion that executes before the first request is processed.
@application.before_first_request
def before_first_request():

	# Create any database tables that don't exist yet.
	db_accounts.create_all()

	# Insert roles, actions and permissions
	rls = [("superuser", "plataform superuser"),
		   ("admin_org", "organization admin"),
		   ("user", "organization regular user")]
	for i in range(0, len(rls)):
		role = Role(name=rls[i][0], information=rls[i][1])
		db_accounts.session.add(role)
		db_accounts.session.commit()

	acts = [("c_org", "create organization"),
			("c_usr", "create user"),
			("r_orgs", "get all organizations"),
			("r_usrs", "get all users"),
			("r_org", "get user"),
			("r_usr", "get user"),
			("c_vrt", "create vertical"), # verticals
			("r_vrts", "get verticals"),
			("d_vrt", "remove vertical"),
			("c_dev", "create device"), # devices
			("r_devs", "get devices"),
			("d_dev", "remove device"),
			("c_stm", "create stream"), # streams
			("r_stms", "get streams"),
			("d_stm", "delete stream"),
			("post_stm_vl", "post stream value"),
			("c_sub", "create (subscribe) data stream"),
			("r_subs", "get subscriptions"),
			("d_sub", "delete (unsubscribe) data stream"),
			("r_sub_vls", "get subscription values"),
			("g_alts", "get alerts"),
			("c_alt", "create alert"),
			("d_alt", "delete alert"),
			("r_trg_alt", "get triggered alert"),
			("dismiss_trg_alt", "dismiss triggered alert"),
			("c_act", "create actuator"),
			("d_act", "delete actuator"),
			("r_act_id", "get actuator by id")
			]
	for i in range(0, len(acts)):
		act = Action(name=acts[i][0], information=acts[i][1])
		db_accounts.session.add(act)
		db_accounts.session.commit()

	prms = [("1", "1"), # superuser - create organization
			("1", "2"), # superuser - create user
			("1", "3"), # superuser - get all organizations
			("1", "4"), # superuser - get all users
			("1", "5"), # superuser - get organization
			("1", "6"), # superuser - get user
			("2", "2"), # admin_org - create user
			("2", "5"), # admin_org - get organizations
			("2", "6"), # admin_org - get user
			("3", "5"), # user - get organization
			("3", "6")] # user - get user
	for i in range(0, len(prms)):
		prm = Permission(role_id=prms[i][0], action_id=prms[i][1])
		db_accounts.session.add(prm)
		db_accounts.session.commit()

	# Insert superuser organization and superuser account
	org = Organization(name="Superuser", information="Superuser organization")
	db_accounts.session.add(org)
	db_accounts.session.commit()
	print('Superuser organization added')
	user = User(username="superuser", email="superuser@iotcc.pt", password="superuserpw", role_id="1", org_id="1")
	db_accounts.session.add(user)
	db_accounts.session.commit()
	print('Superuser user added')



# Roles class
class Role(db_accounts.Model):
	__tablename__ = 'roles'
	id = db_accounts.Column(db_accounts.Integer, primary_key=True)
	name = db_accounts.Column(db_accounts.String(32), unique=True, nullable=False)
	information = db_accounts.Column(db_accounts.String(300), nullable=False)

	def __init__(self, name, information):
		self.name = name
		self.information = information


# Actions class
class Action(db_accounts.Model):
	__tablename__ = 'actions'
	id = db_accounts.Column(db_accounts.Integer, primary_key=True)
	name = db_accounts.Column(db_accounts.String(32), unique=True, nullable=False)
	information = db_accounts.Column(db_accounts.String(300), nullable=False)

	def __init__(self, name, information):
		self.name = name
		self.information = information


# Permissions class
class Permission(db_accounts.Model):
	__tablename__ = 'permissions'
	role_id = db_accounts.Column(db_accounts.Integer, db_accounts.ForeignKey("roles.id"), primary_key=True)
	action_id = db_accounts.Column(db_accounts.Integer, db_accounts.ForeignKey("actions.id"), primary_key=True)

	role = db_accounts.relationship("Role", foreign_keys=role_id)
	action = db_accounts.relationship("Action", foreign_keys=action_id)

	def __init__(self, role_id, action_id):
		self.role_id = role_id
		self.action_id = action_id

# Organization class
class Organization(db_accounts.Model):
	__tablename__ = 'organizations'
	id = db_accounts.Column(db_accounts.Integer, primary_key=True)
	name = db_accounts.Column(db_accounts.String(32), unique=True, nullable=False)
	information = db_accounts.Column(db_accounts.String(300), nullable=False)
	date_registered = db_accounts.Column(db_accounts.DateTime, nullable=False)

	def __init__(self, name, information):
		self.name = name
		self.information = information
		self.date_registered = datetime.datetime.now()


# User class
class User(db_accounts.Model):
	__tablename__ = 'users'
	id = db_accounts.Column(db_accounts.Integer, primary_key=True)
	username = db_accounts.Column(db_accounts.String(32), unique=True, nullable=False)
	email = db_accounts.Column(db_accounts.String(32), unique=True, nullable=False)
	password_hash = db_accounts.Column(db_accounts.String(128), nullable=False)
	date_registered = db_accounts.Column(db_accounts.DateTime, nullable=False)
	role_id = db_accounts.Column(db_accounts.Integer, db_accounts.ForeignKey("roles.id"))
	org_id = db_accounts.Column(db_accounts.Integer, db_accounts.ForeignKey("organizations.id"))
	last_token = db_accounts.Column(db_accounts.String())

	org = db_accounts.relationship("Organization", foreign_keys=org_id)
	rol = db_accounts.relationship("Role", foreign_keys=role_id)


	def __init__(self, username, email, password, role_id, org_id):
		self.username = username
		self.email = email
		self.password_hash = custom_app_context.encrypt(password)
		self.date_registered = datetime.datetime.now()
		self.role_id = role_id
		self.org_id = org_id
		self.last_token = None

	def verify_password(self, password):
		return custom_app_context.verify(password, self.password_hash)

	def generate_auth_token(self, expiration=600):
		s = Serializer(application.config['SECRET_KEY'], expires_in=expiration)
		return s.dumps({'id': self.id})

	@staticmethod
	def verify_auth_token(token):
		s = Serializer(application.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except SignatureExpired:
			return None
		except BadSignature:
			return None
		user = User.query.get(data['id'])
		return user


@basic_auth.verify_password
def verify_password(username, password):
	# try to authenticate with username/password
	user = User.query.filter_by(username=username).first()
	if not user or not user.verify_password(password):
		return False
	g.user = user
	return True


@token_auth.verify_token
def verify_token(token):
	# try to authenticate with token
	user = User.verify_auth_token(token)
	if not user:
		return False
	g.user = user
	if not g.user.last_token:
		return False
	if g.user.last_token != token:
		return False
	return True



# Home
@application.route('/', methods=['GET'])
def home():
	response = {
		'status': 'success'
	}
	return (jsonify(response), 200)


# Login
@application.route('/login', methods=['POST'])
def login():
	try:
		username = request.json.get('username')
		password = request.json.get('password')

		if(not username or not password):
			code = 400
			raise Exception('null arguments')

		if(not verify_password(username, password)):
			code = 401
			raise Exception("invalid credentials")

	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	token = g.user.generate_auth_token(token_duration)

	g.user.last_token = token.decode('ascii')

	response = {
		'status': 'success',
		'id': g.user.id,
		'username': username,
		'token': token.decode('ascii'),
		'token_duration': token_duration
	}
	return (jsonify(response), 200)


# Logout
@application.route('/logout', methods=['POST'])
@multi_auth.login_required
def logout():
	g.user.last_token = None

	response = {
		'status': 'success',
		'id': g.user.id,
		'username': g.user.username
	}
	return (jsonify(response), 200)


# Authenticated
@application.route('/authenticated', methods=['GET'])
@multi_auth.login_required
def authenticated():
	response = {
		'status': 'success',
		'id': g.user.id,
		'username': g.user.username
	}
	return (jsonify(response), 200)


# Get new token
@application.route('/token')
@multi_auth.login_required
def get_auth_token():
	token = g.user.generate_auth_token(token_duration)
	g.user.last_token = token

	response = {
		'status': 'success',
		'id': g.user.id,
		'token': token.decode('ascii'),
		'token_duration': token_duration
	}
	return (jsonify(response), 200)


# Permissions
@application.route('/permissions/<string:action>', methods=['GET'])
@multi_auth.login_required
def get_permission(action):
	try:
		act = Action.query.filter_by(name=action).first()
		if(act is None):
			code = 400
			raise Exception("action does not exist")
		if(Permission.query.filter_by(role_id=g.user.role_id, action_id=act.id).first() is None):
			code = 403
			raise Exception("no permission")
	except Exception as e:
		response = {
			'status': 'error',
			'id': g.user.id,
			'username': g.user.username
		}
		return (jsonify(response), code)

	response = {
		'status': 'success',
		'id': g.user.id,
		'username': g.user.username
	}
	return (jsonify(response), 200)

# Get permissions (internal function)
def get_permission_internal(action):
	try:
		act = Action.query.filter_by(name=action).first()
		if(act is None):
			raise Exception("action does not exist")
		if(Permission.query.filter_by(role_id=g.user.role_id, action_id=act.id).first() is None):
			raise Exception("no permission")
	except Exception as e:
		return False

	return True


# Create organization
@application.route('/organizations', methods=['POST'])
@multi_auth.login_required
def create_organization():
	try:
		act = Action.query.filter_by(name="c_org").first()
		if(act is None):
			code = 400
			raise Exception("action does not exist")
		# check if superuser
		if(not get_permission_internal("c_org")):
			code = 403
			raise Exception("no permission")

		name = request.json.get('name')
		information = request.json.get('information')

		if(not name or not information):
			code = 400
			raise Exception("missing arguments")
		if(Organization.query.filter_by(name=name).first() is not None):
			code = 409
			raise Exception("existing user")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	org = Organization(name=name, information=information)
	db_accounts.session.add(org)
	db_accounts.session.commit()
	response = {
		'status': 'success',
		'id': org.id,
		'name': org.name
	}
	return (jsonify(response), 201)


# Create user
@application.route('/users', methods=['POST'])
@multi_auth.login_required
def create_user():
	try:
		# check if superuser or admin
		if(not get_permission_internal("c_usr")):
			code = 403
			raise Exception("no permission")

		username = request.json.get('username')
		email = request.json.get('email')
		password = request.json.get('password')
		role = request.json.get('role')
		org = g.user.org

		if(g.user.role_id == 1):
			org = request.json.get('org')
	
		if(not username or not email or not password or not org):
			code = 400
			raise Exception("missing arguments")
		if(User.query.filter_by(username=username).first() is not None):
			code = 409
			raise Exception("existing user")
		if(Organization.query.filter_by(id=org).first() is None):
			code = 400
			raise Exception("invalid organization")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	user = User(username=username, email=email, password=password, role_id=role, org_id=org)
	db_accounts.session.add(user)
	db_accounts.session.commit()
	response = {
		'status': 'success',
		'id': user.id,
		'username': user.username
	}
	return (jsonify(response), 201)


# Get organizations
@application.route('/organizations', methods=['GET'])
@multi_auth.login_required
def get_all_organizations():
	try:
		# check if superuser
		if(not get_permission_internal("r_orgs")):
			code = 403
			raise Exception("no permission")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	orgs = Organization.query.all()
	data = []
	for content in orgs:
		org_info = {
			'id': content.id,
			'name': content.name,
			'information': content.information,
			'date_registered': content.date_registered
		}
		data.append(org_info)

	response = {
		'status': 'success',
		'data': data
	}
	return (jsonify(response), 200)


# Get users
@application.route('/users', methods=['GET'])
@multi_auth.login_required
def get_all_users():
	try:
		# check if superuser
		if(not get_permission_internal("r_usrs")):
			code = 403
			raise Exception("no permission")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	users = User.query.all()
	data = []
	for content in users:
		usr_info = {
			'id': content.id,
			'username': content.username,
			'date_registered': content.date_registered
		}
		data.append(usr_info)

	response = {
		'status': 'success',
		'data': data
	}
	return (jsonify(response), 200)


# Get organization information
@application.route('/organizations/<int:id>', methods=['GET'])
@multi_auth.login_required
def get_organization(id):
	try:
		# check if superuser or admin
		if(not get_permission_internal("r_org")):
			code = 403
			raise Exception("no permission")
		
		org = Organization.query.get(id)
		if(not org):
			code = 404
			raise Exception("organization does not exist")

		rl = Role.query.filter_by(id=g.user.role_id).first()
		if(rl.name == "admin_org" and g.user.org != id):
			code = 403
			raise Exception("admin_org can not get information about another organization")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	response = {
		'status': 'success',
		'name': org.name,
		'information': org.information,
		'date_registered': org.date_registered
	}
	return (jsonify(response), 200)


# Get user information
@application.route('/users/<int:id>', methods=['GET'])
@multi_auth.login_required
def get_user(id):
	try:
		# check if superuser or admin
		if(not get_permission_internal("r_usr")):
			code = 403
			raise Exception("no permission")
	
		user = User.query.get(id)
		if(not user):
			code = 400
			raise Exception("user does not exist")

		rl = Role.query.filter_by(id=g.user.role_id).first()
		if(rl.name == "admin_org" and g.user.org != id):
			code = 403
			raise Exception("admin_org can not get information about user from another organization")
	except Exception as e:
		response = {
			'status': 'error'
		}
		return (jsonify(response), code)

	response = {
		'status': 'success',
		'username': user.username,
		'email': user.email,
		'date_registered': user.date_registered,
		'role_id': user.role_id,
		'org_id': user.org_id
	}
	return (jsonify(response), 200)



########################## Websockets Configuration ##########################
webSockets = []


@sockets.route('/updated')
def updated(ws):
	if not ws:
		raise RuntimeError("Environment lacks WSGI WebSocket support")

	webSockets.append(ws)

	while not ws.closed:
		gevent.sleep(DELAY)

	ws.send(str(random.randint(0,20)).encode('utf-8'))

	webSockets.remove(ws)

@application.route("/newValue", methods=["POST"])
def newData():
	
	logging.info("Receiving data...")
	result_json = request.get_json()

	if result_json == None or not set(["data"]).issubset(result_json):
		logging.error("Error on the request body: %s", request.data)
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	data = result_json["data"]

	for ws in webSockets:
		ws.send(data.encode('utf-8'))

	message = jsonify({"status": "OK"})
	message.status_code = 200
	return message

########################## Vertical Configuration ##########################

@application.route("/verticals", methods=["GET"])
@multi_auth.login_required
def list_verticals():
	"""
	List all verticals
	---
	tags:
		- verticals

	description: List all verticals
	
	responses:
		200:
			description: List of all verticals
			schema:
				id: vertical_list
				properties:
					values:
						type: array
						required: true
						description: array with all verticals
						items:
							type: String
							required : true
							description: vertical name
						example: ["temperature", "pressure"]
		500:
			description: Internal server error
	"""
	logging.info("Listing verticals...")

	try:
		verticals = db.list_all_verticals()
	except Exception as e:
		logging.error("Error listing verticals: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	message = jsonify({"values": verticals})
	message.status_code = 200
	logging.info("Listed all verticals successfully")
	
	return message

@application.route("/verticals", methods=["POST"])
@multi_auth.login_required
def insert_vertical():
	"""
	Insert vertical
	---
	tags:
		- verticals

	description: Insert new vertical
	
	parameters:
		- name: name
		  type: string
		  required : true
		  description: vertical name

	responses:
		201:
			description: Vertical inserted successfully
		400:
			description: Error on request body
		500:
			description: Internal server error
	
	"""

	logging.info("Inserting vertical...")
	result_json = request.get_json()

	if result_json == None or not set(["name"]).issubset(result_json):
		logging.error("Error on the request body: %s", request.data)
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	name = result_json["name"]
	logging.info("Vertical name: %s", name)

	try:
		db.insert_vertical(name)
	except Exception as e:
		logging.error("Error inserting vertical %s in db: %s.", name, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	message = jsonify({"status": "OK"})
	message.status_code = 201
	logging.info("Vertical %s inserted successfully", name)
	return message

@application.route("/verticals/<name>", methods=["DELETE"])
@multi_auth.login_required
def remove_vertical(name):
	"""
	Remove vertical
	---
	tags:
		- verticals

	description: Delete vertical vertical
	
	parameters:
		- name: name
		  type: string
		  required : true
		  description: vertical name

	responses:
		204:
			description: Vertical deleted successfully
		500:
			description: Internal server error
	
	"""

	logging.info("Removing vertical %s.", name)
	try:
		db.remove_vertical(name)
	except Exception as e:
		logging.error("Error removing vertical %s: %s.", name, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	message = jsonify({"status": "OK"})
	message.status_code = 204
	logging.info("Vertical removed successfully: %s", name)
	return message


########################### Device Configuration ###########################


@application.route("/device", methods=["POST"])
@multi_auth.login_required
def register_device():
	'''
		Register a device
	'''

	logging.info("Registering a device...")

	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]

	result_json = request.get_json()

	if result_json == None or not set(["name", "vertical"]).issubset(result_json):
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	name = result_json["name"]
	vertical = result_json["vertical"]

	location = None
	description = None
	
	if "location" in result_json:
		location = result_json["location"]

	if "description" in result_json:
		description = result_json["description"]

	verticals = []

	try:
		verticals = db.list_all_verticals()
	except Exception as e:
		logging.error("Error listing verticals: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	if vertical not in verticals:
		logging.error("Vertical %s not in verticals stored.", vertical)
		message = jsonify({"status": "Error", "Description": "Vertical not found"})
		message.status_code = 404
		return message

	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	message_content = {"name": name}

	if description:
		message_content["description"] = description

	try:
		data = json.dumps(message_content)
		r = requests.post(DATA_LAYER_URL+"/device", headers=headers, data=data)
	except requests.exceptions.RequestException as e:
		logging.error("Could not register device: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error
	
	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		logging.error("Error registering device: %s", r.text)
		error.status_code = 400
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error registering device: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error registering device: %s", r.text)
		return error
	elif r.status_code!=201:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error registering device: %s", r.text)
		return error

	content = r.json()
	if "id" not in content or "secret" not in content:
		logging.error("ID or secret not im message from Data Layer when registering device: %s.", content)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	device_id = content["id"]
	device_secret = content["secret"]

	try:
		db.insert_device(name, vertical, description, location, device_id, device_secret)
	except Exception as e:
		logging.error("Could not insert device: %s.", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		return error

	content = jsonify({'status': 'OK', 'device_id': device_id})
	content.status_code = 200
	logging.info("Device %s registered successfully with id %s.", name, device_id)
	return content

@application.route("/device", methods=["GET"])
@multi_auth.login_required
def list_devices():
	'''
		List all devices
	'''
	logging.info("Listing all devices...")
	
	devices = []
	try:
		devices = db.list_all_devices()
	except Exception as e:
		logging.error("Error listing all devices: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message


	device_list = []
	for content in devices:
		response = {"id": content[0], "name": content[1], "vertical": content[2], "description": content[3], "location": content[4], "secret": content[5]}
		device_list.append(response)

	logging.info("All devices listed successfully")
	message = jsonify({"values": device_list})
	message.status_code = 200
	return message




@application.route("/device/<device_id>", methods=["DELETE"])
@cross_origin()
@multi_auth.login_required
def remove_device(device_id):
	'''
		Remove a device
	'''
	logging.info("Removing all devices with ID %s...", device_id)
	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}
	
	try:
		r = requests.delete(DATA_LAYER_URL+"/device/"+device_id, headers=headers)
	except requests.exceptions.RequestException as e:
		logging.error("Could not delete device %s: %s", name, device_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error removing device: %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error removing device: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error removing device: %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error removing device: %s", r.text)
		return error
	elif r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error removing device: %s", r.text)
		return error

	try:
		db.delete_device(device_id)
	except Exception as e:
		logging.error("Error deleting devices with ID %s: %s.", device_id, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	logging.info("All devices with ID %s removed successfully.", device_id)
	message = jsonify({"Status": "OK"})
	message.status_code = 204
	return message

########################## Stream Configuration #############################

@application.route("/device/<device_id>/stream", methods=["POST"])
@cross_origin()
@multi_auth.login_required
def add_stream(device_id):
	'''
		Add a stream to a device
	'''
	logging.info("Registering a stream...")

	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]

	result_json = request.get_json()

	if result_json == None or not set(["name"]).issubset(result_json):
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	name = result_json["name"]

	description = None
	if "description" in result_json:
		description = result_json["description"]

	actuator = False
	if "actuator" in result_json and result_json["actuator"]=="true":
		actuator = True

	try:
		devices = db.get_id_all_devices()
	except Exception as e:
		logging.error("Error listing id of devices: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	if device_id not in devices:
		logging.error("Device %s not in devices stored.", device_id)
		message = jsonify({"status": "Error", "Description": "Device not found"})
		message.status_code = 404
		return message

	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	try:
		r = requests.put(DATA_LAYER_URL+"/device/"+device_id+"/streams/"+name, headers=headers)
	except requests.exceptions.RequestException as e:
		logging.error("Could not add stream %s to device %s: %s", name, device_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error registering stream: %s", r.text)
		return error
	elif r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error registering stream: %s", r.text)
		return error

	try:
		db.insert_stream(name, device_id, description, actuator)
	except Exception as e:
		logging.error("Could not insert stream %s into device %s: %s.", name, device_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		return error

	content = jsonify({"Status": "OK"})
	content.status_code = 204
	logging.info("Stream %s registered successfully to device %s.", name, device_id)
	return content


@application.route("/device/<device_id>/stream")
@cross_origin()
@multi_auth.login_required
def list_streams(device_id):
	'''
		List all streams of a device
	'''
	logging.info("Listing all streams...")
	try:
		devices = db.get_id_all_devices()
	except Exception as e:
		logging.error("Error listing id of devices: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	if device_id not in devices:
		logging.error("Device %s not in devices stored.", device_id)
		message = jsonify({"status": "Error", "Description": "Device not found"})
		message.status_code = 404
		return message

	try:
		streams = db.get_streams_of_device(device_id)
	except Exception as e:
		logging.error("Error listing streams of devices: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message


	stream_list = []
	for content in streams:
		response = {"name": content[0], "device_id": content[1], "description": content[2], "actuator": content[3]}
		stream_list.append(response)

	logging.info("All streams of device listed successfully")
	message = jsonify({"values": stream_list})
	message.status_code = 200
	return message

@application.route("/device/<device_id>/stream/<stream_name>", methods=["DELETE"])
@multi_auth.login_required
def remove_stream(device_id, stream_name):
	'''
		Delete a stream from a device
	'''
	logging.info("Removing the stream %s from device %s...", device_id, stream_name)

	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	try:
		r = requests.delete(DATA_LAYER_URL+"/device/"+device_id+"/streams/"+stream_name, headers=headers)
	except requests.exceptions.RequestException as e:
		logging.error("Could not delete stream %s of device %s: %s", name, device_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error registering stream: %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error registering stream: %s", r.text)
		return error
	elif r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error registering stream: %s", r.text)
		return error

	try:
		db.delete_stream(device_id, stream_name)
	except Exception as e:
		logging.error("Error deleting stream with name %s from device %s: %s.", stream_name, device_id, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	logging.info("The stream with name %s from device %s %s removed successfully.", stream_name, device_id)
	message = jsonify({"Status": "OK"})
	message.status_code = 204
	return message



@application.route("/device/<device_id>/stream/<stream_name>", methods=["POST"])
@cross_origin()
@multi_auth.login_required
def postStreamValue(device_id, stream_name):
	logging.info("Sending a value to the stream %s of the device %s...", stream_name, device_id)
	
	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	result_json = request.get_json()

	if result_json == None or not set(["value"]).issubset(result_json):
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	try:
		password = db.get_device_password_to_actuate(device_id, stream_name)
	except Exception as e:
		logging.error("Error getting device password from device %s with stream %s: %s.", device_id, stream_name, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	if len(password)<1:
		logging.info("Password not found to stream %s of device %s.", stream_name, device_id)
		message = jsonify({"status": "Not Found"})
		message.status_code = 400
		return message

	password = password[0]
	value = float(result_json["value"])

	if "timestamp" in result_json:
		timestamp = result_json["timestamp"]
	else:
		timestamp = (datetime.datetime.now(pytz.timezone(zone))+datetime.timedelta(hours=1)).isoformat()


	headers = {"Content-Type":"application/json", "DEVICE-ID": device_id, "DEVICE-SECRET": password}
	data = {"value": value, "timestamp": timestamp}

	try:
		r = requests.post(DATA_LAYER_URL+"/device/"+device_id+"/streams/"+stream_name+"/value", headers=headers, data=json.dumps(data))
	except requests.exceptions.RequestException as e:
		logging.error("Could not post value %s to stream %s of device %s: %s", value, stream_name, device_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error pushing value to stream: %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error pushing value to stream: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error pushing value to stream: %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error pushing value to stream: %s", r.text)
		return error
	elif r.status_code!=201:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error pushing value to stream: %s", r.text)
		return error

	message = jsonify({"Status": "OK"})
	message.status_code = 201
	return message



#################### Subscription Configuration #############################

@application.route("/subscriptions", methods=["POST"])
@multi_auth.login_required
def subscribe_data_stream():
	
	logging.info("Subscribing data stream...")

	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	result_json = request.get_json()

	if result_json == None or not set(["name", "subscriber_id", "device_id", "device_secret", "stream_name"]).issubset(result_json):
		logging.error("Error on the request body: %s", request.data)
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	name = result_json["name"]
	subscriber_id = result_json["subscriber_id"]
	device_id = result_json["device_id"]
	device_secret = result_json["device_secret"]
	stream_name = result_json["stream_name"]

	description = None
	state = "active"
	method = "push"

	if "description" in result_json:
		description = result_json["description"]

	if "state" in result_json:
		if result_json["state"]=="active" or result_json["state"]=="suspended":
			state = result_json["state"]

	if "method" in result_json and (result_json["method"]=="push" or result_json["method"]=="pull"):
		method = result_json["method"]


	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	message_content = {"name": name, "subscriber_id": subscriber_id, "device_id": device_id, "device_secret": device_secret, "stream_name": stream_name}

	if description:
		message_content["description"] = description

	if state:
		message_content["state"] = state

	if method:
		message_content["method"] = method

	try:
		data = json.dumps(message_content)
		r = requests.post(DATA_LAYER_URL+"/subscriptions", headers=headers, data=data)
	except requests.exceptions.RequestException as e:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error subscribing stream %s from device %s to device %s: %s", stream_name, device_id, subscriber_id, e)
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error subscribing data stream: %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error subscribing data stream: %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error subscribing data stream: %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error subscribing data stream: %s", r.text)
		return error
	elif r.status_code!=201:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error subscribing data stream: %s", r.text)
		return error

	content = r.json()
	if "subscription_id" not in content:
		logging.error("ID of subscription not im message from Data Layer when registering device: %s.", content)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	subscription_id = content["subscription_id"]
	try:
		db.subscribe_stream(subscription_id, name, subscriber_id, device_id, device_secret, stream_name, description, state, method)
	except Exception as e:
		logging.error("Could not subscribe stream: %s.", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		return error

	content = jsonify({'status': 'OK', 'subscription_id': subscription_id})
	content.status_code = 200
	logging.info("Subscription successfully created to stream %s from device %s to device %s with id %s.", stream_name, device_id, subscriber_id, subscription_id)
	return content


@application.route("/subscriptions", methods=["GET"])
@multi_auth.login_required
def get_subscriptions():
	logging.info("Listing all subscriptions...")
	
	devices = []
	try:
		subscriptions = db.list_all_subscriptions()
	except Exception as e:
		logging.error("Error listing all subscriptions: %s.", e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message


	subscription_list = []
	for content in subscriptions:
		response = {"id": content[0], "name": content[1], "subscriber_id": content[2], "device_id": content[3], "device_secret": content[4], "stream_name": content[5], "description": content[6], "state": content[7], "method": content[8]}
		subscription_list.append(response)

	logging.info("All subscriptions listed successfully.")
	message = jsonify({"values": subscription_list})
	message.status_code = 200
	return message


@application.route("/subscriptions/<subscription_id>", methods=["DELETE"])
@multi_auth.login_required
def delete_subscription(subscription_id):
	logging.info("Removing the subscription with ID %s", subscription_id)
	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}
	
	try:
		r = requests.delete(DATA_LAYER_URL+"/subscriptions/"+subscription_id, headers=headers)
	except requests.exceptions.RequestException as e:
		logging.error("Could not delete subscription %s: %s", subscription_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error removing subscription %s: %s", subscription_id, r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error removing subscription %s: %s", subscription_id, r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error removing subscription %s: %s", subscription_id, r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error removing subscription %s: %s", subscription_id, r.text)
		return error
	elif r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error removing subscription %s: %s", subscription_id, r.text)
		return error

	try:
		db.delete_subscription(subscription_id)
	except Exception as e:
		logging.error("Error deleting subscription %s: %s.", subscription_id, e)
		message = jsonify({"status": "Error"})
		message.status_code = 500
		return message

	logging.info("Subscription with ID %s removed successfully.", subscription_id, )
	message = jsonify({"Status": "OK"})
	message.status_code = 204
	return message

@application.route("/subscriptions/<subscription_id>/values", methods=["GET"])
@multi_auth.login_required
def subscription_values(subscription_id):
	logging.info("Getting values from subscription")
	try:
		r = requests.get(LONG_TERM_PERSISTENCE_URL+"/values/"+subscription_id)
	except requests.exceptions.RequestException as e:
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		return error
	elif r.status_code!=200:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not get values from subscription %s: %s", subscription_id, e)
		return error

	logging.info("Values from subscription with ID %s fetched successfully.", subscription_id)
	message = jsonify(r.json())
	message.status_code = 200
	return message


@application.route("/alerts")
@multi_auth.login_required
def get_all_alerts():
	logging.info("Fetching all alerts...")

	try:
		r = requests.get(ALERTS_MODULE_URL+"/alerts")
	except requests.exceptions.RequestException as e:
		logging.error("Could not fetch alerts: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=200:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not fetch alerts")
		return error

	logging.info("Alerts fetched successfully.")
	message = jsonify(r.json())
	message.status_code = 200
	return message

@application.route("/alerts", methods=["POST"])
@cross_origin()
@multi_auth.login_required
def add_alerts():
	logging.info("Adding alert...")
	
	result_json = request.get_json()
	if result_json == None or not set(["subscription_id", "alarm_type", "threshold"]).issubset(result_json):
		logging.error("Error on the request body: %s", request.data)
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	subscription_id = result_json["subscription_id"]
	alarm_type = result_json["alarm_type"]
	threshold = result_json["threshold"]


	message_content = {"subscriptionId": subscription_id, "threshold": threshold, "alarm_type": alarm_type}
	try:
		data = json.dumps(message_content)
		r = requests.post(ALERTS_MODULE_URL+"/alerts", data=data)
	except requests.exceptions.RequestException as e:
		logging.error("Could not add alert: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=201:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not add alert")
		return error

	logging.info("Alert successfully added.")
	message = jsonify({"Status": "OK"})
	message.status_code = 201
	return message

@application.route("/alert/<alert_id>", methods=["DELETE"])
@multi_auth.login_required
def delete_alert(alert_id):
	logging.info("Deleting alert...")
	
	try:
		r = requests.delete(ALERTS_MODULE_URL+"/alert/"+alert_id)
	except requests.exceptions.RequestException as e:
		logging.error("Could not delete alert: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not delete alert")
		return error

	logging.info("Alert successfully deleted.")
	message = jsonify({"Status": "OK"})
	message.status_code = 201
	return message


@application.route("/triggered")
@multi_auth.login_required
def get_triggered_alerts():
	logging.info("Fetching all triggered alerts...")

	try:
		r = requests.get(ALERTS_MODULE_URL+"/triggered")
	except requests.exceptions.RequestException as e:
		logging.error("Could not fetch triggered alerts: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=200:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not fetch triggered alerts: %s", e)
		return error

	logging.info("Triggered alerts fetched successfully.")
	message = jsonify(r.json())
	message.status_code = 200
	return message

@application.route("/triggered/<triggered_alert_id>/dismiss", methods=["PUT"])
@cross_origin()
@multi_auth.login_required
def dismiss_triggered_alert(triggered_alert_id):
	logging.info("Dismissing triggered alert...")

	try:
		r = requests.put(ALERTS_MODULE_URL+"/triggered/"+triggered_alert_id+"/dismiss")
	except requests.exceptions.RequestException as e:
		logging.error("Could not dismiss triggered alert %s: %s", triggered_alert_id, e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not dismiss triggered alert %s", triggered_alert_id)
		return error

	logging.info("Triggered alert dismissed successfully")
	message = jsonify({"Status": "OK"})
	message.status_code = 204
	return message

@application.route("/alert/<alert_id>/actuator", methods=["POST"])
@multi_auth.login_required
def add_actuator(alert_id):
	logging.info("Adding actuator to the alert...")

	if "ACCOUNT-ID" not in request.headers or "ACCOUNT-SECRET" not in request.headers:
		error = jsonify({'status': 'Error', 'description': "Could not get the ID and secret of account"})
		error.status_code = 400
		logging.error("Account-ID and Account-secret not found on headers.")
		return error

	account_id = request.headers["ACCOUNT-ID"]
	account_secret = request.headers["ACCOUNT-SECRET"]
	headers = {"Content-Type":"application/json", "ACCOUNT-ID": account_id, "ACCOUNT-SECRET": account_secret}

	result_json = request.get_json()
	if result_json == None or not set(["value", "deviceId", "streamName"]).issubset(result_json):
		logging.error("Error on the request body: %s", request.data)
		error = jsonify({'status': 'Error', 'description': "The request does not have all the required fields"})
		error.status_code = 400
		return error

	value = result_json["value"]
	device_id = result_json["deviceId"]
	stream_name = result_json["streamName"]
	data = {"alertId": alert_id, "value": value, "deviceId": device_id, "streamName": stream_name}

	try:
		r = requests.post(ALERTS_MODULE_URL+"/actuator", headers=headers, data=json.dumps(data))
	except requests.exceptions.RequestException as e:
		logging.error("Could not add actuator to alert: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code==400:
		error = jsonify({'status': 'Error'})
		error.status_code = 400
		logging.error("Error adding actuator %s", r.text)
		return error
	if r.status_code==401:
		error = jsonify({'status': 'Error'})
		error.status_code = 401
		logging.error("Error adding actuator %s", r.text)
		return error
	if r.status_code==403:
		error = jsonify({'status': 'Error'})
		error.status_code = 403
		logging.error("Error adding actuator %s", r.text)
		return error
	if r.status_code==404:
		error = jsonify({'status': 'Error'})
		error.status_code = 404
		logging.error("Error adding actuator %s", r.text)
		return error
	elif r.status_code!=201:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Error adding actuator %s", r.text)
		return error

	logging.info("Actuator added successfully")
	message = jsonify({"Status": "OK"})
	message.status_code = 201
	return message

@application.route("/alert/<alert_id>/<actuator_id>", methods=["DELETE"])
@multi_auth.login_required
def delete_actuator(alert_id, actuator_id):
	logging.info("Deleting actuator...")
	
	try:
		r = requests.delete(ALERTS_MODULE_URL+"/actuator/"+actuator_id)
	except requests.exceptions.RequestException as e:
		logging.error("Could not delete actuator: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=204:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not delete actuator")
		return error

	logging.info("Actuator successfully deleted.")
	message = jsonify({"Status": "OK"})
	message.status_code = 204
	return message

@application.route("/alert/<alert_id>/actuators")
@multi_auth.login_required
def get_actuator_by_id(alert_id):
	logging.info("Listing all actuators from alert %s", alert_id)

	try:
		r = requests.get(ALERTS_MODULE_URL+"/alert/"+alert_id+"/actuators")
	except requests.exceptions.RequestException as e:
		logging.error("Could not fetch actuators: %s", e)
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		return error

	if r.status_code!=200:
		error = jsonify({'status': 'Error'})
		error.status_code = 500
		logging.error("Could not fetch actuator")
		return error

	logging.info("Successfully fetched all actuators by id")
	content = r.json()
	message = jsonify(content)
	message.status_code = 200
	return message

from subprocess import *
from aux_functions import *
from ruamel.yaml import YAML
import time, sys, logging, falcon, json, os

class Organization(object):
	'''
		Get organization information
		URL params: Gateway type, Organization id
	'''
	def on_get(self, req, resp, gw_type, org_id):
		logging.info("Returning Organization " + org_id + " information.")
		# Open yml file
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if organization exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		resp.status = falcon.HTTP_200
		resp.body = json.dumps({"status": "success", "info": {org_id: configurations[gw_type][org_id]}})

	'''
		Update organization
		Provide either api_url or period or both
		URL params: Gateway type, Organization id
		Body Params: api_url, period
		{
			"api_url": "abc.com",
			"period": 15
		}
	'''
	def on_put(self, req, resp, gw_type, org_id):
		logging.info("Updating Organization " + org_id)

		# Parse received data
		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error("Data received not in the right format: %s", bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Data received not in the right format"})
			return

		if "period" not in parsed_data and "api_url" not in parsed_data:
			logging.error("Request missing parameters")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Request has missing parameters"})
			return

		# Open yml file
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error('Could not parse the configuraiton file')
			sys.exit(1)

		# Check if org exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		# Update configuration file
		if "period" in parsed_data:
			try:
				period = int(parsed_data["period"])
				configurations[gw_type][org_id]["period"] = period
			except:
				resp.status = falcon.HTTP_400
				resp.body = json.dumps({"status": "error", "message": "Period is not an integer"})
				return

		if "api_url" in parsed_data:
			configurations[gw_type][org_id]["api"] = parsed_data["api_url"]

		try:
			# Store on config file
			with open("gateway_config.yml", 'w') as f:
				yaml=YAML(typ='safe')
				yaml.dump(configurations, f)
		except:
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Could not update organization " + org_id})
			logging.error("Could not update Organization " + org_id)
			return

		# Restart gateway if organization has one running
		if org_id in GatewayProcessManager.processes[gw_type].keys():
			logging.info("Restarting gateway " + gw_type + " for organization " + org_id)
			GatewayProcessManager.stop_gateway(gw_type, org_id)
			#time.sleep(1)
			GatewayProcessManager.start_gateway(gw_type, org_id)

		logging.info("Updated organization " + org_id + " info on " + gw_type)
		resp.status = falcon.HTTP_204

	def on_delete(self, req, resp, gw_type, org_id):
		logging.info("Deleting Organization " + org_id)

		# Open yml file
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if org exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		# Stop gateway instance if this org has one running
		if org_id in GatewayProcessManager.processes[gw_type].keys():
			logging.info("Stopping "+ gw_type +" gateway for " + org_id)
			GatewayProcessManager.stop_gateway(gw_type, org_id)

		# Delete from configuration file
		try:
			info_removed = configurations[gw_type].pop(org_id)
			
			# Store on config file
			with open("gateway_config.yml", 'w') as f:
				yaml=YAML(typ='safe')
				yaml.dump(configurations, f)

		except:
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Could not remove Organization " + org_id})
			logging.error("Could not remove Organization " + org_id)
			return

		logging.info("Removed organization " + org_id + " from " + gw_type)
		resp.status = falcon.HTTP_204

class RegisterOrganization(object):
	''' 
		Register new organization
		Body Params: gateway_type, organization_id,  period, api_url
		{
			"gateway_type": "360waste",
			"api_url": "abc.com",
			"period": 15,
			"organization_id": "CM Aveiro"
		}
	'''
	def on_post(self, req, resp):
		logging.info("Registering new organization")

		# Parse received data
		logging.info("Parsing the received data")
		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error("Data received not in the right format: %s", bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Data received not in the right format"})
			return

		if "gateway_type" not in parsed_data or "organization_id" not in parsed_data or "period" not in parsed_data or "api_url" not in parsed_data:
			logging.error("Request missing parameters")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Request has missing parameters"})
			return

		gateway_type = parsed_data["gateway_type"]
		organization_id = parsed_data["organization_id"]

		logging.info("Checking for valid period value")
		try:
			period = int(parsed_data["period"])
		except:
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Period is not an integer"})
			return
		api_url = parsed_data["api_url"]

		# Check if valid gateway type
		if gateway_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Open yml file and store info
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if any organization exists
		try:
			configurations[gateway_type].keys()
		except:
			logging.info('No organizations exist for this gateway type')
			configurations[gateway_type] = {}

		# Check if org already exists
		logging.info("Checking if organization already exists")
		if organization_id in configurations[gateway_type].keys():
			resp.status = falcon.HTTP_409
			resp.body = json.dumps({"status": "error", "message": "Organization already exists"})
			return

		# If does not exist, register id
		configurations[gateway_type][organization_id] = {'api': api_url, 'period': period}

		# Store on config file
		try:
			with open("gateway_config.yml", 'w') as f:
				yaml=YAML(typ='safe')
				yaml.dump(configurations, f)
		except Exception as e:
			logging.error("Could not store in the configuraiton file")
			sys.exit(1)

		logging.info("Organization successfully registered.")
		resp.status = falcon.HTTP_201
		resp.body = json.dumps({"status": "success", "message": "Organization successfully registered"})

class RegisterDevice(object):
	'''
		Add devices to an existing organization
		URL params: Gateway type, Organization id
		Body params: devices
		360Waste example
		{
			"devices":
			[
				{
					"device_id": "1a2",
					"pw": "aaaaa",
					"api_id": "12",
					"wasteperc_stream": "wasteperc_stream",
					"intemp_stream": "intemp_stream"
				},
				{
					"device_id": "1a23",
					"pw": "bbbbb",
					"api_id": "123",
					"wasteperc_stream": "wasteperc_stream",
					"intemp_stream": "intemp_stream"
				}
			]
		}
	'''
	def on_post(self, req, resp, gw_type, org_id):
		logging.info("Registering new devices for specific organization")

		# Parse received data
		try:
			parsed_data = json.loads(bytes_to_string(req.stream.read()))
		except Exception as e:
			logging.error("Data received not in the right format: %s", bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Data received not in the right format"})
			return

		if "devices" not in parsed_data:
			logging.error("Data received not in the right format: %s", bytes_to_string(req.stream.read()))
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Request has missing parameters"})
			return

		devices = parsed_data["devices"]

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Open yml file and store info
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if org exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		# Store new device information given the gateway type chosen
		if gw_type == '360waste':
			# Update config file
			dev = []
			try:
				for device in devices:
					dev.append({'api_id': int(device['api_id']), 'pw': device['pw'], "device_id": device["device_id"], "wasteperc_stream": device["wasteperc_stream"], "intemp_stream": device["intemp_stream"]})
			except:
				resp.status = falcon.HTTP_400
				resp.body = json.dumps({"status": "error", "message": "Device's information missing or not in the right format"})
				logging.error("Device's information missing or not in the right format")
				return
		#elif gw_type == ...

		# Check if org already has devices
		update = False
		if 'devices' in configurations[gw_type][org_id].keys():
			logging.info("Organization already has devices, updating devices")
			update = True
			current_dev = list(configurations[gw_type][org_id]['devices'].values())
			dev = current_dev+dev

		dev = {v+1: k for v, k in enumerate(dev)}

		configurations[gw_type][org_id]["devices"] = dev

		# Store on config file
		try:
			with open("gateway_config.yml", 'w') as f:
				yaml=YAML(typ='safe')
				yaml.dump(configurations, f)
		except Exception as e:
			logging.error("Could not store in the configuraiton file")
			sys.exit(1)

		# Start gateway instance for organization
		# If already had devices restart else start a new one
		if update:
			logging.info("Restarting gateway for Organization " + org_id)
			GatewayProcessManager.stop_gateway(gw_type, org_id)
			#time.sleep(1)
			GatewayProcessManager.start_gateway(gw_type, org_id)
		else:
			logging.info("Starting gateway for Organization " + org_id)
			GatewayProcessManager.start_gateway(gw_type, org_id)

		logging.info("Devices successfully registered")
		resp.status = falcon.HTTP_201
		resp.body = json.dumps({"status": "success", "message": "Devices successfully registered for " + org_id})

class Device(object):
	'''
		Get device information
		URL params: Gateway type, Organization id, Device id
	'''
	def on_get(self, req, resp, gw_type, org_id, dev_id):
		logging.info("Returning device " + dev_id + " information.")
		# Open yml file
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if org exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		# Check if organization has devices
		if 'devices' not in configurations[gw_type][org_id].keys():
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Organization does not have any devices"})
			return

		# Check if device exists
		if int(dev_id) not in configurations[gw_type][org_id]["devices"].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization "+ org_id + " does not have device " + dev_id})
			return

		resp.status = falcon.HTTP_200
		resp.body = json.dumps({"status": "success", "info": {dev_id: configurations[gw_type][org_id]["devices"][int(dev_id)]}})

	'''
		Remove device
		URL params: Gateway type, Organization id, Device id
	'''
	def on_delete(self, req, resp, gw_type, org_id, dev_id):
		logging.info("Deleting device " + dev_id)

		# Open yml file
		# Open configuration file
		try:
			with open("gateway_config.yml") as f:
				config_file = f.read()
		except Exception as e:
			logging.error("Could not read the configuration file %s", config_file)
			sys.exit(1)

		# Check if valid gateway type
		if gw_type not in GatewayProcessManager.gw_types:
			logging.error("Invalid gateway type")
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Invalid gateway type"})
			return

		# Parse config file
		try:
			yaml=YAML(typ='safe')
			configurations = yaml.load(config_file)
		except Exception as e:
			logging.error("Could not parse the configuraiton file")
			sys.exit(1)

		# Check if org exists
		if configurations[gw_type] is None:
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		if org_id not in configurations[gw_type].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization " + org_id + " does not exist"})
			return

		# Check if organization has devices
		if 'devices' not in configurations[gw_type][org_id].keys():
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Organization does not have any devices to delete"})
			return

		# Check if device exists
		if int(dev_id) not in configurations[gw_type][org_id]["devices"].keys():
			resp.status = falcon.HTTP_404
			resp.body = json.dumps({"status": "error", "message": "Organization "+ org_id + " does not have device " + dev_id})
			return

		# Delete from configuration file
		try:
			info_removed = configurations[gw_type][org_id]["devices"].pop(int(dev_id))

			# Check for zero devices
			# If no more devices remove device entry
			if not configurations[gw_type][org_id]["devices"].keys():
				configurations[gw_type][org_id].pop("devices")

			# Store on config file
			with open("gateway_config.yml", 'w') as f:
				yaml=YAML(typ='safe')
				yaml.dump(configurations, f)
		except:
			resp.status = falcon.HTTP_400
			resp.body = json.dumps({"status": "error", "message": "Could not remove device " + dev_id})
			logging.error("Could not remove device " + dev_id)
			return

		# Restart gateway (or stop if no devices)
		# Check if organization has devices
		if 'devices' not in configurations[gw_type][org_id].keys():
			logging.info("Stopping gateway " + gw_type + " from " + org_id)
			GatewayProcessManager.stop_gateway(gw_type, org_id)
		else:
			logging.info("Restarting gateway " + gw_type + " from " + org_id)
			GatewayProcessManager.stop_gateway(gw_type, org_id)
			#time.sleep(1)
			GatewayProcessManager.start_gateway(gw_type, org_id)

		logging.info("Removed device " + dev_id + " from " + org_id)
		resp.status = falcon.HTTP_204

'''
	Static class used to manage the gateways

	Known issue: If user provides wrong api url, the gateway for the
	organization will become a zombie process.
'''
class GatewayProcessManager(object):
	# CONFIGURE NEW GATEWAY HERE
	gw_types = ['360waste']
	processes = dict()

	@staticmethod
	def initialize():
		for gwtype in GatewayProcessManager.gw_types:
			GatewayProcessManager.processes[gwtype] = {}

	@staticmethod
	def start_gateway(gw_type, org):
		log = open(org+'_'+gw_type+'.txt', 'a')
		log.write(org+' log file for '+gw_type+'\n')
		log.flush()
		if gw_type == '360waste':
			child_pid = Popen(['python3', 'gw360.py', org], stdout=log, stderr=log)
		#elif gw_type == ...

		# Store child pid
		GatewayProcessManager.processes[gw_type][org] = child_pid

	@staticmethod
	def stop_gateway(gw_type, org):
		pid = GatewayProcessManager.processes[gw_type].pop(org)
		pid.kill()
		pid.wait()

# Configure logger
logging.getLogger().setLevel(logging.INFO)

# Create API and endpoints
app = falcon.API()
registerOrg = RegisterOrganization()
org = Organization()
registerDev = RegisterDevice()
dev = Device()

app.add_route('/organization', registerOrg)
app.add_route('/organization/{gw_type}/{org_id}', org)
app.add_route('/device/{gw_type}/{org_id}', registerDev)
app.add_route('/device/{gw_type}/{org_id}/{dev_id}', dev)

# Start processes for registered organizations
logging.info("Starting processes for registered organizations")

# Open configuration file
try:
	with open("gateway_config.yml") as f:
		config_file = f.read()
except Exception as e:
	logging.error("Could not read the configuration file")
	sys.exit(1)

# Parse config file
try:
	yaml=YAML(typ='safe')
	configurations = yaml.load(config_file)
except Exception as e:
	logging.error("Could not parse the configuraiton file")
	sys.exit(1)

# Start gateways for all gateway types
GatewayProcessManager.initialize()

try:
	for gwtype in configurations.keys():
		# Start gateways for each gateway type
		for org in configurations[gwtype].keys():
			GatewayProcessManager.start_gateway(gwtype, org)
except:
	logging.info("No organizations yet registered")
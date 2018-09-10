from ruamel.yaml import YAML
import time, json, requests, logging, datetime, pytz, sys
from smartIoT_Interface import *

zone = 'Europe/Lisbon'

# Configure logger
logging.getLogger().setLevel(logging.INFO)

# Open configuration file
try:
	with open("gateway_config.yml") as f:
		config_file = f.read()
except Exception as e:
	logging.error('Could not read the configuration file')
	sys.exit(1)

# Parse config file
try:
	yaml=YAML(typ='safe')
	configurations = yaml.load(config_file)
except Exception as e:
	logging.error('Could not parse the configuraiton file')
	sys.exit(1)

# Console parameter
if len(sys.argv) != 2:
	logging.error('No organization provided')
	sys.exit(1)

org = sys.argv[1]
info = configurations["360waste"][org]

devices = {}

# Get API URL
try:
	URL = info["api"]
except KeyError as e:
	logging.error('Configuration file does not have the api url')
	sys.exit(1)

# Get period
try:
	PERIOD = info["period"]
except KeyError as e:
	logging.error('Configuration file does not have the period')
	sys.exit(1)

# Read devices information
try:
	for dev in info["devices"]:
		devices[dev] = info["devices"][dev]
except KeyError as e:
	logging.error('Configuration file does not have the devices information')
	sys.exit(1)

# Read 
while(True):
	try:
		logging.info('Getting api information')
		response = requests.get(URL)
		raw_data = json.loads(response.text)
		api_sensors = raw_data['Sensors'] 
	except:
		logging.error('Could not retrieve sensors data from API')
		sys.exit(1)

	# For each device of the org get corresponding data from API
	for device in devices.values():
		try:
			for sensor in api_sensors:
				if sensor["idcontainer_sensor"] == device['api_id']:
					break
				else:
					sensor = None
		except:
			logging.error('Could not get data from API')
			continue

		if sensor is None:
			logging.error('Could not find device with api id '+str(device['api_id'])+' in API')
			continue

		# Read and compute values streams
		maxVolume = sensor['maxVolume']
		fullness = int(float(sensor['volume'])/maxVolume*100)
		temperature = sensor['temperature']

		# Publish into Smart IoT
		# Auth device
		# device_authentication not returning tuple correcly
		try:
			logging.info('Authenticating device '+device['device_id'])
			dev_auth = device_authentication("https://iot.alticelabs.com/api", device['device_id'], device['pw'])[1]
			#if dev_auth[0] != 201:
			#	raise Exception
		except:
			logging.warning('Could not authenticate device '+device['device_id'])

		# Percentage
		try:
			logging.info('Publishing percentage data for device '+device['device_id'])
			pub = publish_into_stream("https://iot.alticelabs.com/api", dev_auth, device['device_id'], device['wasteperc_stream'], datetime.datetime.now(pytz.timezone(zone)).isoformat(), fullness, 300)
			if pub[0] == 202:
				logging.info('Published percentage value '+str(fullness)+' into stream for device '+device['device_id'])
			else:
				raise Exception
		except:
			logging.error('Error publishing data into Percentage stream for device '+device['device_id'])
		
		# Temperature
		try:
			logging.info('Publishing temperature data for device '+device['device_id'])
			pub = publish_into_stream("https://iot.alticelabs.com/api", dev_auth, device['device_id'], device['intemp_stream'], datetime.datetime.now(pytz.timezone(zone)).isoformat(), temperature, 300)
			if pub[0] == 202:
				logging.info('Published temperature value '+str(temperature)+' into stream for device '+device['device_id'])
			else:
				raise Exception
		except:
			logging.error('Error publishing data into Temperature stream for device '+device['device_id'])

	logging.info('Sleeping for '+str(PERIOD)+' seconds')
	time.sleep(PERIOD)
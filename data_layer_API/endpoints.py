import falcon
from device_management import *
from stream_management import *
from subscription_management import *

config_file = "configurations.yml"

try:
	with open(config_file) as f:
		configuration_file = f.read()
except Exception as e:
	logging.warning('Could not read the configuration file %s', config_file)
	sys.exit(1)

try:
	yaml=YAML(typ='safe')
	configurations = yaml.load(configuration_file)
except Exception as e:
	logging.warning('Could not parse the configuraiton file')
	sys.exit(1)

try:
	prefix_point_of_contact = configurations["prefix_point_of_contact"]
except KeyError as e:
	logging.warning('Configuration file does not have the prefix point of contact')
	sys.exit(1)

try:
	postfix_point_of_contact = configurations["postfix_point_of_contact"]
except KeyError as e:
	logging.warning('Configuration file does not have the postfix point of contact')
	sys.exit(1)


app = falcon.API()

registerDevice = RegisterDevice()
device = Device()

createDeleteStream = CreateDeleteStream()
publishValue = PublishIntoStream()
listStreams = ListStreams()

subscribeStream = SubscribeStream()
subscriptionManagement = SubscriptionManagement()
getSubscriptionValues = SubscriptionValues()

pointOfContact = PointOfContact()

app.add_route('/device', registerDevice)
app.add_route('/device/{device_id}', device)
app.add_route('/device/{device_id}/streams', listStreams)
app.add_route('/device/{device_id}/streams/{stream_name}', createDeleteStream)
app.add_route('/device/{device_id}/streams/{stream_name}/value', publishValue)
app.add_route('/subscriptions', subscribeStream)
app.add_route('/subscriptions/{subscription_id}', subscriptionManagement)
app.add_route('/subscriptions/{subscription_id}/values', getSubscriptionValues)
app.add_route(prefix_point_of_contact+"/{subscription_id}"+postfix_point_of_contact, pointOfContact)

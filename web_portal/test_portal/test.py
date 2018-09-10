
from flask import Flask, render_template

application = Flask(__name__)
application.config['DEBUG'] = True


@application.route("/")
def main():
    return render_template("index.html")

@application.route("/login")
def login():
    return render_template("login.html")

@application.route("/verticals")
def verticals():
    return render_template("verticals.html")

@application.route("/devices")
def devices():
    return render_template("devices.html")

@application.route("/device/<device_id>/streams")
def streams(device_id):
    return render_template("streams.html", device_id=device_id)

@application.route("/subscriptions")
def subscriptions():
    return render_template("subscriptions.html")

@application.route("/subscription/<subscription_id>")
def subscription(subscription_id):
    return render_template("subscription.html", subscription_id=subscription_id)

@application.route("/alerts")
def alerts():
    return render_template("alerts.html")

@application.route("/triggered")
def triggered():
    return render_template("triggered.html")

@application.route("/alert/<alert_id>/actuators")
def actuators(alert_id):
    return render_template("actuators.html", alert_id=alert_id)

CREATE USER "alertManager";

CREATE DATABASE alerts;

\c alerts

alter user "alertManager" with encrypted password 'alertManager';

GRANT ALL PRIVILEGES ON DATABASE alerts to "alertManager";

CREATE TABLE alerts_table(
	id SERIAL primary key,
	subscription_id varchar(50) NOT NULL,
	threshold real NOT NULL,
	alarm_type varchar(50) NOT NULL
);

CREATE TABLE triggered_alerts(
	id SERIAL primary key,
	dismiss boolean NOT NULL default false,
	alert_id int NOT NULL REFERENCES ALERTS_TABLE(id) ON DELETE CASCADE,
	trigger_time timestamp NOT NULL
);

CREATE TABLE actuators(
	id SERIAL primary key,
	alert_id int NOT NULL REFERENCES ALERTS_TABLE(id) ON DELETE CASCADE,
	account_id varchar(80) NOT NULL,
	account_secret varchar(80) NOT NULL,
	value varchar(50) NOT NULL,
	device_id varchar(50) NOT NULL,
	stream_name varchar(80) NOT NULL
);


GRANT ALL PRIVILEGES ON TABLE alerts_table TO "alertManager";
GRANT USAGE, SELECT ON SEQUENCE alerts_table_id_seq TO "alertManager";

GRANT ALL PRIVILEGES ON TABLE triggered_alerts TO "alertManager";
GRANT USAGE, SELECT ON SEQUENCE triggered_alerts_id_seq TO "alertManager";

GRANT ALL PRIVILEGES ON TABLE actuators TO "alertManager";
GRANT USAGE, SELECT ON SEQUENCE actuators_id_seq TO "alertManager";


GRANT ALL ON SCHEMA public TO "alertManager";

CREATE OR REPLACE FUNCTION insert_alert(arg_subscription_id varchar(50), arg_threshold real, arg_alarm_type varchar(50)) RETURNS VOID AS
$$
BEGIN
	INSERT INTO alerts_table (subscription_id, threshold, alarm_type) VALUES (arg_subscription_id, arg_threshold, arg_alarm_type);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_all_alerts() 
RETURNS TABLE (arg_id int, arg_subscription_id varchar(50), arg_threshold real, arg_alarm_type varchar(50)) AS
$$
BEGIN
	RETURN QUERY SELECT id, subscription_id, threshold, alarm_type FROM alerts_table;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_alert_by_id(arg_id int)
RETURNS TABLE (arg_subscription_id varchar(50), arg_threshold real, arg_alarm_type varchar(50)) AS
$$
BEGIN
	RETURN QUERY SELECT subscription_id, threshold, alarm_type FROM alerts_table WHERE id=arg_id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_subscription_alerts(arg_subscription_id varchar(50))
RETURNS TABLE (arg_id int, arg_threshold real, arg_alarm_type varchar(50)) AS
$$
BEGIN
	RETURN QUERY SELECT id, threshold, alarm_type FROM alerts_table WHERE subscription_id=arg_subscription_id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_alert(arg_id integer, arg_threshold real, arg_alarm_type varchar(50)) RETURNS VOID AS
$$
BEGIN
	UPDATE alerts_table SET threshold=arg_threshold AND alarm_type=arg_alarm_type WHERE id=arg_id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_alert(arg_id int) RETURNS VOID AS
$$
BEGIN
	DELETE FROM alerts_table WHERE arg_id=id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_triggered_alert(arg_alertId int) RETURNS VOID AS
$$
BEGIN
	INSERT INTO triggered_alerts (alert_id, trigger_time) VALUES (arg_alertId, CURRENT_TIMESTAMP);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_all_triggered_alerts_not_dismissed() 
RETURNS TABLE (arg_id int, arg_alert_id int, arg_trigger_time timestamp) AS
$$
BEGIN
	RETURN QUERY SELECT id, alert_id, trigger_time FROM triggered_alerts where dismiss=False;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION dismiss_triggered_alert(arg_id integer) 
RETURNS VOID AS
$$
BEGIN
	UPDATE triggered_alerts SET dismiss=True WHERE id=arg_id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_actuator(arg_alert_id int, arg_account_id varchar(80), arg_account_secret varchar(80), arg_value varchar(50), arg_device_id varchar(50), arg_stream_name varchar(80))
RETURNS VOID AS
$$
BEGIN
	INSERT INTO actuators (alert_id, account_id, account_secret, value, device_id, stream_name) VALUES (arg_alert_id, arg_account_id, arg_account_secret, arg_value, arg_device_id, arg_stream_name);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION delete_actuator(arg_id int)
RETURNS VOID AS
$$
BEGIN
	DELETE FROM actuators WHERE arg_id=id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_actuators_of_alert(arg_alert_id int)
RETURNS TABLE(
	ret_int int,
	ret_account_id varchar(80),
	ret_account_secret varchar(80),
	ret_value varchar(50),
	ret_device_id varchar(50),
	ret_stream_name varchar(80)
) AS
$$
BEGIN
	RETURN QUERY SELECT id, account_id, account_secret, value, device_id, stream_name FROM actuators where alert_id=arg_alert_id;
END
$$
LANGUAGE plpgsql;


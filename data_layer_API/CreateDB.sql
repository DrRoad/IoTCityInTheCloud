CREATE USER "smReceiver";

CREATE DATABASE subscriptionsdb;

\c subscriptionsdb

alter user "smReceiver" with encrypted password 'ReceiverPass';

GRANT ALL PRIVILEGES ON DATABASE subscriptionsdb to "smReceiver";

CREATE TABLE devices(
	device_id varchar(50) PRIMARY KEY,
	device_secret varchar(80) NOT NULL
);

CREATE TABLE subscriptions_table (
	subscriptions varchar(50) PRIMARY KEY,
	device varchar(50) references devices (device_id) NOT NULL,
	pooling boolean NOT NULL
);

GRANT ALL PRIVILEGES ON TABLE subscriptions_table TO "smReceiver";
GRANT ALL PRIVILEGES ON TABLE devices TO "smReceiver";
GRANT ALL ON SCHEMA public TO "smReceiver";

CREATE OR REPLACE FUNCTION get_all_subscriptions_with_devices_for_pooling() 
RETURNS TABLE (subscriptions varchar(50), device_id varchar(50), device_secret varchar(80)) AS
$$
BEGIN
    RETURN QUERY SELECT ST.subscriptions, D.device_id, D.device_secret FROM subscriptions_table as ST INNER JOIN devices as D ON ST.device=D.device_id WHERE pooling=TRUE;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_subscription_and_device(subscription varchar(50), device_id_arg varchar(50), device_secret_arg varchar(50), pooling boolean) RETURNS VOID AS
$$
BEGIN
	INSERT INTO devices VALUES (device_id_arg, device_secret_arg) ON CONFLICT (device_id) DO NOTHING;
    INSERT INTO subscriptions_table VALUES (subscription, device_id_arg, pooling);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_pooling(subscription_id varchar(50), pooling_arg boolean) RETURNS VOID AS
$$
BEGIN
	UPDATE subscriptions_table as ST SET pooling=pooling_arg WHERE ST.subscriptions=subscription_id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_subscription(subscription varchar(50)) RETURNS VOID AS
$$
BEGIN
	DELETE FROM subscriptions_table AS ST WHERE ST.subscriptions=subscription;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION exists_subscription_push(subscription_id varchar(50)) RETURNS BOOLEAN AS
$$
BEGIN
	RETURN EXISTS(SELECT ST.subscriptions FROM subscriptions_table as ST WHERE ST.subscriptions=subscription_id AND pooling=FALSE);
END;
$$
LANGUAGE plpgsql;
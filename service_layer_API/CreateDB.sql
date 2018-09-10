CREATE USER "serviceLayer";

CREATE DATABASE iotcdb;

\c iotcdb

alter user "serviceLayer" with encrypted password 'serviceLPass';

GRANT ALL PRIVILEGES ON DATABASE iotcdb to "serviceLayer";

CREATE TABLE verticals (
	name varchar(100) PRIMARY KEY
);


CREATE TABLE devices (
	id varchar(50) PRIMARY KEY,
	name varchar(50) NOT NULL,
	vertical varchar(100) REFERENCES verticals (name) NOT NULL,
	description text,
	location varchar(50),
	secret varchar(80) NOT NULL
);

CREATE TABLE stream (
	name varchar(50),
	device_id varchar(50) REFERENCES devices(id),
	description text,
	actuator boolean NOT NULL,
	PRIMARY KEY(device_id, name)
);

CREATE TABLE subscriptions (
	id varchar(50) PRIMARY KEY,
	name varchar(50) NOT NULL,
	subscriber_id varchar(50) REFERENCES devices(id) NOT NULL,
	device_id varchar(50) NOT NULL,
	device_secret varchar(80) NOT NULL,
	stream_name varchar(50) NOT NULL,
	description text,
	state varchar(10),
	method varchar(4)
);

GRANT ALL PRIVILEGES ON TABLE verticals TO "serviceLayer";
GRANT ALL PRIVILEGES ON TABLE devices TO "serviceLayer";
GRANT ALL PRIVILEGES ON TABLE stream TO "serviceLayer";
GRANT ALL PRIVILEGES ON TABLE subscriptions TO "serviceLayer";
GRANT ALL ON SCHEMA public TO "serviceLayer";


CREATE OR REPLACE FUNCTION get_all_verticals()
RETURNS TABLE (verticals varchar(100)) AS
$$
BEGIN
    RETURN QUERY SELECT name FROM verticals;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_vertical(name_arg varchar(50)) RETURNS VOID AS
$$
BEGIN
	INSERT INTO verticals VALUES (name_arg);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_vertical(name_arg varchar(50)) RETURNS VOID AS
$$
BEGIN
	DELETE FROM verticals WHERE name=name_arg;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_device(name varchar(50), vertical varchar(100), description text, location varchar(50), id varchar(50), secret varchar(80)) RETURNS VOID AS
$$
BEGIN
	INSERT INTO devices VALUES (id, name, vertical, description, location, secret);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_all_devices()
RETURNS TABLE (
	id varchar(50),
	name varchar(50),
	vertical varchar(100),
	description text,
	location varchar(50),
	secret varchar(80))
	AS
$$
BEGIN
	RETURN QUERY SELECT * FROM devices;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_device(id_arg varchar(50)) RETURNS VOID AS
$$
BEGIN
	DELETE FROM devices WHERE id=id_arg;
END
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_id_all_devices()
RETURNS TABLE (id_tb varchar(50))
	AS
$$
BEGIN
	RETURN QUERY SELECT id FROM devices;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_stream(name varchar(50), device_id varchar(50), description text, actuator boolean) RETURNS VOID AS
$$
BEGIN
	INSERT INTO stream VALUES (name, device_id, description, actuator);
END
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_streams_of_device(device_id_arg varchar(50)) RETURNS 
TABLE (
	name varchar(50),
	device_id_tb varchar(50),
	description text,
	actuator boolean)
AS
$$
BEGIN
	RETURN QUERY SELECT * FROM stream WHERE stream.device_id=device_id_arg;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_stream(device_id_arg varchar(50), stream_name_arg varchar(50)) RETURNS VOID AS
$$
BEGIN
	DELETE FROM stream WHERE device_id=device_id_arg AND name=stream_name_arg;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION insert_subscription(
	id varchar(50),
	name varchar(50),
	subscriber_id varchar(50),
	device_id varchar(50),
	device_secret varchar(80),
	stream_name varchar(50),
	description text,
	state varchar(10),
	method varchar(4)
	) RETURNS VOID AS
$$
BEGIN
	INSERT INTO subscriptions VALUES (id, name, subscriber_id, device_id, device_secret, stream_name, description, state, method);
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_all_subscriptions()
RETURNS TABLE (
	id varchar(50),
	name varchar(50),
	subscriber_id varchar(50),
	device_id varchar(50),
	device_secret varchar(80),
	stream_name varchar(50),
	description text,
	state varchar(10),
	method varchar(4))
	AS
$$
BEGIN
	RETURN QUERY SELECT * FROM subscriptions;
END
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION remove_subscription(id_arg varchar(50)) RETURNS VOID AS
$$
BEGIN
	DELETE FROM subscriptions WHERE id_arg=id;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_device_password_to_actuate(arg_device_id varchar(50), arg_stream_name varchar(50))
RETURNS TABLE (rec_secret varchar(80)) AS
$$
BEGIN
	RETURN QUERY SELECT secret FROM devices JOIN stream ON stream.device_id=devices.id AND stream.device_id=arg_device_id AND stream.name=arg_stream_name;
END
$$
LANGUAGE plpgsql;
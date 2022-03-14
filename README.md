Phone CallerID remote sensor using MQTT to communicate to my home assistant setup

Caller ID and number is main sensor  mqtt output topic

Also a mqtt status published every 15 minutes or any change to the phone monitor state

A return mqtt topic can be published to sensor to hang up the incoming call


Sensor is built in python3 and dependent on a voice capable modem. The modem control is derived from basic modem code: https://github.com/gurbyz/basicmodem


./caller_id.py


callerID.service


docker build -t caller-id .
docker run --restart always -i --device=/dev/ttyACM0 caller-id
docker start caller-id

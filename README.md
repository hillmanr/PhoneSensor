Phone CallerID remote sensor using MQTT to communicate to my home assistant setup

Caller ID and number is main mqtt sensor 

Also a mqtt status published every 15 minutes or any change to the phone state: init, idle, ring, fail, callerid

A return mqtt topic can be published to sensor to hang up the incoming call


Sensor is built in python3 and dependent on a voice capable modem. The modem control is derived from basic modem code: https://github.com/gurbyz/basicmodem

There are 3 ways to envoke the sensor
1) command line using code in src/ directory:   ./caller_id.py
2) build a linux service using systemctl and modify paths in file: callerID.service
3) using docker\
&nbsp;&nbsp;&nbsp;&nbsp; docker build -t caller-id . \
&nbsp;&nbsp;&nbsp;&nbsp; docker run --name caller-id --restart always -i --device=/dev/ttyACM0 caller-id\
&nbsp;&nbsp;&nbsp;&nbsp; docker start caller-id

#!/usr/bin/env python3
import logging
import serial
from basicmodem.basicmodem import BasicModem as bm
import paho.mqtt.client as mqtt
import datetime
import time
import json
import configparser


config = configparser.ConfigParser()
config.read('myconfig.ini')
if config.has_section('mqtt')  == False:
    config.read('config.ini')
broker = config['mqtt']['host']
port = int(config['mqtt']['port'])
user = config['mqtt']['user']
passwd = config['mqtt']['passwd']
tty = config['modem']['tty']
logfile = config['logger']['file']
loglevel = logging.INFO
if  config['logger']['debug'] == '1':
    loglevel = logging.DEBUG



ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh = logging.FileHandler(logfile)

# create logger
logger = logging.getLogger('Main')
logger.setLevel(loglevel)

# add ch to loggerclient1.publish("stat/phoneCaller/id",msg)
logger.addHandler(ch)
logger.addHandler(fh)

# 'application' code
logger.debug('MQTT host:%s port:%s user:%s password:%s',
            broker, port, user, passwd )




def hangup_call():
    # answer call
    resp = modem.sendcmd("ATA")
    for line in resp:
        if line:
            logger.debug('Answer: %s',line)
    # switch to voice mode
    resp = modem.sendcmd("AT+FCLASS=8")
    for line in resp:
        if line:
            logger.debug('Voice Mode:: %s',line)
    # hangug
    resp = modem.sendcmd("ATH")
    for line in resp:
        if line:
            logger.debug('Hangup: %s',line)


def hangup_message(client, userdata, message):
    data = str(message.payload.decode("utf-8"))
    if data == "1":
      logger.info("recieved terminate call control")
      client.publish("cmnd/setPhoneOFF/control")
      hangup_call()


def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        logger.info("MQTT connection OK")
    else:
      logger.info("Bad MQTT connection")
      exit(1)

# 'idle' 'ring' 'callerid' 'init' 'fail'
def callback(newstate):
    global client
    """Callback from modem, process based on new state"""
    if newstate == 'callerid':
        msg = {"time": modem.get_cidtime.strftime("%I:%M %p"),
               "number": modem.get_cidnumber,
               "caller": modem.get_cidname}
        data_out = json.dumps(msg)
        client.publish("stat/phoneCaller/id",data_out)
        logger.info('CallerID Detected: %s', msg)
    
    logger.debug('New Modem State: %s', newstate)
    client.publish('stat/phone/status', newstate)
    return

client= mqtt.Client('Phone Control')
client.on_connect=on_connect
client.username_pw_set(user, passwd)
client.on_message=hangup_message
client.connect(broker,port)
client.loop_start()    #start the loop
client.subscribe("cmnd/setPhoneOFF/control")

modem = bm(tty, callback, logfile, loglevel)
def main():
    logger.info("Starting version 1.1 main loop")
    current = modem.state
    count = 0
    while current != 'fail':
       count = count + 1 
       state = modem.state
       if state != current or count > 50:
          count = 0
          current = state
          logger.debug('New State: %s', state)
          client.publish('stat/phone/status',state)
       time.sleep(15)

    modem.close()


if __name__ == '__main__':
    main()

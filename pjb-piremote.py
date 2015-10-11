#!/usr/bin/env python2.7
# Remote control of a Raspberry Pi through MQTT requests
# By Paul Booth 2015  paul_booth_uk@hotmail.com
#

import subprocess
import os
import sys
import time, datetime
import paho.mqtt.client as paho        #as instructed by http://mosquitto.org/documentation/python/
import RPi.GPIO as GPIO
from ConfigParser import SafeConfigParser

configfile = "pjb-piremote.cfg"
dateString = '%Y/%m/%d %H:%M:%S'
progname = sys.argv[0]
keep_running = 1
mqtt_connected = 0


####  here are the defs   ###################


def printlog(message):
	logline = progname + version + " " + datetime.datetime.now().strftime(dateString) + " " + message
	print logline	
	if mqtt_connected == 1:
		client.publish(topicLog, payload=logline, qos=0, retain=False)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
    client.subscribe(topicRequest)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	global parms
	try:
		cmd = msg.payload
		reqnum = int(cmd)
	except ValueError:
		reqnum = 0
	requests[reqnum]()        #  execute the requested subroutine
	printlog(msg.topic+" "+str(msg.payload))


def badrequest():
	printlog("Requests must be an integer between 1 and 2 inclusive")


def shutdown():
	global keep_running
	printlog("Stopping the Raspberry")
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -h now"
	import subprocess
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def reboot():
	printlog("Restarting as requested")
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	import subprocess
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def dummy():
	dummyline = "this does not do anything"

###########  end of defs  ##################

requests = {0 : badrequest,
			1 : shutdown,
			2 : reboot
}

try:
	parser = SafeConfigParser()										# open and read the configuration file
	parser.read(configfile)
	version = parser.get('pjb-piremote', 'version')
	mqttBroker = parser.get('pjb-piremote', 'mqttBroker')
	topicRequest = parser.get('pjb-piremote', 'topicRequest')
	topicLog = parser.get('pjb-piremote', 'topicLog')
	delay = parser.getint('pjb-piremote', 'delay')
	
	printlog(progname + " starting up")							# startup message
	
	try:     									# Create the MQTT client, connect to the broker and start threaded loop in background
		global client
		client = paho.Client()           			# as instructed by http://mosquitto.org/documentation/python/
		printlog("done paho.Client()")
		client.on_connect = on_connect				# Connect to the MQTT broker 
		printlog("done client.on_connect")
		client.on_message = on_message
		printlog("done client.on_message")
		client.connect(mqttBroker, 1883, 60)
		printlog("done client.connect")
		mqtt_connected = 1
		printlog("MQTT client connected to broker")
		try:
			while keep_running == 1:
				client.loop(timeout=1.0, max_packets=1)
				time.sleep(delay)
		except:
			printlog("Unknown fault in main loop")
	except:
		printlog("Cannot start MQTT client and connect to MQ broker")
except KeyboardInterrupt:
	printlog("Exiting after Ctrl-C")
except:
	printlog("Trouble reading configuration file: " + configfile)

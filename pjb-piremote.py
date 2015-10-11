#!/usr/bin/env python2.7
# Remote control of a Raspberry Pi through MQTT requests
# By Paul Booth 2015  paul_booth_uk@hotmail.com
#
configfile = "pjb-piremote.cfg"
dateString = '%Y/%m/%d %H:%M:%S'

import subprocess
import os
import sys
import time, datetime
import paho.mqtt.client as paho        #as instructed by http://mosquitto.org/documentation/python/
import RPi.GPIO as GPIO
from ConfigParser import SafeConfigParser


####  here are the defs   ###################


def printlog(message):
	logline = version + " " + datetime.datetime.now().strftime(dateString) + " " + message
	print logline	
#	client.publish(topicLog, payload=logline, qos=0, retain=False)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
    client.subscribe(topicLog)


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
	parser = SafeConfigParser()
	parser.read(configfile)
	version = parser.get('pjb-piremote', 'version')
	topicRequest = parser.get('pjb-piremote', 'topicRequest')
	topicLog = parser.get('pjb-piremote', 'topicLog')
	printlog("version = " + version)
	
	
	
except:
	printlog("Trouble reading configuration file: " + filename)
	
except KeyboardInterrupt:
	printlog("Exiting after Ctrl-C")
	
finally:
	GPIO.cleanup()     # this ensures a clean exit	


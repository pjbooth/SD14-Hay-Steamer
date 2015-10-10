#!/usr/bin/env python2.7
# Remote control of a Raspberry Pi through MQTT requests
# By Paul Booth 2015  paul_booth_uk@hotmail.com
#
filename = "pjb-piremote.cfg"
dateString = '%Y/%m/%d %H:%M:%S'

import subprocess
import os
import sys
import time, datetime
import paho.mqtt.client as paho        #as instructed by http://mosquitto.org/documentation/python/
import smtplib
import base64
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText


####  here are the defs   ###################


def printlog(message):
	logline = version + " " + datetime.datetime.now().strftime(dateString) + " " + message
	print logline	
	if diagnostics ==1:
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


def endprog():
	global keep_running
	printlog("Stopping the Raspberry")
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -h now"
	import subprocess
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output
	
	
def setdelay():
	global parms
	printlog("Setting delay")
	printlog("Parms = " + parms)
	


def restart():
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
			1 : diagon,
			2 : diagoff,
			3 : restart,
			4 : endprog,
			5 : setdelay,
}


GPIO.setmode(GPIO.BCM) 
GPIO.setup(23, GPIO.OUT) # 23 for LDR light sensor


try:
	lines = [line.rstrip('\n') for line in open('filename')]
except:
	printlog("Trouble reading configuration file: " + filename)


try:     # Create the MQTT client, connect to the broker and start threaded loop in background
	global client
	client = paho.Client()           # as instructed by http://mosquitto.org/documentation/python/
	# Connect to the MQTT broker 
	client.on_connect = on_connect
	client.on_message = on_message
	client.connect("iot.eclipse.org", 1883, 60)
	print("MQTT client connected to broker")
except:
	print("Cannot start MQTT client and connect to MQ broker")


try:
	while keep_running == 1:
            sensor = 1
            for device in w1_device_list:
                temperature = '%d' % read_temp(device)
                sensor += 1
            msgline = "Temperature = " + temperature + "C"
            printlog(msgline)
            client.loop(timeout=1.0, max_packets=1)
            time.sleep(delay)
    	
except KeyboardInterrupt:
	printlog("Exiting after Ctrl-C")
	
except:
	printlog("Unexpected fault occurred in main loop")
	
finally:
	GPIO.cleanup()     # this ensures a clean exit	


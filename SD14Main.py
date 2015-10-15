#!/usr/bin/env python2.7
# Temperature watcher .. publishes temperature over MQTT
# based on example from Raspberry Pi Temperature and Light Sensor.pdf 
# By Paul Booth 2015  paul_booth_uk@hotmail.com
#
# This script should automatically detect your 1-wire sensors
# It will load device drivers for them if needed
# Just wire them up and run it
# By Alex Eames http://RasPi.TV

import subprocess
import os
import sys
import time, datetime
import RPi.GPIO as GPIO
import paho.mqtt.client as paho        #as instructed by http://mosquitto.org/documentation/python/
from ConfigParser import SafeConfigParser
import ibmiotf.device


progname = sys.argv[0]
configfile = "SD14Main.cfg"
dateString = '%Y/%m/%d %H:%M:%S'
timeString = '%H:%M:%S'
keep_running = 1
mqtt_connected = 0
diagnostics = 1
organization = "p4t75f"
deviceType = "pjb-rpi"
deviceId = "b827eba84426"
authMethod = "token"
authToken = "*eMiC02@KsQ)xCO2Tx"
deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}


####  here are the defs   ###################


def read_temp(device):
	DS18b20 = open(device)
	text = DS18b20.read()
	DS18b20.close()
	secondline = text.split("\n")[1]		    # Split the text with new lines (\n) and select the second line.
	temperaturedata = secondline.split(" ")[9]	# Split the line into words, referring to the spaces, and select the 10th word (counting from 0).
	temperature = float(temperaturedata[2:])	# The first two characters are "t=", so get rid of those and convert the temperature from a string to a number.
	temperature = temperature / 1000			# Put the decimal point in the right place and display it.
	return temperature


def printlog(message):
	logline = progname + " " + version + " " + datetime.datetime.now().strftime(dateString) + ": " + message
	print logline	
	if mqtt_connected == 1 and diagnostics == 1:
		myData={'name' : progname, 'version' : version, 'date' : datetime.datetime.now().strftime(dateString), 'message' : message}
		client.publishEvent(event="logs", msgFormat="json", data=myData)


def printdata(temp):
	myData={'date' : datetime.datetime.now().strftime(dateString), 'temp' : temp}
	client.publishEvent(event="data", msgFormat="json", data=myData)


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
	printlog(msg.topic+" "+str(msg.payload))


###########  end of defs  ##################


GPIO.setmode(GPIO.BCM) 
GPIO.setup(23, GPIO.OUT) # 23 for LDR light sensor


try:
	parser = SafeConfigParser()										# open and read the configuration file
	parser.read(configfile)
	version = parser.get('SD14Main', 'version')
	delay = parser.getint('SD14Main', 'delay')
	printlog(progname + " starting up")							# startup messag

	try:     									# Create the MQTT client, connect to the IOTF broker and start threaded loop in background
		global client
		client = ibmiotf.device.Client(deviceOptions)
		client.connect()
		mqtt_connected = 1
		printlog("MQTT client connected to broker")

		try:
			w1_devices = os.listdir("/sys/bus/w1/devices/")
		except:
			printlog("Loading 1-wire device drivers, please wait five seconds...")
			output_mp1 = subprocess.Popen('sudo modprobe w1-gpio', shell=True, stdout=subprocess.PIPE)
			output_mp2 = subprocess.Popen('sudo modprobe w1-therm', shell=True, stdout=subprocess.PIPE)
			time.sleep(5)        									# wait a few seconds to stop the program storming ahead and crashing out
			w1_devices = os.listdir("/sys/bus/w1/devices/")
		no_of_devices = len(w1_devices) -1
		printlog("You have %d 1-wire devices attached" % (no_of_devices))
		if no_of_devices < 1:
			printlog("Please check your wiring and try again.")
			sys.exit()
		w1_device_list = []
		for device in w1_devices:
			if not ('w1_bus' in device):				        # create string for calling each device and append to list
				this_device = "/sys/bus/w1/devices/" + device + "/w1_slave"
				w1_device_list.append(this_device)

		try:
			while keep_running == 1:
				sensor = 1
				for device in w1_device_list:
					temperature = '%d' % read_temp(device)
					sensor += 1
				printdata(temperature)
				client.loop(timeout=1.0, max_packets=1)
				time.sleep(delay)

		except KeyboardInterrupt:
			printlog("Exiting after Ctrl-C")

		except:
			printlog("Unexpected fault occurred in main loop")

	except:
		printlog("Cannot start MQTT client and connect to MQ broker")

except:
	printlog("Unable to process configuration file " + configfile)

finally:
	GPIO.cleanup()     # this ensures a clean exit	


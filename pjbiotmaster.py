#!/usr/bin/env python2.7
# Controller program for IoT devices.  
# Connects via MQTT
# Reports CPU stats
# Allows a limited range of commands such as reboot, shutdown, ...

import subprocess
import os
import sys
import time, datetime
import paho.mqtt.client as paho        #as instructed by http://mosquitto.org/documentation/python/
import ibmiotf.device
import psutil


progname = sys.argv[0]						# name of this program
version = "1.0"								# allows me to track which release is running
interval = 15								# number of seconds between readings
iotfFile = "/home/pi/SD14IOTF.cfg"
dateString = '%Y/%m/%d %H:%M:%S'
mqtt_connected = 0
keep_running = true


####  here are the defs   ###################


def printlog(message):
	logline = progname + " " + version + " " + datetime.datetime.now().strftime(dateString) + ": " + message
	print logline	
	if mqtt_connected == 1 and diagnostics == 1:
		myData={'name' : progname, 'version' : version, 'date' : datetime.datetime.now().strftime(dateString), 'message' : message}
		client.publishEvent(event="logs", msgFormat="json", data=myData)


def printdata():
#	cputemp = getCPUtemperature()
	res = os.popen('vcgencmd measure_temp').readline()
	cputemp = float(res.replace("temp=","").replace("'C\n",""))
	cpupct = float(psutil.cpu_percent())
	cpumem = float(psutil.virtual_memory().percent)
	myData = {'date' : datetime.datetime.now().strftime(dateString), 'cputemp' : cputemp, 'cpupct' : cpupct, 'cpumem' : cpumem}
	client.publishEvent(event="data", msgFormat="json", data=myData)


def myCommandCallback(cmd):						# callback example from IOTF documentation
	global keep_running
	printlog("Command received: " + cmd.command + " with data: %s" % cmd.data)
	if cmd.command == "dkE20s*r19s!u":
		reboot()
	elif cmd.command == "gsYi21lu-!e8":
		shutdown()
	elif cmd.command == "Exit":
		keep_running = false
	else:
		printlog("Unsupported command: %s" % cmd.command)


def shutdown():
	command = "/usr/bin/sudo /sbin/shutdown -h now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def reboot():
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


###########  end of defs  ##################


try:
	deviceOptions = ibmiotf.device.ParseConfigFile(iotfFile)	# keeping the IOTF config file locally on device for security
	try:     									# Create the MQTT client, connect to the IOTF broker and start threaded loop in background
		global client
		client = ibmiotf.device.Client(deviceOptions)
		client.connect()
		mqtt_connected = 1
		client.commandCallback = myCommandCallback
		try:
			while keep_running:
				printdata()					# Transmit CPU stats
				time.sleep(delay)
		except KeyboardInterrupt:
			printlog("Exiting as requested")
		except BaseException as e:
			printlog("Unexpected fault occurred in main loop: " + str(e))
	except:
		printlog("Cannot start MQTT client and connect to MQ broker")
except:
	printlog("Unable to process configuration file " + iotfFile)

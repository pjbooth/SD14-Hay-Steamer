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
#from ConfigParser import SafeConfigParser
import ibmiotf.device


progname = sys.argv[0]						# name of this program
version = "2.2"								# allows me to track which release is running
interval = 5								# number of seconds between readings
iotfFile = "/home/pi/SD14IOTF.cfg"
dateString = '%Y/%m/%d %H:%M:%S'
state = 0									# keep track of which state we are in
											# state 0 = RAG = booting up 
											# state 1 = R   = Up and connected to IOTF but steamer not turned on
											# state 2 = A   = Steamer switched on but not yet reached target temperature
											# state 3 = G   = Target temperature reached
mqtt_connected = 0
diagnostics = 1
target = 25									# target temperature
greenLED = 23
amberLED = 24
redLED = 25
buttonSteam = 7
buttonReset = 8


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


def printdata(data):
	global state
	myData = {'date' : datetime.datetime.now().strftime(dateString), 'temp' : data, 'state' : state}
	vizData = {'d' : myData}
	client.publishEvent(event="data", msgFormat="json", data=vizData)


def myCommandCallback(cmd):						# callback example from IOTF documentation
	global state
	printlog("Command received: " + cmd.command + " with data: " + cmd.data)
	if cmd.command == "setState":
		if 'state' not in cmd.data:
			printlog("Error - command is missing required information: 'state'")
		else:
			try:
				i = int(cmd.data['state'])
				state = i
			except:
				printlog("Invalid state value")

	elif cmd.command == "dkE20s*r19s!u":
		reboot()

	elif cmd.command == "gsYi21lu-!e8":
		shutdown()

	else:
		printlog("Unsupported command: %s" % cmd.command)


def shutdown():
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -h now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def reboot():
	printlog("Restarting as requested")
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


###########  end of defs  ##################


GPIO.setmode(GPIO.BCM) 
GPIO.setup(buttonSteam, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Push button 1
GPIO.setup(buttonReset, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Push button 2
GPIO.setup(greenLED, GPIO.OUT)								# LED 1
GPIO.setup(amberLED, GPIO.OUT)								# LED 2
GPIO.setup(redLED, GPIO.OUT)								# LED 3
GPIO.output(greenLED, 1)									# Turn on LED to confirm it works
GPIO.output(amberLED, 1)									# Turn on LED to confirm it works
GPIO.output(redLED, 1)									# Turn on LED to confirm it works


try:
	deviceOptions = ibmiotf.device.ParseConfigFile(iotfFile)	# keeping the IOTF config file locally on device for security

	try:     									# Create the MQTT client, connect to the IOTF broker and start threaded loop in background
		global client
		client = ibmiotf.device.Client(deviceOptions)
		client.connect()
		mqtt_connected = 1
		client.commandCallback = myCommandCallback

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
		state = 1

		try:
			while state < 10:							# Use state 10 to request a controlled termination of program
				if state == 1:
					GPIO.output(redLED, 1)
					GPIO.output(amberLED, 0)
					GPIO.output(greenLED, 0)
					i = 300
					while state == 1:								# Wait for Steam button to be pressed
						i += 1
						if i > 300:									# every minute....
							for device in w1_device_list:
								t = read_temp(device)
							printdata(t)							# Keep the user informed of our state
							i = 0
						input_state = GPIO.input(buttonSteam)
						if input_state == False:
							state = 2
						time.sleep(0.2)

				elif state == 2:
					GPIO.output(redLED, 0)
					GPIO.output(amberLED, 1)
					GPIO.output(greenLED, 0)			
					t = -100							# start with an absurdly low temperature until first reading is captured so loop works
					while state == 2:
						for device in w1_device_list:
							t = read_temp(device)
							printdata(t)
						if t > target:
							state = 3
						i = interval * 5				# the button read loop happens 5 times per second
						while i > 0:					# Wait 'interval' seconds whilst watching the Reset button
							i -= 1
							input_state = GPIO.input(buttonReset)		# Spend the interval checking if the Reset button is pressed
							if input_state == False:
								state = 1								# go back to State 1
								break
							time.sleep(0.2)

				elif state == 3:
					GPIO.output(redLED, 0)
					GPIO.output(amberLED, 0)
					GPIO.output(greenLED, 1)
					i = 300
					while state == 3:
						i += 1
						if i > 300:						# every minute....
							for device in w1_device_list:
								t = read_temp(device)
							printdata(t)				# Keep the user informed of our state
							i = 0
						input_state = GPIO.input(buttonReset)			# Wait until the Reset button is pressed
						if input_state == False:
							state = 1
						time.sleep(0.2)

		except KeyboardInterrupt:
			printlog("Exiting after Ctrl-C")

		except:
			printlog("Unexpected fault occurred in main loop")

	except:
		printlog("Cannot start MQTT client and connect to MQ broker")

except:
	printlog("Unable to process configuration file " + iotfFile)

finally:
	printlog("Closing program as requested")
	GPIO.cleanup()     # this ensures a clean exit	


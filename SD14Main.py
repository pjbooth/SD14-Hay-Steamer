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
import psutil


progname = sys.argv[0]						# name of this program
version = "2.5"								# allows me to track which release is running
interval = 15								# number of seconds between readings (note that ThingSpeak max rate is one update per 15 seconds)
iotfFile = "/home/pi/SD14IOTF.cfg"
dateString = '%Y/%m/%d %H:%M:%S'
state = 0									# keep track of which state we are in
											# state 0 = RAG = booting up 
											# state 1 = R   = Up and connected to IOTF but steamer not turned on
											# state 2 = A   = Steamer switched on but not yet reached target temperature
											# state 3 = G   = Target temperature reached
mqtt_connected = 0
diagnostics = 1
trigger = 30								# temperature at which the countdown safety timer begins
safety = 30								# number of seconds to continue after trigger temperature is reached
trip = 0									# the countdown timer trip switch ... zero means it's not yet set
target = 86									# target temperature
greenLED = 13								# These are GPIO numbers
amberLED = 19
redLED = 26
buttonSteam = 20
buttonReset = 16
buzzer = 21
error_count = 0
error_limit = 20


####  here are the defs   ###################


def read_temp(device):
	global error_count
	temperature = 0
	DS18b20 = 0
	try:
		DS18b20 = open(device)
		try:
			text = DS18b20.read()
			secondline = text.split("\n")[1]		    # Split the text with new lines (\n) and select the second line.
			temperaturedata = secondline.split(" ")[9]	# Split the line into words, referring to the spaces, and select the 10th word (counting from 0).
			temperature = float(temperaturedata[2:])	# The first two characters are "t=", so get rid of those and convert the temperature from a string to a number.
			temperature = temperature / 1000			# Put the decimal point in the right place and display it.
		except:
			printlog("Error trying to read thermometer: " + str(sys.exc_info()[0]))
			error_count += 1
			DS18b20.close()
	except:
		printlog("Error trying to open thermometer: " + str(sys.exc_info()[0]))
		error_count += 1
	return temperature


def printlog(message):
	logline = progname + " " + version + " " + datetime.datetime.now().strftime(dateString) + ": " + message
	print logline	
	if mqtt_connected == 1 and diagnostics == 1:
		myData={'name' : progname, 'version' : version, 'date' : datetime.datetime.now().strftime(dateString), 'message' : message}
		client.publishEvent(event="logs", msgFormat="json", data=myData)


def printdata(data):
	global state
	cputemp = getCPUtemperature()				# may as well report on various processor stats while we're at it
	cpupct = float(psutil.cpu_percent())
	cpumem = float(psutil.virtual_memory().percent)
	myData = {'date' : datetime.datetime.now().strftime(dateString), 'temp' : data, 'state' : state, 'cputemp' : cputemp, 'cpupct' : cpupct, 'cpumem' : cpumem}
	vizData = {'d' : myData}
	client.publishEvent(event="data", msgFormat="json", data=myData)


def myCommandCallback(cmd):						# callback example from IOTF documentation
	global state
	printlog("Command received: " + cmd.command + " with data: %s" % cmd.data)
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
	mains_off()
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -h now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def reboot():
	printlog("Restarting as requested")
	mains_off()
	GPIO.cleanup()
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
	output = process.communicate()[0]
	print output


def mains_init():
#	printlog("Initialising Mains")
	# Select the GPIO pins used for the encoder K0-K3 data inputs
	GPIO.setup(17, GPIO.OUT)
	GPIO.setup(22, GPIO.OUT)
	GPIO.setup(23, GPIO.OUT)
	GPIO.setup(27, GPIO.OUT)
	# Select the signal to select ASK/FSK
	GPIO.setup(24, GPIO.OUT)
	# Select the signal used to enable/disable the modulator
	GPIO.setup(25, GPIO.OUT)
	# Disable the modulator by setting CE pin lo
	GPIO.output (25, False)
	# Set the modulator to ASK for On Off Keying 
	# by setting MODSEL pin lo
	GPIO.output (24, False)
	# Initialise K0-K3 inputs of the encoder to 0000
	GPIO.output (17, False)
	GPIO.output (22, False)
	GPIO.output (23, False)
	GPIO.output (27, False)


def mains_on():
#	printlog("Mains ON")
	# Set K0-K3
	GPIO.output (17, True)
	GPIO.output (22, True)
	GPIO.output (23, True)
	GPIO.output (27, True)
	# let it settle, encoder requires this
	time.sleep(0.1)	
	# Enable the modulator
	GPIO.output (25, True)
	# keep enabled for a period
	time.sleep(0.25)
	# Disable the modulator
	GPIO.output (25, False)


def mains_off():
#	printlog("Mains OFF")
	# Set K0-K3
	GPIO.output (17, True)
	GPIO.output (22, True)
	GPIO.output (23, True)
	GPIO.output (27, False)
	# let it settle, encoder requires this
	time.sleep(0.1)
	# Enable the modulator
	GPIO.output (25, True)
	# keep enabled for a period
	time.sleep(0.25)
	# Disable the modulator
	GPIO.output (25, False)


# Return CPU temperature as a float                                      
def getCPUtemperature():
	res = os.popen('vcgencmd measure_temp').readline()
	cputemp = float(res.replace("temp=","").replace("'C\n",""))
	return cputemp


###########  end of defs  ##################


GPIO.setmode(GPIO.BCM) 
GPIO.setup(buttonSteam, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Push button 1
GPIO.setup(buttonReset, GPIO.IN, pull_up_down=GPIO.PUD_UP)		# Push button 2
GPIO.setup(greenLED, GPIO.OUT)								# LED 1
GPIO.setup(amberLED, GPIO.OUT)								# LED 2
GPIO.setup(redLED, GPIO.OUT)								# LED 3
GPIO.setup(buzzer, GPIO.OUT)								# Buzzer
GPIO.output(greenLED, 1)									# Turn on LED to confirm it works
GPIO.output(amberLED, 1)									# Turn on LED to confirm it works
GPIO.output(redLED, 1)									# Turn on LED to confirm it works
mains_init()				# initialise the Energenie power controller
mains_off()

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
		if no_of_devices != 1:
			printlog("Please check your wiring and try again.")
			sys.exit()
		w1_device_list = []
		for device in w1_devices:
			if not ('w1_bus' in device):				        # create string for calling each device and append to list
				this_device = "/sys/bus/w1/devices/" + device + "/w1_slave"
				w1_device_list.append(this_device)
		state = 1


		try:
			while state < 10  and error_count < error_limit:							# Use state 10 to request a controlled termination of program
				if state == 1:
					GPIO.output(redLED, 1)
					GPIO.output(amberLED, 0)
					GPIO.output(greenLED, 0)
					i = 300
					while state == 1 and error_count < error_limit:								# Wait for Steam button to be pressed
						i += 1
						if i > 300:									# every minute....
							mains_off()
							for device in w1_device_list:
								t = read_temp(device)
							printdata(t)							# Keep the user informed of our state
							i = 0
						input_state = GPIO.input(buttonSteam)
						if input_state == False:
							state = 2
							mains_on()
						time.sleep(0.2)

				elif state == 2 and error_count < error_limit:
					GPIO.output(redLED, 0)
					GPIO.output(amberLED, 1)
					GPIO.output(greenLED, 0)			
					t = -100							# start with an absurdly low temperature until first reading is captured so loop works
					while state == 2:
						mains_on()
						for device in w1_device_list:
							t = read_temp(device)
							printdata(t)
						if t > trigger:					# we must be into the safety countdown period in case the clips are off
							if trip == 0:				# we have just crossed over the trigger temperature
								trip = safety + time.time()		# trip becomes the target "safety cutout" time
							elif trip < time.time():		# the safety cutout time has expired so shut everything down
								state = 4				# a new state indicating a fault
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

				elif state == 3 and error_count < error_limit:
					GPIO.output(redLED, 0)
					GPIO.output(amberLED, 0)
					GPIO.output(greenLED, 1)
					i = 300
					while state == 3:
						mains_off()
						i += 1
						if i > 280:						# every minute....  the buzzer takes 4 seconds, the loop 56 seconds at 5 times per second round the loop
							for device in w1_device_list:
								t = read_temp(device)
							printdata(t)				# Keep the user informed of our state
							for j in range(4):
								GPIO.output(buzzer,1)			# sound the buzzer
								time.sleep(0.5)
								GPIO.output(buzzer,0)			# turn off the buzzer
								time.sleep(0.5)
							i = 0
						input_state = GPIO.input(buttonReset)			# Wait until the Reset button is pressed
						if input_state == False:
							state = 1
						time.sleep(0.2)
						
				elif state == 4 and error_count < error_limit:				# this state is entered if a steamer fault is detected
					while state == 4:
						GPIO.output(redLED, 1)
						GPIO.output(amberLED, 0)
						GPIO.output(greenLED, 0)
						mains_off()
						for device in w1_device_list:
							t = read_temp(device)
						printdata(t)				# Keep the user informed of our state
						GPIO.output(redLED, 1)
						GPIO.output(buzzer,1)			# sound the buzzer
						time.sleep(0.5)
						GPIO.output(redLED, 0)
						GPIO.output(buzzer,0)			# turn off the buzzer
						time.sleep(0.5)
						i = 0
						input_state = GPIO.input(buttonReset)			# Wait until the Reset button is pressed
						if input_state == False:
							state = 1
						time.sleep(0.2)


		except KeyboardInterrupt:
			printlog("Exiting after Ctrl-C")

		except BaseException as e:
			printlog("Unexpected fault occurred in main loop: " + str(e))

	except:
		printlog("Cannot start MQTT client and connect to MQ broker")

except:
	printlog("Unable to process configuration file " + iotfFile)

finally:
	if error_count < error_limit:
		printlog("Closing program as requested")
	else:
		printlog("Closing program due to excessive errors")
	mains_off()
	time.sleep(3)		# allow time to switch off
	GPIO.cleanup()		# this ensures a clean exit	


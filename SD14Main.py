#!/usr/bin/env python2.7
# Temperature watcher .. publishes temperature over MQTT
# based on example from Raspberry Pi Temperature and Light Sensor.pdf 
# By Paul Booth 2015  paul_booth_uk@hotmail.com
#
# This script should automatically detect your 1-wire sensors
# It will load device drivers for them if needed
# Just wire them up and run it
# By Alex Eames http://RasPi.TV

delay = 10                #  number of seconds between each reading sample
dateString = '%Y/%m/%d %H:%M:%S'
topicRequest = "PJB/SD14-Hay-Steamer/1/Request"
topicResponse = "PJB/SD14-Hay-Steamer/1/Response"
topicLog = "PJB/SD14-Hay-Steamer/1/Log"
diagnostics = 1
emailfrom = "pjb.rpi@gmail.com"
emailto = "paulbooth46@gmail.com"
username = emailfrom
password = "gmailpass9"
keep_running = 1


import subprocess
import os
import sys
import time, datetime
import RPi.GPIO as GPIO
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


def read_temp(device):
    DS18b20 = open(device)
    text = DS18b20.read()
    DS18b20.close()

    # Split the text with new lines (\n) and select the second line.
    secondline = text.split("\n")[1]

    # Split the line into words, referring to the spaces, and select the 10th word (counting from 0).
    temperaturedata = secondline.split(" ")[9]

    # The first two characters are "t=", so get rid of those and convert the temperature from a string to a number.
    temperature = float(temperaturedata[2:])

    # Put the decimal point in the right place and display it.
    temperature = temperature / 1000
    return temperature


def msr_time(msr_pin):
    reading = 0
    GPIO.setup(msr_pin, GPIO.OUT)
    GPIO.output(msr_pin, GPIO.LOW)
    time.sleep(0.1)
    starttime = time.time()                     # note start time
    GPIO.setup(msr_pin, GPIO.IN)
    while (GPIO.input(msr_pin) == GPIO.LOW):
        reading += 1
    endtime = time.time()                       # note end time
    total_time = 1000 * (endtime - starttime)
    return total_time                           # reading in milliseconds


def printlog(message):
	logline = datetime.datetime.now().strftime(dateString) + " " + message
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
		cmd, parms = msg.payload.split(' ', 1)
		reqnum = int(cmd)
	except ValueError:
		reqnum = 0
	requests[reqnum]()        #  execute the requested subroutine
	printlog(msg.topic+" "+str(msg.payload))


def badrequest():
	printlog("Requests must be an integer between 1 and 2 inclusive")


def diagon():
	global diagnostics
	diagnostics = 1
	print "turning diag on"


def diagoff():
	global diagnostics
	diagnostics = 0
	print "turning diag off"


def endprog():
	global keep_running
	printlog("Stopping the program")
	keep_running = 0
	
	
def setdelay():
	global parms
	printlog("Setting delay")
	printlog("Parms = " + parms)
	


def dummy():
	dummyline = "this does not do anything"

###########  end of defs  ##################

requests = {0 : badrequest,
			1 : diagon,
			2 : diagoff,
			3 : dummy,
			4 : endprog,
			5 : setdelay,
}


GPIO.setmode(GPIO.BCM) 
GPIO.setup(23, GPIO.OUT) # 23 for LDR light sensor


try:
    w1_devices = os.listdir("/sys/bus/w1/devices/")
except:
    print "Loading 1-wire device drivers, please wait five seconds..."
    output_mp1 = subprocess.Popen('sudo modprobe w1-gpio', shell=True, stdout=subprocess.PIPE)
    output_mp2 = subprocess.Popen('sudo modprobe w1-therm', shell=True, stdout=subprocess.PIPE)
    time.sleep(5)        # wait a few seconds to stop the program storming ahead and crashing out
    w1_devices = os.listdir("/sys/bus/w1/devices/")

no_of_devices = len(w1_devices) -1
print("You have %d 1-wire devices attached" % (no_of_devices))

if no_of_devices < 1:
    print("Please check your wiring and try again.")
    sys.exit()

w1_device_list = []

for device in w1_devices:
    if not ('w1_bus' in device):
        # create string for calling each device and append to list
        this_device = "/sys/bus/w1/devices/" + device + "/w1_slave"
        w1_device_list.append(this_device)

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
            msgline = temperature
            printlog(msgline)
            client.loop(timeout=1.0, max_packets=1)
            time.sleep(delay)
    	
except KeyboardInterrupt:
	printlog("Exiting after Ctrl-C")
	
except:
	printlog("Unexpected fault occurred in main loop")
	
finally:
	GPIO.cleanup()     # this ensures a clean exit	


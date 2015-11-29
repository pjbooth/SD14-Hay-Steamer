# SD14-Hay-Steamer V3
IOT sensor for Hay Steamer
Contains:

SD14Main.py	runs in the Raspberry, connects to IOTF via MQTT and to ThingSpeak via http, monitors and publishes temperature to ThingSpeak, allows remote MQ commands to switch power on and off, automatically cuts power to steamer when target temperature is reached.
NodeRed.txt	export of the Node Red program which runs in an IBM Bluemix Node Red server, connected via IOTF to the Raspberry Pi. 
		It also serves a web page, updated via WS with the current temperature, so users can watch via browser.
pjbiotmaster.py	A management program which runs on the Raspberry Pi, monitors the CPU stats, allow remote commands to quit running app program, to reboot, to shutdown [and perhaps other limited, screened commands]

# SD14-Hay-Steamer V3.2
IOT sensor for Hay Steamer
Contains:

SD14Main.py	runs in the Raspberry, connects to IOTF via MQTT, monitors temperature, allows remote commands to switch power on and off, automatically cuts power to steamer when target temperature is reached.
NodeRed.txt	export of the Node Red program which runs in an IBM Bluemix Node Red server, connected via IOTF to the Raspberry Pi. 
		It also serves a web page, updated via WS with the current temperature, so users can watch via browser.

V3.2 adds a safety cutout if the steamer appears to be steaming too long without completing

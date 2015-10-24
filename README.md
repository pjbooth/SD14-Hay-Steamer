# SD14-Hay-Steamer
IOT sensor for Hay Steamer
Contains:

SD14Main.py	runs in the Raspberry, connects to IOTF via MQTT
NodeRed.txt	export of the Node Red program which runs in an IBM Bluemix Node Red server, connected via IOTF to the Raspberry Pi. 
		It also serves a web page, updated via WS with the current temperature, so users can watch via browser.

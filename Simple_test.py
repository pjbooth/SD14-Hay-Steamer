####--------------------------------------------------------
#### Name:            SendLocalIP.py
#### Programmer:      Paul Booth, based on work by Tony Tosi
#### Created:         03/10/2015
#### Purpose:         Monitor temperature, switch off steamer when ready
####--------------------------------------------------------
import time
import commands
import re
import smtplib

####--[CONFIGURATION]
server = 'smtp.gmail.com' #smtp server address
server_port = '587' #port for smtp erver

username = 'pjb.rpi@gmail.com' #gmail account
password = 'gmailpass9' #password for that gmail account

fromaddr = 'pjb.rpi@gmail.com' #address to send from
toaddr = 'paulbooth46@gmail.com' #address to send IP to
message = 'RPi SD14 Hay Steamer is up and running the main program' #message that is sent
####--[/CONFIGURATION]

headers = ["From: " + fromaddr,
           "To: " + toaddr,
           "MIME-Version: 1.0",
           "Content-Type: text/html"]
headers = "\r\n".join(headers)

server = smtplib.SMTP(server + ':' + server_port)  
server.ehlo()
server.starttls()  
server.ehlo()
server.login(username, password)  
server.sendmail(fromaddr, toaddr, headers + "\r\n\r\n" +  message)  
server.quit()
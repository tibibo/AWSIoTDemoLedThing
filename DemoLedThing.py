#!/usr/bin/env python

import logging
import logging.handlers
import argparse
import sys
import time  

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import json
import os
import ssl
import RPi.GPIO as GPIO

# Deafults
LOG_FILENAME = "/home/pi/DemoLedThing/log/Device.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"


parser = argparse.ArgumentParser(description="My simple Python service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

args = parser.parse_args()
if args.log:
        LOG_FILENAME = args.log



logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class MyLogger(object):
        def __init__(self, logger, level):
                self.logger = logger
                self.level = level

        def write(self, message):
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())


sys.stdout = MyLogger(logger, logging.INFO)
sys.stderr = MyLogger(logger, logging.ERROR)



# These are my AWS IoT login and certificates
host = "a2fo0j0u55vbhj.iot.eu-central-1.amazonaws.com"
cert_path = os.path.realpath(__file__).rstrip(os.path.basename(__file__)) + "cert/"
rootCAPath = cert_path + "root-CA.crt"
certificatePath = cert_path + "f84fba1380-certificate.pem.crt"
privateKeyPath = cert_path + "f84fba1380-private.pem.key"
shadowClient = "DemoLedThing"



Led_Status = ["False", "True"]

Base_Led_Power = 18


def IoT_to_Raspberry_Change_Led(ShadowPayload):
    global Base_Led_Power
    
    shadowDict = {'state': { \
                        'desired': { \
                                'led': 'False' \
                                }, \
                        'reported': { \
                                'led': 'False' \
                                } \
                            } \
                }

    if ShadowPayload in Led_Status:

        if (ShadowPayload == "True"):
            
            GPIO.output(Base_Led_Power, GPIO.HIGH) 
            time.sleep(0.1)            

        else:
            
            GPIO.output(Base_Led_Power, GPIO.LOW)


        shadowDict['state']['desired']['led'] = ShadowPayload
        shadowDict['state']['reported']['led'] = ShadowPayload
        JSONPayload = json.dumps(shadowDict)
        print("IoT_to_Raspberry_Change_Led JSONPayload - " + JSONPayload)
        myDeviceShadow.shadowUpdate(JSONPayload, IoTShadowCallback_Update, 5) #Send the new status as REPORTED values


    
# Shadow callback for when a DELTA is received (this happens when Lamda does set a DESIRED value in IoT)
def IoTShadowCallback_Delta(payload, responseStatus, token):
    payloadDict = json.loads(payload)
    if ("led" in payloadDict["state"]):
        IoT_to_Raspberry_Change_Led(str(payloadDict["state"]["led"]))



# Shadow callback GET for setting initial status
def IoTShadowCallback_Get(payload, responseStatus, token):
    payloadDict = json.loads(payload)
    if ("led" in payloadDict["state"]["desired"]):
        IoT_to_Raspberry_Change_Led(str(payloadDict["state"]["desired"]["led"]))



# Shadow callback for updating the AWS IoT
def IoTShadowCallback_Update(payload, responseStatus, token):
   print("IoTShadowCallback_Update responseStatus " + responseStatus + " token " + token)





# Init AWSIoTMQTTShadowClient
myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(shadowClient)
myAWSIoTMQTTShadowClient.configureEndpoint(host, 8883)
myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTShadowClient configuration
myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT
myAWSIoTMQTTShadowClient.connect()

# Create a deviceShadow with persistent subscription
myDeviceShadow = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(shadowClient, True)


#Now start setting up all GPIO required things like the PINs, and the interrupts
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(Base_Led_Power, GPIO.OUT)
GPIO.output(Base_Led_Power, GPIO.LOW)

myDeviceShadow.shadowGet(IoTShadowCallback_Get, 5)


time.sleep(1)



def loop():
	time.sleep(1)


# Listen on deltas from the IoT Shadow
myDeviceShadow.shadowGet(IoTShadowCallback_Get, 5)
myDeviceShadow.shadowRegisterDeltaCallback(IoTShadowCallback_Delta)

if __name__ == '__main__':
    try:
        print '\n DemoLed started, Press Ctrl-C to quit.'
        while True:
            #pass
            loop()
    finally:
        GPIO.cleanup()
        myDeviceShadow.shadowUnregisterDeltaCallback()
        myAWSIoTMQTTShadowClient.disconnect()
        print 'DemoLed stopped.\n'

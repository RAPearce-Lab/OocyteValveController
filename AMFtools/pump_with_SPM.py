# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : get_all_data.py
# Package : AMFTools example
# Description : This module provide an example of how to pump with an AMF SPM product
# Author : Paul Giroux - AMF
# Date Created : November 07, 2023
# Date Modified : September 10, 2024
# Version : 1.0.0
# Python Version : 3.11.4
# Dependencies : pyserial, ftd2xx
# License : all Right reserved : Proprietary license (Advanced Microfluidics S.A.)
#*******************************************************************************

import amfTools # import the module
import time

COM_port = 'COM45'      # (optional) COM port of the product, needs to be changed before using it

list_amf = amfTools.util.getProductList() # get the list of AMF products connected to the computer
print("\n******* List of AMF products connected to the computer *******")
for amf in list_amf:
    print(amf)
print("**************************************************************\n")

# Connect to the first AMF product that is an SPM of the list
product : amfTools.Device = None
amf : amfTools.AMF = None
for product in list_amf:
    if product.deviceType == "SPM":
        amf = amfTools.AMF(product)
        break
    
if amf is None:
    print("No SPM product found")
    print("Force connection to port " + COM_port)
    try:
        amf = amfTools.AMF(COM_port)
    except Exception as e:
        raise ConnectionError(str(e))

# check if the product is homed (if not, home it)
if not amf.getHomeStatus():
    amf.home() # home the product

#set the pump parameters
amf.setAccelerationRate(1557) # set the aceleration rate to 1557 pulse/s^2
amf.setDecelerationRate(59590) # set the deceleration rate to 59590 pulse/s^2
amf.setSpeed(150) # set the speed to 150 pulse/s
amf.setSyringeSize(1000) # set the syringe size to 1000 µL (1 mL)

# Move the valve to port 3
amf.valveMove(3)

# Pump to 1500 (half of the full stroke)
print("Pickup from port 3")
amf.pump(1500)
time.sleep(1)

# Move the valve to port 1
amf.valveMove(1)

# Pump dispense 500 (go to 1000 in absolute position)
print("Dispense on port 1")
amf.pumpDispense(500)
time.sleep(1)
amf.valveMove(6)

# Pump pickup 1000 (go to 2000 in absolute position)
print("Pickup from port 6")
amf.pumpPickup(1000)
time.sleep(1)
amf.valveMove(1)

# Pump dispense 500 µL (1/2 of 1ml => 1/2 of the syringe size ~ dispense 1/2 of the full stroke = 1500)
print("Dispense on port 1")
amf.pumpDispenseVolume(500)
time.sleep(1) 

# Move the valve to port 3
amf.valveMove(3)

# Pump pickup 750 µL
print("Pickup from port 3")
amf.pumpPickupVolume(750) 
time.sleep(1)
amf.valveMove(1)

# Pump to 0 (go to 0 in absolute position)
print("Dispense on port 1")
amf.pump(0)

print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")






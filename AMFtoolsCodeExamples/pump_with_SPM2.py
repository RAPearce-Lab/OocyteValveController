# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : pump_with_SPM.py
# Package : AMFTools example
# Description : This module provide an example of how to pump with an AMF SPM product
# Author : Paul Giroux - AMF
# Date Created : November 07, 2023
# Date Modified : October 23, 2025
# Python Version : 3.11.4
# AMFTools Version: 0.1.10
# License : all Right reserved : Proprietary license (Advanced Microfluidics S.A.)
#*******************************************************************************

import amfTools
import time

list_amf = amfTools.util.getProductList() # Get the list of AMF products connected to the computer
print("\n******* List of AMF products connected to the computer *******")
for amf in list_amf:
    print(amf)
print("**************************************************************\n")

pump : amfTools.AMF = None

try:
    # Connect to the first AMF product of the list that is a pump
    for product in list_amf:
        if product.deviceFamily == "Pump":
            pump = amfTools.AMF(product)
            break           
    if pump is None:
        raise ConnectionAbortedError("No AMF pump connected to the computer. Please check your connections")
        
    print(f"Connected to product {pump.getType()} on port {pump.getSerialPort()}\n")
    
    # Check if the product is homed (if not, home it)
    if not pump.getHomeStatus():
        pump.home()
    
    # Set the pump parameters
    pump.setAccelerationRate(5000) # Set the aceleration rate to 5000 step/s^2
    pump.setSpeed(250) # Set the speed to 250 pulse/s
    pump.setSyringeSize(1000) # Set the syringe size to 1000 µL (1 mL)
    pump.pumpAbsolutePosition(0) # Empty the syringe
    
    # Move the valve to port 3
    pump.valveMove(3)
    
    # Pump to 1500 (half of the full stroke)
    print("Pickup from port 3")
    pump.pumpAbsolutePosition(1500)
    time.sleep(1)
    
    # Move the valve to port 1
    pump.valveMove(1)
    
    # Pump dispense 500 (go to 1000 in absolute position)
    print("Dispense on port 1")
    pump.pumpDispense(500)
    time.sleep(1)
    pump.valveMove(6)
    
    # Pump pickup 1000 (go to 2000 in absolute position)
    print("Pickup from port 6")
    pump.pumpPickup(1000)
    time.sleep(1)
    pump.valveMove(1)
    
    # Pump dispense 500 µL (1/2 of 1ml => 1/2 of the syringe size ~ dispense 1/2 of the full stroke = 1500)
    print("Dispense on port 1")
    pump.pumpDispenseVolume(500)
    time.sleep(1) 
    
    # Move the valve to port 3
    pump.valveMove(3)
    
    # Pump pickup 750 µL
    print("Pickup from port 3")
    pump.pumpPickupVolume(750) 
    time.sleep(1)
    pump.valveMove(1)
    
    # Pump to 0 (go to 0 in absolute position)
    print("Dispense on port 1")
    pump.pump(0)

finally : 
    if pump:
        pump.disconnect()
    
print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")
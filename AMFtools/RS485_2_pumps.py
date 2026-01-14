# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : RS485_2_pumps.py
# Package : AMFTools example
# Description : This module provide an example of how to use AMFTools with RS485 communication
# Author : Matthieu Gevers - AMF
# Date Created : October 23, 2025
# Date Modified : October 23, 2025
# Python Version : 3.11.4
# AMFTools Version: 0.1.10
# License : all Right reserved : Proprietary license (Advanced Microfluidics S.A.)
#*******************************************************************************

import amfTools

""" 
This code is made to communicate with 2 pumps using RS485 communication. 
The 2 pumps should be configured in RS485 mode and should not have the same address for this code to work.
The 2 pumps should be connected on the same RS485 bus.
To set a pump in RS485 mode, connect it with a USB mini cable and use the setRS485Mode() function.
"""

list_amf = amfTools.util.getProductList("RS485", product_family="Pump") # Get the list of AMF pumps connected to the computer by RS485
print("\n******* List of AMF pumps connected to the computer by RS485 *******")
for amf in list_amf:
    print(amf)
print("**************************************************************\n")

pump_1 : amfTools.AMF = None
pump_2 : amfTools.AMF = None
pumps_broadcast : amfTools.AMF = None

try:
    for pump in list_amf:
        # We look for the 1st pump
        if pump_1 is None and pump.deviceFamily == "Pump":
            pump_1 = amfTools.AMF(pump)
        # We look for the 2nd pump and we check that they share the same serial port
        elif pump_1 is not None and pump.deviceFamily == "Pump" and pump_1.getSerialPort() == pump.comPort:
            pump_2 = amfTools.AMF(pump)
            break
        
    if pump_2 is None:
        raise ConnectionAbortedError("Unable to find 2 pumps on the same RS485 bus. Please check your connections")
            
    # We create a 3rd AMF object that we will use to send RS485 broadcast commands
    # We use the serial port of the 1st pump and we specify RS485 connection with broadcast address "_"
    # We specify that the product is an SPM so we can use all the pump functions
    pumps_broadcast = amfTools.AMF(pump_1.getSerialPort(), connectionMode="RS485", productAddress="_", typeProduct="SPM")
    
    # Check if the pumps are homed and home them sequentially if needed
    if not pump_1.getHomeStatus():
        pump_1.home()
    if not pump_2.getHomeStatus():
        pump_2.home()
        
    # Start a simultaneous pickup with broadcast command
    pumps_broadcast.pumpAbsolutePosition(1500)
    print("Starting a simultaneous pickup on both pumps")
    
    # Wait for the 2 pumps to finish their move
    pump_1.pullAndWait()
    pump_2.pullAndWait()
    
    # Start a sequential dispense
    print("Starting a sequential dispense")
    pump_1.pumpAbsolutePosition(0)
    pump_2.pumpAbsolutePosition(0)
    
finally:
    if pump_1:
        pump_1.disconnect()
    if pump_2:
        pump_2.disconnect()
    if pumps_broadcast:
        pumps_broadcast.disconnect()
    
print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")
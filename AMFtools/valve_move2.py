# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : valve_move.py
# Package : AMFTools example
# Description : This module provide an example of how to move an RVM
# Author : Matthieu Gevers - AMF
# Date Created : August 23, 2024
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

amf : amfTools.AMF = None

try:
    if len(list_amf) < 1:
        raise ConnectionAbortedError("No AMF product connected to the computer. Please check your connections")
        
    # Connect to the first AMF product of the list
    amf = amfTools.AMF(list_amf[0])        
    
    print(f"Connected to product {amf.getType()} on port {amf.getSerialPort()}\n")
    
    # Check if the product is homed (if not, home it)
    if not amf.getHomeStatus():
        amf.home()
    
    # Move to the port 2, wait 3 seconds and move to the port 4
    amf.valveShortestPath(2) # Blocking function, will return only once the move is done
    print("Valve on port 2")
    time.sleep(3)
    amf.valveShortestPath(4) 
    
    print(f"Valve on port {amf.getValvePosition()}")
    
    # Move to the port 3
    amf.valveShortestPath(3, block= False)  # Non blocking function
    # Wait until the move is done
    amf.pullAndWait()
    print("Valve on port 3")
    print(f"Valve Status: {amf.checkValveStatus()}")
    
finally:
    if amf:
        amf.disconnect()
    
print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")
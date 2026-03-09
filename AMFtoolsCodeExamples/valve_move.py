# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : get_all_data.py
# Package : AMFTools example
# Description : This module provide an example of how to move an RVM
# Author : Matthieu Gevers - AMF
# Date Created : August 23, 2024
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

# Connect to the first AMF product that is an RVM of the list
product : amfTools.Device = None
rvm : amfTools.AMF = None
for product in list_amf:
    if "RVM" in product.deviceType :
        rvm = amfTools.AMF(product)
        break
    
if rvm is None:
    print("No RVM product found")
    print("Force connection to port " + COM_port)
    try:
        rvm = amfTools.AMF(COM_port)
    except Exception as e:
        raise ConnectionError(str(e))

# Check if the product is homed (if not, home it)
if not rvm.getHomeStatus():
    rvm.home() # home the product
    time.sleep(2)

# move to the port 2, wait 3 seconds and move to the port 4
rvm.valveShortestPath(2) # blocking function, will return only once the move is done
print("Valve on port 2")
time.sleep(3)
rvm.valveShortestPath(4) 
print("Valve on port 4")
time.sleep(3)

# move to the port 3, wait 3 seconds and move to the port 5
rvm.valveShortestPath(3, block= False)  # non blocking function

valvebusy= True
while valvebusy:                        # wait for the valve to perfom the move
    time.sleep(0.1)
    response = rvm.checkValveStatus()
    if response[0] == 0:
        valvebusy = False
    elif response[0] != 255:
        raise Exception("Valve error : "+str(response[1]+" : "+response[2]))
    else:
        valvebusy = True

print("Valve on port 3")
time.sleep(3)                           # wait 3 seconds
rvm.valveShortestPath(5)                # blocking function
print("Valve on port 5")

print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")


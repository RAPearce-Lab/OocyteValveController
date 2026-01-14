# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : get_all_data.py
# Package : AMFTools example
# Description : This module provide an example of how to get all the data from an AMF product
# Author : Paul Giroux - AMF
# Date Created : November 07, 2023
# Date Modified : October 23, 2025
# Python Version : 3.11.4
# AMFTools Version: 0.1.10
# License : all Right reserved : Proprietary license (Advanced Microfluidics S.A.)
#*******************************************************************************

import amfTools


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
    
    # Get the data from the AMF product
    data = amf.getDeviceInformation(full=True)
    print("\n***************** Data from the AMF product ******************")
    for i in data:
        print(i, " : ", data[i]) # print the data from the AMF product
    print("**************************************************************")

finally :
    if amf:
        amf.disconnect()

print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")
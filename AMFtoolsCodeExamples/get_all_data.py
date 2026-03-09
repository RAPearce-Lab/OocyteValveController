# !/usr/bin/env python3
# -*- coding: utf-8 -*-

#*******************************************************************************
# File : get_all_data.py
# Package : AMFTools example
# Description : This module provide an example of how to get all the data from an AMF product
# Author : Paul Giroux - AMF
# Date Created : November 07, 2023
# Date Modified : August 23, 2024
# Version : 1.0.0
# Python Version : 3.11.4
# Dependencies : pyserial, ftd2xx
# License : all Right reserved : Proprietary license (Advanced Microfluidics S.A.)
#*******************************************************************************

import amfTools # import the module

COM_port = 'COM45'      # (optional) COM port of the product, needs to be changed before using it

list_amf = amfTools.util.getProductList() # get the list of AMF products connected to the computer
print("\n******* List of AMF products connected to the computer *******")
for amf in list_amf:
    print(amf)
print("**************************************************************\n")

# Connect to the first AMF product of the list
if len(list_amf) != 0: 
    amf = amfTools.AMF(list_amf[0])
else:
    print("No AMF product connected to the computer")
    print("Force connection to port " + COM_port)
    try:
        amf = amfTools.AMF(COM_port)
    except Exception as e:
        raise ConnectionError(str(e))

# Get the data from the AMF product
data = amf.getDeviceInformation()
print("\n***************** Data from the AMF product ******************")
for i in data:
    print(i, " : ", data[i]) # print the data from the AMF product
print("**************************************************************")

print("\n**************************************************************")
print("********************* End of the program *********************")
print("**************************************************************\n")



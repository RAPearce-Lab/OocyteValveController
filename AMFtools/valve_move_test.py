
# File : valve_move_test.py
# Package : 
# Description : 
# Author :
# Date Created : 
# Date Modified : 
# Python Version : 
# AMFTools Version: 0.1.10
# License : 
#*******************************************************************************

from amfValveControl import amfValveControl
vc = amfValveControl()

vc.setValvePort('A', 1)
vc.setValvePort('B', 4)
vc.setValvePort('C', 1)
vc.setValvePort('D', 1)
vc.setValvePort('E', 1)
vc.setValvePort('F', 1)
vc.getAllValves()

vc.setValvePort('A', 1)
vc.setValvePort('B', 2)
vc.setValvePort('C', 1)
vc.setValvePort('D', 1)
vc.setValvePort('E', 1)
vc.setValvePort('F', 1)
vc.getAllValves()

vc.setValvePort('A', 2)
vc.setValvePort('B', 6)
vc.setValvePort('C', 4)
vc.setValvePort('D', 4)
vc.setValvePort('E', 4)
vc.setValvePort('F', 4)
vc.getAllValves()




import amfTools
import time

# config variable
valveCount = 6
# get our list of connected valves
listAmf = amfTools.util.getProductList("USB")
# a quick error check 
if len(listAmf) < valveCount:
    raise ConnectionAbortedError(f"unable to find all {valveCount} valves")
# step through all valves set them to home position
valveList = []
for iValve, dInfo in enumerate(listAmf):
    print(f"Index {iValve}: {dInfo}")
    print(dInfo)
    thisValve = amfTools.AMF(listAmf[iValve])
    valveList.append(thisValve)
    valveList.append(thisValve.getSerialPort())
    thisValve.getHomeStatus()
    print(f"Connected to product {thisValve.getType()} on port {thisValve.getSerialPort()}\n")
    if not thisValve.getHomeStatus():
        thisValve.home()
        time.sleep(0.1) # TODO - how low can this be?
        thisValve.disconnect()
        
        
        
        
from amfValveControl import amfValveControl
vc = amfValveControl()

vc.getAllValves()
vc.setValveHome('A')


vc.getValvePort('A')
vc.setValvePort('A', 2)
vc.getValvePort('A')


vc.getValvePort('B')
vc.setValvePort('B', 2)
vc.getValvePort('B')

vc.getValvePort('C')
vc.setValvePort('C', 2)
vc.getValvePort('C')

vc.getValvePort('D')
vc.setValvePort('D', 2)
vc.getValvePort('D')

vc.getValvePort('E')
vc.setValvePort('E', 2)
vc.getValvePort('E')


vc.getAllValves()









vc.valves
raw_list = vc.getValveList()
vc.setAllValvesHome()


# Valve, serial, COM port (for now), index, 
# A, P201-O00005087, COM6, 2, 
# B, P201-O00005331, COM5, 1, 
# C, P201-O00005333, COM8, 4, 
# D, P201-O00005329, COM9, 5
# E, P201-O00005332, COM4, 0,  
# F, P201-O00005330, COM7, 3
# I learned another weird thing: if you send a .getValvePosition() it will send the state of the valve back before a disconnection, which means if you check the position, then move it, then check the position again, it will report the port information pre-move twice, and only when you send a separate port location request (after the disconnect) will you get the new, updated port....
# valves start at 0 (0:5), ports start at 1 (1:nPorts)
# because the .getValvePosition() quirk above we should double check "home" routing state for the side-by-side valves.
# I think com port might change with reboot, or certainly if anything gets unplugged, so we need to map serial to valve letter

# testing: set the first valve to port 1
iValve = 0
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.valveShortestPath(2, block= False)  # Non blocking function
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()

iValve = 1
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.valveShortestPath(2, block= False)  # Non blocking function
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()

iValve = 2
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.valveShortestPath(2, block= False)  # Non blocking function
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()

iValve = 2
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.home()
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()

iValve = 4
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.valveShortestPath(2, block= False)  # Non blocking function
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()



iValve = 5
thisValve = amfTools.AMF(listAmf[iValve])
thisValve.valveShortestPath(2, block= False)  # Non blocking function
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
time.sleep(0.1) # TODO - how low can this be?
thisValve.disconnect()



iValve = 3
thisValve = amfTools.AMF(listAmf[iValve])
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
thisValve.valveShortestPath(1, block= False)  # Non blocking function
time.sleep(0.1) # TODO - how low can this be?
print(f"Connected to product {thisValve.getType()} set to port: {thisValve.getValvePosition()}\n")
thisValve.disconnect()

        






# Wait until the move is done
# thisValve.pullAndWait()   
# thisValve.getValvePosition() # int
# thisValve.getValveStatus() # int
    
    
    
    
    
    
    
    
    
    
    
    
    
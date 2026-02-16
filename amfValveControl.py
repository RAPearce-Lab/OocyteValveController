import amfTools
import json
import os
import time

class amfValveControl:
    def __init__(self,status_callback=None):
        self.status_callback = status_callback
        self.log("Initializing Hardware...")
        configFile = "valve_config.json" 
        # 1 get the list of connected valves
        self.valveList = self.getValveList()
        # print("1. Connected valves discovered.")
        self.log("1. Connected valves discovered.")
        # 2. load a valve configuration (serial# to letter association)
        self.serialMap = {}
        self.loadConfig(configFile)
        # print("2. Valve map loaded.")
        self.log("2. Valve map loaded.")
        # 3. be sure all valves are present
        theseSerials = {v.serialnumber for v in self.valveList}
        expectedSerials = set(self.serialMap.values())
        if theseSerials != expectedSerials:
            missingValves = expectedSerials - theseSerials
            raise RuntimeError(f"unable to find valve: {missingValves}")
        # print("3. All valves confirmed.")
        self.log("3. All valves confirmed.")
        # 4. associate the letters with the serial number and object
        self.initializeValves(self.valveList)
        # print("4. Letter mapping to hardware completed.")
        self.log("4. Letter mapping to hardware completed.")
        # 5. home all valves 
        self.setAllValvesHome()
        # print("5. All valves homed.")
        self.log("5. All valves homed.")
    def loadConfig(self,configFile):
        thisFolder = os.path.dirname(__file__)
        configFilePath = os.path.join(thisFolder,configFile)
        try:
            with open(configFilePath, 'r') as f:
                loadedConfig = json.load(f)
            self.serialMap= {label: data['sn'] for label, data in loadedConfig.items()}
            self.portCounts = {label: data['ports'] for label, data in loadedConfig.items()}
        except Exception as e:
            print(f"I couldn't load {e}")
    def initializeValves(self, valveList):
        self.valves = {}
        for label, sn in self.serialMap.items():
            for hardware in valveList:
                if hardware.serialnumber == sn:
                    self.valves[label] = hardware
        if len(self.valves) != len(self.serialMap):
            raise RuntimeError("unable to initialize valves!")
    def log(self, message):
        print(message)
        if self.status_callback:
            self.status_callback(message)

    @staticmethod
    def getValveList():
        return amfTools.util.getProductList("USB")
    def setValveHome(self, valveID):
        thisValve = amfTools.AMF(self.valves.get(valveID))
        if not thisValve.getHomeStatus():
            self.log(f"Homing Valve {valveID}.")
            thisValve.home()
            time.sleep(0.01) # 10ms is usually a very safe minimum (according to google. test?)
        else:
            self.log(f"{valveID} already home.")    
        thisValve.disconnect()
    def setAllValvesHome(self):
        for label in self.valves:
            # print(f"Homing Valve {label}.")
            # self.log(f"Homing Valve {label}.")
            self.setValveHome(label)
    def setValvePort(self, valveID, portID):
        thisValve = amfTools.AMF(self.valves.get(valveID))
        thisValve.valveShortestPath(portID, block= False)  # Non blocking function
        time.sleep(0.01)
        self.log(f"moving valve: {valveID} to port {portID}.")
        thisValve.disconnect()
    def getValvePort(self, valveID):
        thisValve = amfTools.AMF(self.valves.get(valveID))
        portOut = thisValve.getValvePosition()
        time.sleep(0.01)
        thisValve.disconnect()
        return portOut
    def getAllValves(self):
        for label in self.valves:
            # print(f"Valve: {label} at port {self.getValvePort(label)}.")
            self.log(f"Valve: {label} at port {self.getValvePort(label)}.")


# # --- DLL Handling ---
# # We had some issues with python finding the appropriate .dll file.  Here is a 
# # hardcoded file location - path to the actual dll folder with FTD2XX64.dll
# # TODO move this dll_path to a config file, or suffer the stupid git updates from each user / location that could break any other user's build
# # more notes: need the amfTools here: https://pypi.org/project/AMFTools/  and 
# # one dependancy is here: https://ftdichip.com/drivers/d2xx-drivers/
# # TODO create an "install" file writeup
# DLL_PATH = r'C:\Windows\System32\DriverStore\FileRepository\ftdibus.inf_amd64_6d7e924c4fdd3111\amd64' 
# try:
#     os.add_dll_directory(DLL_PATH)
#     import amfTools as AMF
#     HARDWARE_CONNECTED = True
# except Exception as e:
#     print(f"Hardware library load failed (Entering Simulation Mode): {e}")
#     HARDWARE_CONNECTED = False
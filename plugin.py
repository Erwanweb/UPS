"""
CASA-IA UPS Monitoring plugin for Domoticz
Author: Erwanweb,
Version:    0.0.1: alpha
            0.0.2: beta
            1.1.1: validate

"""
"""
<plugin key="UPS" name="AC UPS Monitoring" author="Erwanweb" version="1.1.1" externallink="https://github.com/Erwanweb/UPS.git">
    <description>
        <h2>Casa.ia UPS Monitoring Plugin</h2><br/>
        Easily Monitor Casa.ia UPS<br/>
        <h3>Set-up and Configuration</h3>
    </description>
    <params>
        <param field="Mode6" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal"  default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import urllib.parse as parse
import urllib.request as request
from datetime import datetime, timedelta
import time
import base64
import itertools
import os
import subprocess as sp
from distutils.version import LooseVersion

class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue


class BasePlugin:

    def __init__(self):

        self.debug = False
        self.PowerSupply = False
        self.BatteryCharging = False
        self.BatteryLevel = 0
        self.LastBatteryLevel = 100
        self.VOLTAGE = 0
        self.CURRENT = 0
        self.POWER = 0
        self.PERCENT = 0
        self.TIMEMIN = 0
        self.TIMESEC = 0
        self.CalcTime = 86400
        self.HourofTR = 24
        self.MinofTR = 59
        self.LastBattUpdate = datetime.now() - timedelta(seconds=1200)
        self.LastIC2Reading = datetime.now()
        self.statussupported = True
        return


    def onStart(self):

        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode6"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode6"]
        if debuglevel != 0:
            self.debug = True
            Domoticz.Debugging(debuglevel)
            DumpConfigToLog()
            self.loglevel = "Verbose"
        else:
            self.debug = False
            Domoticz.Debugging(0)

        # create the child devices if these do not exist yet
        devicecreated = []
        if 1 not in Devices:
            Domoticz.Device(Name="Power supply", Unit=1, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(1, 0, ""))  # default is Off
        if 2 not in Devices:
            Domoticz.Device(Name="Charger", Unit=2, TypeName="Alert", Used=1).Create()
            devicecreated.append(deviceparam(2, 0, ""))  # default is charged
        if 3 not in Devices:
            Domoticz.Device(Name="Battery Level", Unit=3, Type=243, Subtype=6, Used=1).Create()
            devicecreated.append(deviceparam(3, 0, ""))  # default is 0

        #if any device has been created in onStart(), now is time to update its defaults
        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

    def onStop(self):

        Domoticz.Debugging(0)


    def onCommand(self, Unit, Command, Level, Color):

        now = datetime.now()
        #self.onHeartbeat()


    def onHeartbeat(self):

        Domoticz.Debug("onHeartbeat Called...")
        # fool proof checking....
        if not all(device in Devices for device in (1,2,3)):
            Domoticz.Error("one or more devices required by the plugin is/are missing, please check domoticz device creation settings and restart !")
            return

        now = datetime.now()

        #cmd = 'sudo python3 /home/pi/domoticz/plugins/UPS/readups.py short'
        cmd = 'sudo python3 /home/domoticz/plugins/UPS/readups.py short'
        output = sp.getoutput(cmd)
        os.system(cmd)
        Domoticz.Debug("Ic2 Info : {}".format(output))
        UPSReadedValues = parseCSV(output)
        if len(UPSReadedValues) == 4:
            self.LastIC2Reading = datetime.now()
            self.VOLTAGE = CheckParam("UPS Voltage", UPSReadedValues[0], 0)
            self.CURRENT = CheckParam("UPS Current", UPSReadedValues[1], 0)
            self.POWER = CheckParam("UPS Power", UPSReadedValues[2], 0)
            self.PERCENT = CheckParam("UPS Battery Level", UPSReadedValues[3], 0)
            # self.TIMEMIN = round(((3350 / ((self.POWER / 10.1) / 0.8)) * (self.PERCENT / 100)) * 60)
            self.TIMEMIN = round(((3350 / (0 - power) * 0.8)) * (percent / 100)) * 60)
            Domoticz.Debug("UPS Values are : Voltage {} mV, Current {} mA, Power {} mW, Battery Level {} %, Calc. remaining time on batt. is {} minutes".format(self.VOLTAGE, self.CURRENT, self.POWER, self.PERCENT, self.TIMEMIN))
            self.TIMESEC = self.TIMEMIN * 60
        else:
            #Domoticz.Error("Error reading UPS Values on Ic2")
            if self.LastIC2Reading + timedelta(seconds=80) <= now:
                Domoticz.Error("Error reading UPS Values on Ic2 since more than 3 times !")
                Devices[1].Update(nValue=0, sValue=Devices[1].sValue)
                Devices[2].Update(nValue=0, sValue="Undefined")
                Devices[3].Update(nValue=0, sValue="0")

        if self.LastBattUpdate + timedelta(seconds=60) <= now:
            Devices[3].Update(nValue=self.PERCENT, sValue=str(self.PERCENT))
            self.BatteryLevel = self.PERCENT
            self.LastBattUpdate = datetime.now()
        
        if self.CURRENT >= -150:
            Domoticz.Debug("Power supply On")
            if (Devices[1].nValue == 0):
                Devices[1].Update(nValue=1, sValue=Devices[1].sValue)
            self.PowerSupply = True
            if self.PERCENT >= 99:
                Domoticz.Debug("Battery Charged")
                Devices[2].Update(nValue=1, sValue="Power supply OK - Battery fully charged")
                Domoticz.Log("Power supply is OK, Battery is full")
            else :
                Domoticz.Debug("Battery Charging")
                if self.BatteryLevel > 0:
                    Domoticz.Log("Power supply is OK, Battery is charging, Battery Level is now at {} %".format(self.BatteryLevel))
                    Devices[2].Update(nValue=2, sValue="Power supply OK - Battery charging - now at {} %".format(self.BatteryLevel))
                    self.LastBatteryLevel = self.BatteryLevel
                else :
                    Domoticz.Log("Power supply is OK, Battery is charging, Battery Level is undefined - Please wait for calculation")
                    Devices[2].Update(nValue=2, sValue="Power supply OK - Battery charging - Level is undefined, wait for calculation")
        else :
            Domoticz.Debug("Power supply Off")
            if (Devices[1].nValue == 1): #Power supply just done, so we change the DZ Widget and calculate the remaining time on battery.
                Devices[1].Update(nValue=0, sValue=Devices[1].sValue)
                self.LastBatteryLevel = self.BatteryLevel
                self.CalcTime = self.TIMESEC
                self.HourofTR = time.strftime("%H", time.gmtime(self.CalcTime))
                self.MinofTR = time.strftime("%M", time.gmtime(self.CalcTime))
                Domoticz.Log("Power supply just cuted - Batt: {} % - Rem. time on Battery is : {} H {} Mins".format(self.BatteryLevel, self.HourofTR, self.MinofTR))
                Devices[2].Update(nValue=4, sValue="Power supply just cuted - Batt: {} %".format(self.BatteryLevel))
            self.PowerSupply = False
            Domoticz.Debug("Battery Dicharging")
            if self.BatteryLevel > 0:
                Domoticz.Log("Power Failure, Battery is discharging, Battery Level is now at {} %".format(self.BatteryLevel))
                if self.LastBatteryLevel > self.BatteryLevel : #or (self.LastBatteryLevel = 0) :
                    self.LastBatteryLevel = self.BatteryLevel
                    Domoticz.Debug("PS DOWN, Battery  is now at {} %".format(self.BatteryLevel))
                    if self.CalcTime > self.TIMESEC : # or self.CalcTime = 0 :
                        self.CalcTime = self.TIMESEC
                        self.HourofTR = time.strftime("%H", time.gmtime(self.CalcTime))
                        self.MinofTR = time.strftime("%M", time.gmtime(self.CalcTime))
                        Domoticz.Debug("Remaining time if working on Battery is : {} H {} Mins".format(self.HourofTR, self.MinofTR))
                    if self.CalcTime > 3540 :
                        Devices[2].Update(nValue=4, sValue="Power Failure - Batt: {} % - {} H {} Mins".format(self.BatteryLevel, self.HourofTR, self.MinofTR))
                    else :
                        Devices[2].Update(nValue=4, sValue="Power Failure - Batt: {} % - {} Mins".format(self.BatteryLevel, self.MinofTR))
            else:
                Domoticz.Log("Power Failure - Battery is discharging and very low level")
                Devices[2].Update(nValue=4, sValue="Power Failure - Very Low Batt. Level")


    def WriteLog(self, message, level="Normal"):

        if self.loglevel == "Verbose" and level == "Verbose":
            Domoticz.Log(message)
        elif level == "Normal":
            Domoticz.Log(message)



global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Plugin utility functions ---------------------------------------------------

def parseCSV(strCSV):
    listvals = []
    for value in strCSV.split(","):
        try:
            val = int(value)
        except:
            pass
        else:
            listvals.append(val)
    return listvals

def CheckParam(name, value, default):
    try:
        param = int(value)
    except ValueError:
        param = default
        Domoticz.Error("Readed '{}' has an invalid value of '{}' ! defaut of '{}' is instead used.".format(name, value, default))
    return param

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

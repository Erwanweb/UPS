#import smbus -- for python <=3.8
from smbus2 import SMBus
import time
import sys
from ina219 import INA219

class PowerFormatting:
    FULL    = 0x01
    SHORT   = 0x02
    PERCENT = 0x03
    CURRENT = 0x04
    #TIME = 0x05

def read(ina219, parameter):

    voltage = ina219.getBusVoltage_V()             # voltage on V- (load side) in V
    shunt_voltage = ina219.getShuntVoltage_mV() / 1000 # voltage between V+ and V- across the shunt
    current = ina219.getCurrent_mA()         # current in mA
    power = ina219.getPower_W() * 1000               # power in mW
    voltage_batt = ina219.getBusVoltage_V() * 1000 # voltage on V- (load side) in mV
    # For UPS HAT (c)
    # percent = (bus_voltage - 6)/2.4*100 # Base calc from WS with 2x 18650 batteries 2600mAh
    # Optimized for 2x 18650 batteries 3350 mAH
    if (voltage_batt >= 8000): percent = (voltage - 6) / 2.15 * 100
    elif (voltage_batt < 8000) and (voltage_batt >= 7800): percent = (voltage - 6) / 2.20 * 100  #
    elif (voltage_batt < 7800) and (voltage_batt >= 7600): percent = (voltage - 6) / 2.25 * 100  #
    elif (voltage_batt < 7600) and (voltage_batt >= 7400): percent = (voltage - 6) / 2.3 * 100  #
    elif (voltage_batt < 7400) and (voltage_batt >= 7200): percent = (voltage - 6) / 2.35 * 100  #
    else: percent = (voltage - 6) / 2.4 * 100
    # For UPS 3S full = 12.5, empty 10.1
    #if (voltage_batt >= 12500): percent = 100 # base percent = (voltage - 9) / 3.6
    #else : percent = ((voltage - 9) - 1.1) / 0.025
    # For all UPS Models :
    if (current < -100):
        if (percent >= 100):
            percent = 98
    else :
        if (percent >= 99):
            percent = 100
    if(percent <= 2):percent = 0
    # Time calculation based on 3x3350mAh
    # timemin = ((3350 / ((power / 10.1) / 0.8)) * (percent / 100)) * 60
    timemin = (3350 / (0 - current) ) #* 0.8) * (percent / 100)) * 60
    result = ""
    if(PowerFormatting.FULL == parameter):
        result = printlong(voltage, current, power, percent, timemin)
    elif(PowerFormatting.SHORT == parameter):
        result = printshort(voltage, current, power, percent)
    elif(PowerFormatting.PERCENT == parameter):
        result = "{0}".format(int(percent))
    elif(PowerFormatting.CURRENT == parameter):
        result = "{0}".format(int(current))
    #elif (PowerFormatting.TIME == parameter):
    #    result = "{0}".format(int(time))
    return result

def printlong(voltage, current, power, percent, timemin):
    discharge = ""
    if(current < -100):
        discharge = "dis"
    print("--------------------------------------------------------------")
    print("Load Voltage:\t\t{:6.3f} V".format(voltage))
    print("Battery {0}charging:\t{1:6.2f} mA".format(discharge, current))
    print("Power:\t\t\t{:6.0f} mW".format(power))
    print("Percent:\t\t{:3.2f} %".format(percent))
    if(current < -100):
        print("Remaining time:\t\t{:3.0f} minutes".format(timemin))
    else :
        print("Remaining time: undefined - Power supply on")
    print("--------------------------------------------------------------")
    return ""

def printshort(voltage, current, power, percent):
    return "{0},{1},{2:1.0f},{3}".format(int(voltage*1000), int(current), power, int(percent))

if __name__=='__main__':
    #ina219 = INA219(addr=0x41) #UPS3S
    ina219 = INA219(addr=0x42) #UPSHAT(B)
    read(ina219, 0)
    time.sleep(2)
    if(len(sys.argv) > 1):
        result = ""
        if(sys.argv[1] == "percent"):
            result = read(ina219, PowerFormatting.PERCENT)
        elif(sys.argv[1] == "current"):
            result = read(ina219, PowerFormatting.CURRENT)
        else:
            result = read(ina219, PowerFormatting.SHORT)
        print(result)
    else:
        read(ina219, PowerFormatting.FULL)

import sys
import time 
from Phidget22.Devices.VoltageRatioInput import *
from Phidget22.PhidgetException import *
from Phidget22.Phidget import *
from Phidget22.Net import *
from numpy import mean, polyfit
import serial
import matplotlib.pyplot as plt
import pandas as pd
import os

cwd = os.getcwd()

arduino = serial.Serial('COM7', 9600, timeout=.1)
thickness = float(input('Thickness of the sample (in micrometers): '))*10**(-6)
width = float(input('Width of the sample (in centimeters): '))*10**(-2)
length0 = float(input('Length of the sample (in centimeters): '))*10**(-2)
outfile = input('Name of the output file (without extension): ')

out_csv = cwd+'/'+outfile+'.csv'
out_png = cwd+'/'+outfile+'.png'


try:
    ch = VoltageRatioInput()
except RuntimeError as e:
    print("Runtime Exception %s" % e.details)
    print("Press Enter to Exit...\n")
    readin = sys.stdin.read(1)
    exit(1)


def VoltageRatioInputAttached(e):
    try:
        attached = e
        print("\nAttach Event Detected (Information Below)")
        print("===========================================")
        print("Library Version: %s" % attached.getLibraryVersion())
        print("Serial Number: %d" % attached.getDeviceSerialNumber())
        print("Channel: %d" % attached.getChannel())
        print("Channel Class: %s" % attached.getChannelClass())
        print("Channel Name: %s" % attached.getChannelName())
        print("Device ID: %d" % attached.getDeviceID())
        print("Device Version: %d" % attached.getDeviceVersion())
        print("Device Name: %s" % attached.getDeviceName())
        print("Device Class: %d" % attached.getDeviceClass())
        print("\n")

    except PhidgetException as e:
        print("Phidget Exception %i: %s" % (e.code, e.details))
        print("Press Enter to Exit...\n")
        readin = sys.stdin.read(1)
        exit(1)


def VoltageRatioInputDetached(e):
    detached = e
    try:
        print("\nDetach event on Port %d Channel %d" % (detached.getHubPort(),
              detached.getChannel()))
    except PhidgetException as e:
        print("Phidget Exception %i: %s" % (e.code, e.details))
        print("Press Enter to Exit...\n")
        readin = sys.stdin.read(1)
        exit(1)


def ErrorEvent(e, eCode, description):
    print("Error %i : %s" % (eCode, description))

all_forces_list = []
all_voltrat_list = []
a = 6.94E6
b = -1401.52


def VoltageRatioChangeHandler(e, voltageRatio):
    x = voltageRatio
    weight = a*x+b    # in grams
    force = weight*9.81/1000   # in Newtons
    all_forces_list.append(force)
    all_voltrat_list.append(x)
#    print("Weight: %f %f %f" % (x,weight,force))


def SensorChangeHandler(e, sensorValue, sensorUnit):
    print("Sensor Value: %f" % sensorValue)

try:
    ch.setOnAttachHandler(VoltageRatioInputAttached)
    ch.setOnDetachHandler(VoltageRatioInputDetached)
    ch.setOnErrorHandler(ErrorEvent)
    ch.setOnVoltageRatioChangeHandler(VoltageRatioChangeHandler)
    ch.setOnSensorChangeHandler(SensorChangeHandler)
    print("Waiting for the Phidget VoltageRatioInput Object to be attached...")
    ch.openWaitForAttachment(5000)
except PhidgetException as e:
    print("Phidget Exception %i: %s" % (e.code, e.details))
    print("Press Enter to Exit...\n")
    readin = sys.stdin.read(1)
    exit(1)

force_list = []
voltrat_list = []
# dist_list = []
stress_list = []
strain_list = []
# ymod_list = []

plt.axis()
plt.ion()

plt.xlabel('Strain')
plt.ylabel('Stress/Pa')
plt.title('Stress-strain curve')

def calc_stress(force):
    return force/(width*thickness)  # in N/m2 (Pa)


def calc_strain(leng):
    return (leng-length0)/length0  # unitless


# def calc_ymod(stress, strain):
#     return stress/strain  # in Pa

plt_length_list = []
plt_force_list = []
t = 0
while True:
    data = arduino.readline()[:-2]  # [:-2] to get rid of the new-line chars
    if len((str(data)[2:-1]).split()) == 2:
        line = str(data)[2:-1]
        try:
            length = length0+float(line.split()[0])*10**(-2)
        except ValueError:
            pass
        try:
            stepping = int(line.split()[1])
        except ValueError:
            pass
        if stepping == 1 and all_forces_list[len(all_forces_list)-2] != all_forces_list[len(all_forces_list)-1]:
            t += 1
#            dist_list.append(length)
            force_list.append(all_forces_list[len(all_forces_list)-1])
            voltrat_list.append(all_voltrat_list[len(all_voltrat_list)-1])
            if t % 500 == 0:
#                plt_length_list.append(t/1000)
                plt_length_list.append(length)
                force = all_forces_list[len(all_forces_list)-1]
                plt_force_list.append(force)
                stress_list.append(calc_stress(force))
                strain_list.append(calc_strain(length))
#                ymod_list.append(calc_ymod(calc_stress(force),calc_strain(length)))
                plt.plot(strain_list, stress_list, linestyle='', marker='o')
                plt.pause(0.05)
        if stepping == 0 and len(force_list) > 0:
            print('Stopped device')
            break
#
try:
    ch.close()
except PhidgetException as e:
    print("Phidget Exception %i: %s" % (e.code, e.details))
    print("Press Enter to Exit...\n")
    readin = sys.stdin.read(1)
    exit(1)
#print(force_list)
#print(dist_list)
print("Closed VoltageRatioInput device")
print("Press CTRL+C to close the plot window and save the data")
try:
    while True:
        plt.pause(0.05)
except KeyboardInterrupt:
    pass

plt.savefig(out_png)

col_names = ['Distance/m'.ljust(15), 'Voltage ratio'.ljust(15), 'Force/N'.ljust(15), 'Stress/Pa'.ljust(15), 'Strain'.ljust(15)]
df = pd.DataFrame(columns=col_names)
for i in range(len(plt_length_list)):
    df.loc[i] = [str(plt_length_list[i]).ljust(15), str(voltrat_list[i]).ljust(15), str(force_list[i]).ljust(15), str(stress_list[i]).ljust(15), str(strain_list[i]).ljust(15)]
df.to_csv(out_csv, sep='\t', index=False)

l_bound = float(input("Linear region lower limit (strain): "))
u_bound = float(input("Linear region upper limit (strain): "))

linear_strain = []
linear_stress = []

for i in range(len(strain_list)):
    if strain_list[i] >= l_bound and strain_list[i] <= u_bound:
        linear_strain.append(strain_list[i])
        linear_stress.append(stress_list[i])
    if strain_list[i] >= u_bound:
        break

fit = polyfit(linear_strain, linear_stress, 1, cov=True)

y_mod = fit[0][0]
unc = fit[1][0][0]**0.5

if y_mod < 1000:
    print('Young\'s Modulus: %.1f ± %.1f Pa' % (y_mod, unc))
elif y_mod < 1000000:
    print('Young\'s Modulus: %.1f ± %.1f kPa' % (y_mod/1000, unc/1000))
else:
    print('Young\'s Modulus: %.1f ± %.1f MPa' % (y_mod/1000000, unc/1000000))
    
uts = max(stress_list)
if uts < 1000:
    print('Ultimate Tensile Stress: %.1f Pa' % (uts))
elif uts < 1000000:
    print('Ultimate Tensile Stress: %.1f kPa' % (uts/1000))
else:
    print('Ultimate Tensile Stress: %.1f MPa' % (uts/1000000))



exit(0)

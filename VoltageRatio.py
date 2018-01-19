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
thickness=float(input('Thickness of the sample (in micrometers): '))*10**(-6)
width=float(input('Width of the sample (in centimeters): '))*10**(-2)
length0=float(input('Length of the sample (in centimeters): '))*10**(-2)
outfile=input('Name of the output file (without extension): ')

out_csv=cwd+'/'+outfile+'.csv'
out_png=cwd+'/'+outfile+'.png'


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
        print("\nDetach event on Port %d Channel %d" % (detached.getHubPort(), detached.getChannel()))
    except PhidgetException as e:
        print("Phidget Exception %i: %s" % (e.code, e.details))
        print("Press Enter to Exit...\n")
        readin = sys.stdin.read(1)
        exit(1)   

def ErrorEvent(e, eCode, description):
    print("Error %i : %s" % (eCode, description))

all_forces_list=[]
a=6.94E6
b=-1401.52

def VoltageRatioChangeHandler(e, voltageRatio):
    x=voltageRatio
    weight=a*x+b    #in grams
    force=weight*9.81/1000   #in Newtons
    all_forces_list.append(force)
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

force_list=[]
dist_list=[]
stress_list = []
strain_list = []
ymod_list = []

plt.axis()
plt.ion()

def calc_stress(force):
    return force/(width*thickness) #in N/m2 (Pa)
    
def calc_strain(leng):
    return (leng-length0)/length0 #unitless

def calc_ymod(stress, strain):
    return stress/strain #in Pa

plt_dist_list=[]
plt_force_list=[]
t = 0
while True:
    data = arduino.readline()[:-2] #the last bit gets rid of the new-line chars
    if len((str(data)[2:-1]).split())==2:
#        print(str(data), dist_list)
        line=str(data)[2:-1]
        try:
            dist=length0+float(line.split()[0])*10**(-2)
        except ValueError:
            pass
        try:
            stepping=int(line.split()[1])
        except ValueError:
            pass
        if stepping==1 and all_forces_list[len(all_forces_list)-2]!=all_forces_list[len(all_forces_list)-1]:
            t += 1
#            dist_list.append(dist)
            force_list.append(all_forces_list[len(all_forces_list)-1])
            if t%500 ==0:
#                plt_dist_list.append(t/1000)
                plt_dist_list.append(dist)
                plt_force_list.append(all_forces_list[len(all_forces_list)-1])
                stress_list.append(calc_stress(all_forces_list[len(all_forces_list)-1]))
                strain_list.append(calc_strain(dist))
                ymod_list.append(calc_ymod(calc_stress(all_forces_list[len(all_forces_list)-1]),calc_strain(dist)))
                plt.plot(strain_list,stress_list,linestyle='',marker='o')
                plt.pause(0.05)
        if stepping ==0 and len(force_list) > 0:
            print('stop')
            break
#
try:
    ch.close()
except PhidgetException as e:
    print("Phidget Exception %i: %s" % (e.code, e.details))
    print("Press Enter to Exit...\n")
    readin = sys.stdin.read(1)
    exit(1) 
print(force_list)
print(dist_list)
print("Closed VoltageRatioInput device")
print("Press CTRL+C to close the plot window and save the data")
try:
    while True:
        plt.pause(0.05)
except KeyboardInterrupt:
    pass

plt.savefig(out_png)

col_names=['Distance'.ljust(15),'Force'.ljust(15),'Stress'.ljust(15),'Strain'.ljust(15)]
df=pd.DataFrame(columns=col_names)
for i in range(len(plt_dist_list)):
    df.loc[i]=[str(plt_dist_list[i]).ljust(15),str(force_list[i]).ljust(15),str(stress_list[i]).ljust(15),str(strain_list[i]).ljust(15)]
df.to_csv(out_csv,sep='\t',index=False)  

l_bound=float(input("Linear region lower limit (strain): "))   
u_bound=float(input("Linear region upper limit (strain): "))

linear_strain=[]
linear_stress=[]

for i in range(len(strain_list)):
    if strain_list[i]>=l_bound and strain_list[i]<=u_bound:
        linear_strain.append(strain_list[i])
        linear_stress.append(stress_list[i])
    if strain_list[i]>=u_bound:
        break
    
fit=polyfit(linear_strain,linear_stress,1,cov=True)

y_mod=fit[0][0]
unc=fit[1][0][0]**0.5

print(str(y_mod)+'+-'+str(unc))
               
exit(0)
                     

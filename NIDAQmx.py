# -*- coding: utf-8 -*-
"""
Created on Wed Jun 16 09:57:19 2021

@author: Conrad Kuz
This was one of my first contributions to the lab lol
It uses the NI-DAQmx with the BNC 2120 card to send out triggered signals or non-triggered signals

"""

import nidaqmx
from nidaqmx.constants import AcquisitionType, Edge
import time
from playsound import playsound
import serial

delayBoxComport = "COM4"
baud_rate = 9600  # Adjust the baud rate if necessary (often 9600 or 115200 for DG645)
timeout = 1  # Timeout for serial communication in seconds

# Establish serial connection


def armDelayBox():
    ser = serial.Serial(com_port, baud_rate, timeout=timeout)
    ser.write(b"*TRG\n")
    time.sleep(0.1)
    ser.close()


def returnToLocalMode():
    ser = serial.Serial(com_port, baud_rate, timeout=timeout)
    ser.write(b"UNLK\n")
    time.sleep(0.1)
    ser.write(b"LCAL\n")
    time.sleep(0.1)
    ser.close()


def openShutter(duration, delay, probe_delay=0):
    # requires trigger input in timing io
    # input as follow: duration units 20 = 2ms
    with nidaqmx.Task() as t:
        samples_per_second = 500  # 1000000 #original 10000
        shutterOpenTime = int(
            float(duration) * float(samples_per_second)
        )  # Number of samples in corresponding to shutter open length
        probe_delay = int(float(probe_delay) * float(samples_per_second))
        t.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        t.ao_channels.add_ao_voltage_chan("Dev1/ao1")
        # set update time per second
        t.timing.cfg_samp_clk_timing(
            int(samples_per_second),
            source="/Dev1/PFI0",
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=int(samples_per_second),
        )
        # ^ look at source input, by leaving blank it defaults to onboard clock, which is probs ehat needs to change
        # starts task on trigger
        t.triggers.start_trigger.cfg_dig_edge_start_trig(
            "/Dev1/PFI0", trigger_edge=Edge.RISING
        )

        delay = int(delay)
        signallist1 = (
            [0.0] * (1 + delay)
            + [5.0] * shutterOpenTime
            + [0.0] * (samples_per_second - shutterOpenTime - delay - 1)
        )
        signallist2 = (
            [0.0] * (1 + probe_delay)
            + [5.0] * shutterOpenTime
            + [0.0] * (samples_per_second - shutterOpenTime - probe_delay - 1)
        )
        # print(f"signallist1: {signallist1[:100]}...")  # Print the first 100 values for debugging
        # print(f"signallist2: {signallist2[:100]}...")
        t.write([signallist1, signallist2])
        t.start()
        t.wait_until_done()
        t.stop()


def openShutterLong(duration):

    # for longer open times: duration in seconds
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        t.write(5.0, auto_start=True)
        time.sleep(duration)
        t.write(0.0, auto_start=True)
        t.stop()


def setShutterOpen():
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        t.write(5.0, auto_start=True)
        t.stop()


def setShutterClose():
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        t.write(0.0, auto_start=True)
        t.stop()


if __name__ == "__main__":
    if input("Long? (y/n): ") == "y":
        shutter_time = float(input("shutter time(seconds): "))
        user_input = input("enter to shoot, e to end: ")
        count = 1
        while user_input != "e":
            # openShutterLong(shutter_time)
            print("SE Laser 5 second timer")
            time.sleep(5)  # Remove this if not using SE laser
            print(count)
            if count < 20:
                count += 1
            else:
                playsound("ClownHorn.mp3")
                count = 1
            user_input = input("enter to shoot, e to end: ")

    else:
        # print("SHUTTER IS ONLY CONFIGURED FOR 1 SHOT RIGHT NOW!!! Save this code and download previous version in teams thor")
        shutter_time = input("shutter time (in Seconds (.002=2ms)):")
        # delay = input("delay (20=2ms): ")
        delay = 0
        probe_delay = 0
        user_input = input("enter to shoot, e to end, c to change probe delay: ")
        while user_input != "e":
            if user_input == "c":
                probe_delay = input("enter probe delay in seconds: ")
            delay = int(delay)
            # armDelayBox()
            openShutter(shutter_time, delay, float(probe_delay))
            print("SE Laser 5 second timer")
            time.sleep(5)
            # returnToLocalMode()
            user_input = input("enter to shoot, e to end, c to change probe delay: ")
            # delay = input("delay (20=2ms): ")

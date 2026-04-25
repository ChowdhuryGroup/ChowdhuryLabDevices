import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import sys
import time

class Oscilloscope:
    def __init__(self, instrumentID=None):
        if sys.platform == "win32":
            self.rm = pyvisa.ResourceManager("C:\\Windows\\System32\\visa32")
        else:
            self.rm = pyvisa.ResourceManager()
            
        if instrumentID is None:
            inst_list = self.rm.list_resources()
            print(f"Available instruments: {inst_list}")
            index = int(input("Select instrument by typing index:\n"))
            instrumentID = inst_list[index]
            
        self.inst = self.rm.open_resource(instrumentID)
        self.inst.timeout = 300000  # 300 seconds is usually plenty
        print(f"Connected: {self.inst.query('*IDN?')}")

        # Standard waveform settings
        self.inst.write(":WAVeform:POINts:MODE MAX")
        self.inst.write(":WAVeform:FORMat WORD")
        self.inst.write(":WAVeform:UNSigned 0")
        self.inst.write(":WAVeform:BYTeorder LSBFirst")

    def select_channels(self, channels: tuple):
        for i in range(1, 5):
            state = "ON" if i in channels else "OFF"
            self.inst.write(f":CHANnel{i}:DISPlay {state}")

    def configure_timebase(self, duration: float, offset: float = 0.0):
        self.inst.write(f":TIMebase:RANGe {duration}")
        self.inst.write(f":TIMebase:POSition {offset}")

    def _get_preamble(self, channel: int) -> dict:
        self.inst.write(f":WAVeform:SOURce CHANnel{channel}")
        raw = self.inst.query(":WAVeform:PREamble?").split(",")
        keys = ["format", "type", "points", "count", "xincrement", "xorigin", 
                "xreference", "yincrement", "yorigin", "yreference"]
        return dict(zip(keys, [float(x) for x in raw]))

    def _scale_data(self, raw_data: np.ndarray, preamble: dict) -> np.ndarray:
        return (raw_data - preamble["yreference"]) * preamble["yincrement"] + preamble["yorigin"]

    def _get_times(self, length: int, preamble: dict) -> np.ndarray:
        return (np.arange(length) - preamble["xreference"]) * preamble["xincrement"] + preamble["xorigin"]
    def set_real_time_mode(self):
        self.inst.write(":ACQuire:MODE RTIMe")
        self.inst.write(":RUN")
    def acquire_single(self, channels: tuple) -> dict:
        self.set_real_time_mode()
        self.inst.write(":SINGle")
        self.inst.query("*OPC?") 

        results = {}
        for ch in channels:
            self.inst.write(f":WAVeform:SOURce CHANnel{ch}")
            preamble = self._get_preamble(ch)
            raw = self.inst.query_binary_values(
                ":WAVeform:DATA?", datatype="h", container=np.array, is_big_endian=False
            )
            
            results[ch] = {
                "times": self._get_times(len(raw), preamble),
                "voltages": self._scale_data(raw, preamble)
            }
        return results
    def acquire_segmented(self, channels: tuple, segment_count: int,laser_to_open_and_close = None,shutter_open_time = None) -> dict:
        self.inst.write(":ACQuire:MODE SEGMented")
        self.inst.write(f":ACQuire:SEGMented:COUNt {segment_count}")
        self.inst.write(":SINGle")
        if laser_to_open_and_close is not None:
            time.sleep(.5)
            laser_to_open_and_close.open_shutter()
            time.sleep(shutter_open_time)  # Wait for the shutter to be open and triggers to be captured
        # Increase timeout temporarily to wait for the triggers to finish
        if laser_to_open_and_close is not None:
            laser_to_open_and_close.close_shutter()
        self.inst.query("*OPC?")


        # --- THE SPEED FIX: Tell the scope to send ALL segments at once ---
        self.inst.write(":WAVeform:SEGMented:ALL ON")

        results = {}
        for ch in channels:
            self.inst.write(f":WAVeform:SOURce CHANnel{ch}")
            preamble = self._get_preamble(ch)
            
            # This now downloads all 80 segments in one giant block!
            raw_flat = self.inst.query_binary_values(
                ":WAVeform:DATA?", datatype="h", container=np.array, is_big_endian=False
            )
            
            # Convert the giant 1D array to floats using the preamble
            scaled_flat = self._scale_data(raw_flat, preamble)
            
            # Reshape into a 2D array: (segment_count, points_per_segment)
            points_per_seg = len(raw_flat) // segment_count
            segments_2d = scaled_flat.reshape((segment_count, points_per_seg))
            
            results[ch] = {
                "times": self._get_times(points_per_seg, preamble),
                # list() converts the 2D array back to a list of 1D arrays to match your script
                "segments": list(segments_2d) 
            }
            
        # Turn it back off to not mess up future single-acquisitions
        self.inst.write(":WAVeform:SEGMented:ALL OFF")
        
        return results


    def acquire_segmentedOld(self, channels: tuple, segment_count: int) -> dict:
        self.inst.write(":ACQuire:MODE SEGMented")
        self.inst.write(f":ACQuire:SEGMented:COUNt {segment_count}")
        self.inst.write(":SINGle")
        self.inst.query("*OPC?") 

        results = {}
        for ch in channels:
            self.inst.write(f":WAVeform:SOURce CHANnel{ch}")
            preamble = self._get_preamble(ch)
            
            segments = []
            for i in range(1, segment_count + 1):
                self.inst.write(f":ACQuire:SEGMented:INDex {i}")
                raw = self.inst.query_binary_values(
                    ":WAVeform:DATA?", datatype="h", container=np.array, is_big_endian=False
                )
                segments.append(self._scale_data(raw, preamble))
                
            results[ch] = {
                "times": self._get_times(len(segments[0]), preamble),
                "segments": segments
            }
        return results

if __name__ == '__main__':
    scope = Oscilloscope()
    
    # Configure Scope
    scope.configure_timebase(duration=1600e-9, offset=500e-9)
    target_channels = (1,2,3) # Add 2, 3, etc if needed
    scope.select_channels(target_channels)

    # Acquire Data
    print("Acquiring segments...")
    data = scope.acquire_segmented(target_channels, segment_count=10)

    # Plotting for Channel 1
    ch1_data = data[1]
    ch2_data = data[2]
    ch3_data = data[3]

    ch1times = ch1_data["times"]
    ch1segments = ch1_data["segments"]

    ch2times = ch2_data["times"]
    ch2segments = ch2_data["segments"]
    ch3times = ch3_data["times"]
    ch3segments = ch3_data["segments"]

    # 1. Plot individual segments
    plt.figure()
    for i, seg_volts in enumerate(ch1segments[:5]):
        plt.plot(ch1times, seg_volts, label=f"Seg {i+1}", alpha=0.6)
        plt.plot(ch2times, ch2segments[i], label=f"Seg {i+1} Ch2", alpha=0.6)
        plt.plot(ch3times, ch3segments[i], label=f"Seg {i+1} Ch3", alpha=0.6)

    plt.title("Segmented Acquisition - Channel 1")
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.legend()
    plt.show()


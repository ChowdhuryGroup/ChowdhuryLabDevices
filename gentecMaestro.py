import serial
import time
import math

class gentecMaestro:
    def __init__(self, port_name='COM1'):
        """
        Initializes the connection to the MAESTRO using the settings 
        specified in the manual (Section 3.1.2.2).
        """
        # Configuration per manual: 115200 baud, 8 data bits, No parity, 1 stop bit, No flow control [cite: 3919]
        self.ser = serial.Serial(
            port=port_name,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
    def measure_statistics(self, duration_seconds):
        """
        Streams power data for x seconds and returns calculated statistics.
        Returns: dictionary {'average_w': float, 'rms_stability_pct': float, 'ptp_stability_pct': float}
        """
        measurements = []
        start_time = time.time()

        # Flush any old data
        self.ser.reset_input_buffer()

        # Send *CAU command to start continuous transmission [cite: 4303]
        # Native commands must start with * and DO NOT end with \r or \n [cite: 4200]
        self.ser.write(b'*CAU')

        try:
            # Collect data for the specified duration
            while (time.time() - start_time) < duration_seconds:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    try:
                        # Values are sent in ASCII [cite: 4306]
                        value = float(line)
                        measurements.append(value)
                    except ValueError:
                        print("measurement received non-numeric data:", line)
                        continue # Ignore non-numeric lines (e.g., startup noise)
        
        finally:
            # Send *CSU to stop the data stream [cite: 4308]
            self.ser.write(b'*CSU')

        if not measurements:
            return None

        # --- Calculate Statistics per Manual Formulas [cite: 3681] ---
        
        # 1. Average Value (P_avg)
        avg_power = sum(measurements) / len(measurements)

        # 2. Standard Deviation (STD)
        # STD = sqrt( sum((P - P_avg)^2) / (n - 1) )
        if len(measurements) > 1:
            variance = sum((x - avg_power) ** 2 for x in measurements) / (len(measurements) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        # 3. RMS Stability (%) = (STD / P_avg) * 100
        rms_stability = (std_dev / avg_power * 100) if avg_power != 0 else 0.0

        # 4. PTP Stability (%) = ((Max - Min) / P_avg) * 100
        max_val = max(measurements)
        min_val = min(measurements)
        ptp_stability = ((max_val - min_val) / avg_power * 100) if avg_power != 0 else 0.0

        return {
            "average_power": avg_power,
            "rms_stability": rms_stability,
            "ptp_stability": ptp_stability,
            "num_measurements": len(measurements)
        }

    def close(self):
        """Closes the serial connection."""
        if self.ser.is_open:
            self.ser.close()

# --- Example Usage ---
if __name__ == "__main__":
    # Replace 'COM3' with your actual USB Serial Port
    monitor = gentecMaestro(port_name='COM11')
    
    try:
        print("Starting 5-second measurement...")
        stats = monitor.measure_statistics(5)
        
        if stats:
            print(f"Average Power: {stats['average_power']:.4e} W")
            print(f"RMS Stability: {stats['rms_stability']:.2f} %")
            print(f"PTP Stability: {stats['ptp_stability']:.2f} %")
            print(f"Number of Measurements: {stats['num_measurements']}")
        else:
            print("No data received.")
            
    finally:
        monitor.close()

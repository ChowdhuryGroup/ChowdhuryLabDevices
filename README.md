# ChowdhuryLabDevices
A collection of lightweight Python classes designed for seamless device integration in laboratory environments. These scripts wrap low-level serial (RS-232), VISA, and .NET interfaces into clean, high-level Pythonic APIs.

---

## 🛠 Supported Hardware

### **Optical & Power Monitoring**
* **Gentec-EO Maestro**: Power meter control for continuous data streaming and real-time statistics (Average, RMS, and PTP stability).
* **Oscilloscope (VISA)**: Interface for capturing waveforms from Rigol/Agilent scopes, managing preambles, and converting binary data into physical units.

### **Motion Control**
* **Newport Delay Line Stage**: .NET-powered control for DLS series stages, featuring automated homing and absolute/relative positioning.
* **OWIS MDE235 Rotator**: High-precision rotation stage control with specialized 3-phase initialization sequences for torque-aligned microstepping.
* **Melles Griot Nanomotion II**: Linear motor control including speed regulation, software limits, and "park/unpark" safety routines.
* **VXM Stage Controller** Stepper motor controller with full control for precise large distance sample or optic positioning.

### **Timing & Signal Generation**
* **Stanford DG645**: Digital delay generator control for triggering and precise multi-channel delay/width synchronization.
* **NI-DAQmx (BNC 2120)**: National Instruments data acquisition control for hardware-triggered shutter operations and analog voltage output.

---

## 🚀 Quick Start

Most devices follow a consistent initialization pattern. For example, to control the **OWIS Rotator**:

```python
from mde235Rotator import OWISController

# Initialize on specific COM port
stage = OWISController(port='COM5')

# Move to an absolute angle
stage.move_absolute_angle(45.0)

# Close connection
stage.close()

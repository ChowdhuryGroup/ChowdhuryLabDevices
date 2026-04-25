import os
import time
import PySpin


class FlirCamera:
    """
    Barebones PySpin camera wrapper.

    API:
      - captureimage(filepath)
      - set_gain(gain_db)
      - set_exposure(time_us)
      - trigger_mode(enabled: bool)

    Defaults:
      - ADC bit depth: 12-bit (if supported)
      - PixelFormat: Mono16 (common for >8-bit acquisition)
      - AcquisitionMode: SingleFrame
    """

    def __init__(self, serial: str | None = None, adc_bits: int = 12):
        self._system = PySpin.System.GetInstance()
        self._cam_list = self._system.GetCameras()

        if self._cam_list.GetSize() == 0:
            self._cleanup()
            raise RuntimeError("No cameras detected by PySpin.")

        self._cam = self._select_camera(serial)
        self._cam.Init()
        self._nodemap = self._cam.GetNodeMap()

        self._set_enum("AcquisitionMode", "SingleFrame")
        self._set_enum("PixelFormat", "Mono16")  # typical container for 12-bit data

        # Best-effort 12-bit ADC depth (node name varies by model)
        self._set_adc_bits(adc_bits)

    # -----------------------------
    # Public API
    # -----------------------------

    def set_gain(self, gain_db: float) -> None:
        self._set_enum("GainAuto", "Off")
        node = PySpin.CFloatPtr(self._nodemap.GetNode("Gain"))
        if not (PySpin.IsAvailable(node) and PySpin.IsWritable(node)):
            raise RuntimeError("Gain node not available/writable.")
        # clamp to range
        gain_db = float(max(node.GetMin(), min(node.GetMax(), gain_db)))
        node.SetValue(gain_db)

    def set_exposure(self, time_us: float) -> None:
        self._set_enum("ExposureAuto", "Off")
        node = PySpin.CFloatPtr(self._nodemap.GetNode("ExposureTime"))
        if not (PySpin.IsAvailable(node) and PySpin.IsWritable(node)):
            raise RuntimeError("ExposureTime node not available/writable.")
        time_us = float(max(node.GetMin(), min(node.GetMax(), time_us)))
        node.SetValue(time_us)

    def trigger_mode(self, enabled: bool) -> None:
        # Note: choose your TriggerSource separately if you need hardware lines.
        self._set_enum("TriggerMode", "On" if enabled else "Off")

    def captureimageUnSafe(self, filepath: str = None, timeout_ms: int = 10000) -> None:
        if filepath is not None:
            folder = os.path.dirname(os.path.abspath(filepath))
            if folder and not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)

        self._cam.BeginAcquisition()
        try:
            img = self._cam.GetNextImage(int(timeout_ms))
            try:
                if img.IsIncomplete():
                    raise RuntimeError(f"Incomplete image (status {img.GetImageStatus()}).")
                if filepath is not None:
                    img.Save(filepath)  # format inferred from extension (png, tif, jpg, etc.)
                img.Release()  # release buffer back to camera
                time.sleep(0.01)  # small delay to ensure file is written before next capture   
                #return img.GetNDArray()  # for in-memory use
            except Exception as e:
                print(f"Error capturing image: {e}")

            finally:
                img.Release()
        finally:
            self._cam.EndAcquisition()

    def captureimage(self, filepath: str = None, timeout_ms: int = 10000) -> None:
        if filepath is not None:
            folder = os.path.dirname(os.path.abspath(filepath))
            if folder and not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)

        # Try BeginAcquisition, and retry once if the first time fails
        for attempt in range(2):
            try:
                self._cam.BeginAcquisition()
                break
            except PySpin.SpinnakerException as e:
                print(f"BeginAcquisition failed (attempt {attempt+1}): {e}")
                if attempt == 1:
                    # Second failure -> give up
                    raise
                time.sleep(0.1)  # small delay before retry

        try:
            img = self._cam.GetNextImage(int(timeout_ms))
            try:
                if img.IsIncomplete():
                    raise RuntimeError(f"Incomplete image (status {img.GetImageStatus()}).")

                if filepath is not None:
                    img.Save(filepath)
                else:
                    return img.GetNDArray()

            except Exception as e:
                print(f"Error capturing image: {e}")
            finally:
                if img.IsValid():
                    img.Release()
            time.sleep(0.01)
        finally:
            self._cam.EndAcquisition()

    def liveview(self) -> None:
        import matplotlib.pyplot as plt
        import keyboard

        sNodemap = self._cam.GetTLStreamNodeMap()

        # --- Save current state ---
        original_acq_mode = self._try_get_enum("AcquisitionMode")
        original_trigger_mode = self._try_get_enum("TriggerMode")

        node_bufferhandling_mode = PySpin.CEnumerationPtr(
            sNodemap.GetNode("StreamBufferHandlingMode")
        )
        original_buffer_mode = None
        if PySpin.IsAvailable(node_bufferhandling_mode) and PySpin.IsReadable(node_bufferhandling_mode):
            original_buffer_mode = node_bufferhandling_mode.GetIntValue()

        try:
            # --- Configure for live view ---
            self._set_enum("TriggerMode", "Off")          # must be off for free-run
            self._set_enum("AcquisitionMode", "Continuous")

            if PySpin.IsAvailable(node_bufferhandling_mode) and PySpin.IsWritable(node_bufferhandling_mode):
                newest = node_bufferhandling_mode.GetEntryByName("NewestOnly")
                if PySpin.IsAvailable(newest) and PySpin.IsReadable(newest):
                    node_bufferhandling_mode.SetIntValue(newest.GetValue())

            self._cam.BeginAcquisition()

            plt.ion()
            fig, ax = plt.subplots()
            img_plot = None
            print("Entering live view mode. Press ENTER to exit.")
            while True:
                if keyboard.is_pressed('ENTER'):
                    break

                try:
                    img = self._cam.GetNextImage(350)

                    if not img.IsIncomplete():
                        data = img.GetNDArray()

                        if img_plot is None:
                            img_plot = ax.imshow(data, cmap='gray')
                        else:
                            img_plot.set_data(data)

                        plt.pause(0.001)
                        time.sleep(0.01)  # small delay to reduce CPU usage
                    img.Release()

                except PySpin.SpinnakerException as e:
                    print(f"LiveView error: {e}")

            plt.close(fig)

        finally:
            # --- Clean shutdown ---
            try:
                self._cam.EndAcquisition()
            except:
                pass

            # Restore acquisition mode
            if original_acq_mode:
                self._set_enum("AcquisitionMode", original_acq_mode)

            # Restore trigger mode
            if original_trigger_mode:
                self._set_enum("TriggerMode", original_trigger_mode)

            # Restore buffer handling
            if original_buffer_mode is not None and PySpin.IsWritable(node_bufferhandling_mode):
                try:
                    node_bufferhandling_mode.SetIntValue(original_buffer_mode)
                except:
                    pass

    def close(self) -> None:
        if getattr(self, "_cam", None) is None:
            return

        try:
            # Drop nodemap first (it can hold camera refs)
            self._nodemap = None

            # Deinit camera
            if self._cam.IsInitialized():
                self._cam.DeInit()

            # IMPORTANT: delete the camera object to release refcounts
            cam = self._cam
            self._cam = None
            del cam

        finally:
            self._cleanup()

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # -----------------------------
    # Internals
    # -----------------------------

    def _select_camera(self, serial: str | None) -> PySpin.CameraPtr:
        if serial is None:
            return self._cam_list.GetByIndex(0)

        for i in range(self._cam_list.GetSize()):
            cam = self._cam_list.GetByIndex(i)
            tlnm = cam.GetTLDeviceNodeMap()
            sn = PySpin.CStringPtr(tlnm.GetNode("DeviceSerialNumber")).GetValue()
            if sn == serial:
                return cam

        raise RuntimeError(f"Camera with serial {serial!r} not found.")

    def _set_enum(self, node_name: str, choice: str) -> None:
        enum_node = PySpin.CEnumerationPtr(self._nodemap.GetNode(node_name))
        if not (PySpin.IsAvailable(enum_node) and PySpin.IsWritable(enum_node)):
            # silently ignore for "best-effort" nodes
            return
        entry = PySpin.CEnumEntryPtr(enum_node.GetEntryByName(choice))
        if not (PySpin.IsAvailable(entry) and PySpin.IsReadable(entry)):
            return
        enum_node.SetIntValue(entry.GetValue())

    def _set_adc_bits(self, bits: int) -> None:
        """
        Different FLIR models expose this differently. Common patterns:
          - AdcBitDepth: "Bit12"
          - ADCBitDepth: "Bit12"
          - PixelSize / BitDepth nodes (less common)
        This is best-effort; if not present, no error.
        """
        bits = int(bits)
        if bits == 12:
            candidates = [("AdcBitDepth", "Bit12"), ("ADCBitDepth", "Bit12")]
        elif bits == 10:
            candidates = [("AdcBitDepth", "Bit10"), ("ADCBitDepth", "Bit10")]
        elif bits == 14:
            candidates = [("AdcBitDepth", "Bit14"), ("ADCBitDepth", "Bit14")]
        else:
            candidates = []

        for node, entry in candidates:
            before = self._try_get_enum(node)
            self._set_enum(node, entry)
            after = self._try_get_enum(node)
            if after is not None and after != before:
                return  # succeeded

    def _try_get_enum(self, node_name: str) -> str | None:
        enum_node = PySpin.CEnumerationPtr(self._nodemap.GetNode(node_name))
        if not (PySpin.IsAvailable(enum_node) and PySpin.IsReadable(enum_node)):
            return None
        cur = enum_node.GetCurrentEntry()
        if not (PySpin.IsAvailable(cur) and PySpin.IsReadable(cur)):
            return None
        return cur.GetSymbolic()

    def _cleanup(self) -> None:
        # Clear camera list
        if getattr(self, "_cam_list", None) is not None:
            cl = self._cam_list
            self._cam_list = None
            cl.Clear()
            del cl

        # Now release the system
        if getattr(self, "_system", None) is not None:
            sys = self._system
            self._system = None
            sys.ReleaseInstance()
            del sys


# Example usage:
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    with FlirCamera(serial=None) as cam:
        cam.set_gain(0)
        cam.set_exposure(800)  # us
        cam.trigger_mode(False)
        plt.imshow(cam.captureimage(filepath = r"outputs\test_image.tif"))
        plt.colorbar()
        plt.show()
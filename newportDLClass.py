import sys
import time

# Load Assembly
sys.path.append(r"C:\Windows\Microsoft.NET\assembly\GAC_32\Newport.DLS.CommandInterface\v4.0_1.0.1.0__90ac4f829985d2bf")
import clr
clr.AddReference(r"C:\Windows\Microsoft.NET\assembly\GAC_64\Newport.DLS.CommandInterface\v4.0_1.0.1.0__90ac4f829985d2bf\Newport.DLS.CommandInterface.dll")
from CommandInterfaceDLS import DLS

class DelayLineStage:
    def __init__(self, port="COM4"):
        self.port = port
        self.device = DLS()
        self.is_connected = False
        self.connect()
        self.ensure_initialized()

    def connect(self):
        """Opens communication with the selected device."""
        print(f"Connecting to {self.port}...")
        result = self.device.OpenInstrument(self.port)
        if result == 0:
            self.is_connected = True
            # The VE command returns (ret_val, ControllerVersion, errstring).
            # Index 1 contains the actual version string.
            ve_result = self.device.VE()
            version = ve_result[1] if len(ve_result) > 1 else "Unknown"
            print(f"Connected successfully. Version: {version}")
            return True
        else:
            print(f"Failed to connect to {self.port}. Error code: {result}")
            return False



    def disconnect(self):
        """Closes communication with the selected device[cite: 400]."""
        if self.is_connected:
            self.device.CloseInstrument()
            self.is_connected = False
            print("Disconnected.")



        
    def get_status(self):
        """Retrieves the positioner error and controller state."""
        ts_result = self.device.TS()
        
        # Unpack dynamically. Safely strip whitespace from the strings.
        if len(ts_result) >= 4:
            print("STAGE STATUS:",ts_result)
            ret_val = ts_result[1]
            error_code = str(ts_result[2]).strip()
            status_code = str(ts_result[3]).strip()
            print("STAGE CONTROLLER STATE: ",status_code)
            
            if ret_val == '0':
                return status_code, error_code
            else:
                err_string = str(ts_result[-1]).strip()
                print(f"TS Command Failed. Error: {err_string}")
                return None, None
        else:
            print(f"Unexpected TS() return format: {ts_result}")
            return None, None

    def ensure_initialized(self, timeout=45):
        """Checks stage status, initializes/homes if needed, and waits for completion."""
        status_code, error_code = self.get_status()
        print(f"Initial Status Check -> Status: '{status_code}', Error: '{error_code}'")

        # If there is an existing error code (not '0', '00', or empty), try to clear it
        if error_code and error_code not in ['0', '00', '00000','@']:
            print(f"Controller has an active error ({error_code}). Reading error to clear...")
            # TE reads and clears the last command error
            self.device.TE() 
            time.sleep(0.5)

        # To be safe while we map your controller, we will force the init/home sequence 
        # unless we specifically see standard "Ready" states. 
        # We'll assume typical Newport ready states: '32', '33', '34'.
        if status_code not in ['46', '47', '48','49']:
            print(f"Stage requires initialization/homing (Current Status: '{status_code}').")
            if input("Sure you want to move stage to home? (y/n): ").lower() != "y":
                sys.exit()
            # 1. Initialization Sequence
            print("Sending Initialization Command (IE)...")
            ret_val, *err_info = self.device.IE()
                
            time.sleep(2) # Buffer time for IE to register before OR

            print("Homing now")
            # 2. Home Search
            self.home_stage()
            
        else:
            print(f"Stage is already initialized and Ready (Status: '{status_code}'). Skipping init.")
            return True
    def home_stage(self, timeout=5):
        """
        Executes the Home Search (OR) and waits for completion.
        """
        print("Initiating Home Search...")
        
        # 1. Send the OR command (Execute Home Search)
        # Syntax: int OR(out string errstring)
        result = self.device.OR() # Returns tuple: (int result, string errstring)
        
        # Check if the command was accepted
        if result[0] != 0:
            print(f"Homing command failed to start. Error: {result[1]}")
            return False

        # 2. Wait for Homing to complete
        # We can monitor the status using the TS (Read Controller Status) command.
        # While moving, the controller usually reports a specific status code.
        # A simple way is to wait until the stage stops moving.
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:

            
            time.sleep(1) 
            
            # If you see the status settle or the position reset to 0 (or HomeOffset), it's done.
        
        print("Homing sequence timeout or complete.")
        return True

    def reset_device(self):
        """Resets controller[cite: 2184]."""
        print("Resetting device...")
        ret_val, err_string = self.device.RS()
        if ret_val == 0:
            print("Reset command sent successfully.")
            return True
        print(f"Failed to reset device. Error: {err_string}")
        return False

    def set_velocity(self, velocity):
        """Sets the velocity[cite: 2351]."""
        status, err_string = self.device.VA_Set(float(velocity))
        if status == 0:
            print(f"Velocity set to {velocity}.")
        else:
            print(f"Failed to set velocity: {err_string}")

    def move_relative(self, step):
        """Moves relative[cite: 1968]."""
        status, err_string = self.device.PR_Set(float(step))
        if status == 0:
            print(f"Moving relatively by {step} units.")
        else:
            print(f"Failed relative move: {err_string}")

    def move_absolute(self, target_position):
        """Moves absolute[cite: 1901]."""
        status, err_string = self.device.PA_Set(float(target_position))
        if status == 0:
            print(f"Moving absolutely to {target_position}.")
        else:
            print(f"Failed absolute move: {err_string}")


if __name__ == "__main__":
    stage = DelayLineStage("COM4")
    
    if stage.connect():
        # Only initializes if the status check requires it
        stage.ensure_initialized()
        
        print("\n--- Manual Stage Control ---")
        print("Commands:")
        print("  rel <value>  : Move relatively (e.g., 'rel 5.0')")
        print("  abs <value>  : Move absolutely (e.g., 'abs 10.0')")
        print("  vel <value>  : Set velocity (e.g., 'vel 2.5')")
        print("  status       : Get current stage status")
        print("  reset        : Reset controller")
        print("  quit         : Exit")
        
        while True:
            try:
                user_input = input("\nEnter command: ").strip().lower().split()
                if not user_input:
                    continue
                
                cmd = user_input[0]
                
                if cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "status":
                    status_code, error_code = stage.get_status()
                    print(f"Status Code: {status_code} | Error Code: {error_code}")
                elif cmd == "reset":
                    stage.reset_device()
                elif cmd == "rel" and len(user_input) > 1:
                    stage.move_relative(user_input[1])
                elif cmd == "abs" and len(user_input) > 1:
                    stage.move_absolute(user_input[1])
                elif cmd == "vel" and len(user_input) > 1:
                    stage.set_velocity(user_input[1])
                elif cmd == "initialize":
                    stage.reset_device()
                    stage.ensure_initialized()
                else:
                    print("Invalid command or missing parameter.")
            except ValueError:
                print("Please enter a valid numeric value.")
            except Exception as e:
                print(f"An error occurred: {e}")

        stage.disconnect()
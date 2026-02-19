import serial
import time

class OWISController:
    # 5446.66 steps per degree (using the exact 1634 gear ratio for MDE235)
    STEPS_PER_DEGREE = 5446.66 

    def __init__(self, port, baudrate=9600):
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            
            self.term_char = '\r'
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            print(f"Connected to {port}. Executing 3-Phase sequence with torque boost...")

            # Phase 1: Torque Boost for Initial Phase Alignment
            # Over-drive the coils to ensure the rotor snaps to the nearest microstep
            phase1 = [
                "term=0",
                "errclear",
                "ampshnt1=0",
                "holcur1=28",  # High hold current for phase lock
                "dricur1=37"   # High drive current for phase lock
            ]
            for cmd in phase1:
                self.send_command(cmd)
            
            self.send_command("init1", delay=0.5) 

            # Phase 2: The Hidden DMT40 Database Base Profile
            # Pushes the critical PWM frequency and chopper decay modes
            phase2 = [
                "pvel1=5750", "acc1=300000", "rvelf1=-5750", "rvels1=570",
                "rdacc1=300000", "fvel1=570", "jvel1=5750", "fkp1=0", "fki1=0",
                "fkd1=0", "fil1=0", "fdt1=0", "fst1=256", "maxout1=99",
                "mxposerr1=0", "smk1=0", "spl1=15", "rmk1=1", "rpl1=15",
                "mcstp1=50", "phintim1=1", "ampmode1=3", "lmk1=0",
                "slmin1=0", "slmax1=0", "amppwmf1=20000"
            ]
            for cmd in phase2:
                self.send_command(cmd)

            self.send_command("init1", delay=0.5) 

            # Phase 3: The User Target Profile (Cooldown and Kinematics)
            # Drops the current back to safe operating limits and sets the slower velocities
            phase3 = [
                "ampshnt1=0",
                "holcur1=10",   # Safe holding current restored
                "dricur1=20",   # Safe drive current restored
                "mcstp1=50",
                "pvel1=32680",
                "acc1=272333",
                "rvelf1=5447",
                "rvels1=545",
                "rdacc1=272333",
                "smk1=0", "spl1=15", "rmk1=1", "rpl1=15"
            ]
            for cmd in phase3:
                self.send_command(cmd)

            print("Controller successfully configured to exact OWISoft runtime specifications.")
            
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            raise

    def send_command(self, command, delay=0.05):
        full_cmd = command + self.term_char
        self.ser.write(full_cmd.encode('ascii'))
        time.sleep(delay) 
        if self.ser.in_waiting > 0:
            self.ser.read(self.ser.in_waiting)
            
    def _degrees_to_counts(self, degrees):
        return int(degrees * self.STEPS_PER_DEGREE)

    def move_relative_angle(self, degrees):
        counts = self._degrees_to_counts(degrees)
        self.send_command("relat1")
        self.send_command(f"pset1={counts}")
        self.send_command("pgo1")
        print(f"Moving Relative: {degrees} deg ({counts} counts)")

    def move_absolute_angle(self, degrees):
        counts = self._degrees_to_counts(degrees)
        self.send_command("absol1")
        self.send_command(f"pset1={counts}")
        self.send_command("pgo1")
        print(f"Moving Absolute: {degrees} deg ({counts} counts)")

    def close(self):
        if self.ser.is_open:
            self.ser.close()
            print("Connection closed.")

if __name__ == "__main__":
    PORT = 'COM5' 
    
    try:
        stage = OWISController(PORT)
        
        while True:
            user_input = input("\nEnter angle (degrees) or 'q' to quit: ").strip()
            if user_input.lower() == 'q':
                break
                
            try:
                angle = float(user_input)
                mode = input("Type 'r' for relative or 'a' for absolute move: ").strip().lower()
                
                if mode == 'r':
                    stage.move_relative_angle(angle)
                elif mode == 'a':
                    stage.move_absolute_angle(angle)
                else:
                    print("Invalid mode selected.")
                    
            except ValueError:
                print("Invalid number entered.")
                
        stage.close()
        
    except Exception as e:
        print(f"Program failed: {e}")
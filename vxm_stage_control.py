import serial
import time
import sys
import glob
import math

#Small stage is .002504mm/step
conversion = 1/.002504 #step/mm conversion - stage takes units of steps rightnow
def serial_ports():
    """Grabbed from: https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    Lists serial port names

    :raises EnvironmentError:
        On unsupported or unknown platforms
    :returns:
        A list of the serial ports available on the system
    """
    if sys.platform.startswith("win"):
        ports = ["COM%s" % (i + 1) for i in range(256)]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        ports = glob.glob("/dev/tty.*")
    else:
        raise EnvironmentError("Unsupported platform")

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class VXMController:

    def __init__(self, step_size: float = 0.254, axis: int = 1,com_port: str = None):
        """
        step_size: mm/step
        """
        self.axis = axis
        self.step_size = step_size
        self.port = serial_ports()[1]
        if com_port:
            self.port = com_port
        self.connection = serial.Serial(self.port)
        self.connection.timeout = 0
        if self.connection.isOpen() == False:
            self.connection.open()
        self.take_control(echo=False)  # may change echo to be class property
        self.set_speed(1000)
        # self.home()
        ##self.set_zero()
        # print("Determining range of motion...")
        # self.move_max()
        # self.max_index = self.poll_index() - 1
        # self.home()
        self.current_index = 0

    def __del__(self):
        self.relinquish_control()
        self.connection.close()
        print("Disconnected controller")

    def serial_write(self, command: str):
        self.connection.write("C".encode(encoding="ascii"))
        self.connection.write(command.encode(encoding="ascii"))

    def take_control(self, echo: bool = False):
        """
        Disable manual control, enable computer control (orange light indicates success)
        """
        if echo:
            self.serial_write("E")
        else:
            self.serial_write("F")

    def relinquish_control(self):
        """
        Clear controller memory of commands and return to manual mode
        """
        self.serial_write("C,Q")
        time.sleep(0.1)

    def kill_program(self):
        """
        Stops the program currently running in the controller
        """
        self.serial_write("K")

    def poll_index(self):
        """
        Gets the absolute index of the stage
        """
        self.serial_write("X")
        time.sleep(0.1)
        index_raw = self.connection.readline()
        index = index_raw.decode(encoding="ascii").strip("^")
        print("Current index: " + index)
        return int(index)

    def move_min(self):
        """
        Move to the maximum position (closest to motor)
        """
        self.serial_write(f"I{self.axis}M-0,R")
        time.sleep(30000 / self.speed + 0.1)

    def move_max(self):
        """
        Move to the maximum position (furthest from motor)
        """
        self.serial_write(f"I{self.axis}M0,R")
        time.sleep(30000 / self.speed + 0.1)

    def set_zero(self):
        """
        Set the absolute zero index
        """
        self.serial_write(f"IA{self.axis}M-0,R")

    def home(self):
        """
        Move to position closest to the motor and set index to zero
        """
        print("Homing...")
        self.move_min()
        self.set_zero()

    def move_absolute(self, index: int, speed: int):
        """
        Move to an absolute index. Homing should be performed before use.
        Speed is steps/second
        """
        print("Moving to index: " + str(index))
        self.set_speed(speed)
        self.serial_write(f"P1,IA{self.axis}M" + str(index) + ",R")
        time.sleep(abs(index - self.current_index) / speed + 0.1)
        self.current_index = index

    def move_relative(self,index: int, speed: int):
        """
        Move to an relative index from current index.
        Speed is steps/second
        """
        print("Moving by relative index: " + str(index))
        self.set_speed(speed)
        self.serial_write(f"P1,I{self.axis}M" + str(index) + ",R")
        time.sleep(abs(index ) / speed + 0.1)
        self.current_index += index

    def set_speed(self, speed: int):
        """
        Set move speed, steps/second
        """
        self.serial_write(f"S{self.axis}M" + str(speed) + ",R")
        self.speed = speed

    def pause(self, seconds: float):
        """
        Pause for 'duration' seconds, to the best of the controller's ability.
        Minimum is 1e-4 seconds, maximum is 6553.5 seconds
        """
        if math.floor(seconds * 10.0) >= 65535:
            raise ValueError("Pause is too long, needs to be under 6553.5 seconds")
        elif seconds * 10.0 >= 1.0:
            tenths_of_second = int(math.ceil(seconds * 10.0))
            self.serial_write("P" + str(tenths_of_second))
        elif seconds * 1.0e4 >= 1.0:
            tenths_of_millisecond = int(math.ceil(seconds * 1.0e4))
            self.serial_write("P-" + str(tenths_of_millisecond))
        else:
            raise ValueError("Pause is too short, needs to be over 1.e-4 seconds")

    def loop_move(
        self, tot_dist: float, increments: int, pause: float, direction: str = "+"
    ):
        """
        loops the action of 'rel_move' the number of times given in increments, moving a total distance give by tot_dist input
        inputs:
        port - str - the COM port name that will allow you to interface with the VXM
        tot_dist - float,[mm] - total distance you would like stage to move, realtive to intial stage position
        increments - int - number of stops you would like the stage to take on its journey
        ^ E04 stage can move 0.0254mm/step so you should keep in mind
        pause - float,[sec] - the amount of time you would like to wait before and after each incremental move
        ^ NOTE: now in a loop, VXM is given a 2 pause commands in between each move, so VXM will wait pause*2 seconds in between each move
        ^ minimum amount of time able to wait: 1e-5 sec (10 microseconds),
        direction - direction stage will move, default '+' direction (away from motor)
        """
        # check inputs
        if type(increments) != int:
            raise ValueError("increments input must be integer")
        if not (direction == "+" or direction == "-"):
            raise ValueError("direction input must be + or -")

        # calculate time for VXM inputs, along with time for sleep
        if pause < 0.03:
            p = round(pause / 1.0e-5)  # [*10 microsec]
            time_com = "P-" + str(p)
        else:
            p = round(pause / 0.1)  # [*.1 sec]
            time_com = "P" + str(p)
        z = increments * pause * 2.0 + 1.0  # sec

        # determine steps nessecary for each incremental move
        dps = tot_dist / increments  # dist per increment [mm]
        spi = round(dps / self.step)  # steps per increment [steps]
        if direction == "+":
            mv_com = f"I{self.axis}M" + str(spi)
        elif direction == "-":
            mv_com = f"I{self.axis}M-" + str(spi)

        # comand string
        cmd = time_com + "," + mv_com + "," + time_com + ",L" + str(increments) + ",R"
        print(cmd)

        # open port
        with serial.Serial() as s:
            s.port = self.port
            s.timeout = 0
            s.open()
            s.flushOutput()
            s.write("F,C".encode(encoding="ascii"))
            s.flushOutput()
            s.write(cmd.encode(encoding="ascii"))
            time.sleep(z)
            s.write("C,Q".encode(encoding="ascii"))
            s.close()


if __name__ == "__main__":
    print(serial_ports())
    motor1 = VXMController(axis=1,com_port='COM12')
    userInput = input("Enter Jog Step (+/-100, q to quit): ")
    while userInput != "q":
        motor1.move_absolute(motor1.current_index + int(userInput), 1000)
        userInput = input("Enter Jog Step (+/-100, q to quit): ")

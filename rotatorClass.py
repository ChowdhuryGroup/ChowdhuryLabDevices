from pylablib.devices import Thorlabs
import time
#print(Thorlabs.list_kinesis_devices())

class rotator:

    def __init__(self, serial: str = '27263056'):
        self.stage = Thorlabs.KinesisMotor(serial)
        steps_per_revolution = 512
        gearbox_ratio = 67
        gear_ratio = 20.145

        self.steps_per_degree = steps_per_revolution * gearbox_ratio * gear_ratio / 360

    def move_relative(self, degrees: float, wait: bool = True):
        self.stage.move_by(self.steps_per_degree * degrees)
        if wait:
            self.wait_for_stop()

    def get_position(self):
        return self.stage.get_position()/self.steps_per_degree
    def move_absolute(self, degrees: float):
        self.stage.move_to(self.steps_per_degree * degrees)
    def is_moving(self):
        return self.stage.is_moving()
    def wait_for_stop(self):
        return self.stage.wait_for_stop()
    def close(self):
        self.stage.close()


if __name__ == "__main__":
    rot = rotator()
    rot.move_relative(90)
    rot.wait_for_stop()
    print(rot.get_position())
    rot.move_relative(-90)
    rot.wait_for_stop()
    print(rot.get_position())

    rot.close()
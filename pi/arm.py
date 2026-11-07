"""Shared code for moving the arm safely. Every script should move joints through this."""

# joint: (channel, lowest angle, highest angle)
JOINTS = {
    "claw":     (0, 10, 80),
    "base":     (1, 8, 170),
    "shoulder": (2, 60, 120),
    "elbow":    (3, 50, 130),
}

ADDR = 0x40


def check_angle(joint, angle):
    """Raise ValueError if this joint or angle isn't allowed. Doesn't touch the hardware."""
    if joint not in JOINTS:
        raise ValueError(f"There's no joint called '{joint}'.")
    _, low, high = JOINTS[joint]
    if not low <= angle <= high:
        raise ValueError(f"{angle} is outside the {joint} limits ({low} to {high}).")


class Arm:
    def __init__(self):
        from smbus2 import SMBus  # imported here so the checks above work anywhere
        import time

        self.bus = SMBus(1)
        # set up the board for 50 Hz (servo speed)
        self.bus.write_byte_data(ADDR, 0x00, 0x10)   # sleep
        self.bus.write_byte_data(ADDR, 0xFE, 121)    # 50 Hz
        self.bus.write_byte_data(ADDR, 0x00, 0x20)   # wake up
        time.sleep(0.01)
        self.bus.write_byte_data(ADDR, 0x00, 0xA0)   # restart

    def move(self, joint, angle):
        check_angle(joint, angle)
        channel = JOINTS[joint][0]
        us = 600 + angle / 180 * 1800                # 600..2400 microseconds
        ticks = int(us * 4096 / 20000)
        reg = 0x06 + 4 * channel
        self.bus.write_i2c_block_data(ADDR, reg, [0, 0, ticks & 0xFF, ticks >> 8])

    def release(self, joint):
        channel = JOINTS[joint][0]
        reg = 0x06 + 4 * channel
        self.bus.write_i2c_block_data(ADDR, reg, [0, 0, 0, 0x10])   # power off

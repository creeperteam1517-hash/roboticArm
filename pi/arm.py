"""Shared code for moving the arm safely. Every script should move joints through this."""

# joint: (channel, lowest angle, highest angle)
JOINTS = {
    "claw":     (0, 10, 80),
    "base":     (1, 0, 180),
    "shoulder": (2, 0, 60),     # fitted at servo 0; 0-60 checked by eye on 2026-11-09
    "elbow":    (3, 50, 130),    # 50-130 confirmed on the arm on 2026-11-10
}

# Pulse lengths (microseconds) that 0 and 180 degrees mean for each joint.
# The base was calibrated on 2026-11-08: its hard stop is at about 600, it rests quietly at 650,
# and it moves freely up to 2500. Uncalibrated joints use the common 600..2400.
DEFAULT_PULSE_RANGE = (600, 2400)
PULSE_RANGE = {
    "base": (650, 2500),
}

ADDR = 0x40

# Standard safe pulse range for hobby servos, in microseconds. Calibration pulses must stay inside it.
MIN_PULSE_US = 500
MAX_PULSE_US = 2500

# Smooth motion: a joint glides to its new position in small steps instead of jumping.
# 30 microseconds is about 3 degrees, so a full 180-degree sweep takes about 0.6 seconds.
# The shoulder and elbow glide slower, the same speed up and down.
# The first move after a joint has been relaxed still jumps, because its position isn't known.
GLIDE_STEP_US = 30
GLIDE_STEP_US_BY_JOINT = {"elbow": 15, "shoulder": 8}
GLIDE_STEP_SECONDS = 0.01

# The shoulder and elbow remember their last pulse in PULSE_FILE, so the next script
# glides from there instead of jumping.
REMEMBERED_JOINTS = {"shoulder", "elbow"}
PULSE_FILE = "/tmp/arm_pulses.json"


def check_pulse(us):
    """Raise ValueError if a calibration pulse is outside the safe range. Doesn't touch the hardware."""
    if not MIN_PULSE_US <= us <= MAX_PULSE_US:
        raise ValueError(f"{us} microseconds is outside the safe range ({MIN_PULSE_US} to {MAX_PULSE_US}).")


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
        self.pulse_now = self._load_pulses()   # last pulse sent to each joint that is still powered

    def _load_pulses(self):
        import json
        try:
            with open(PULSE_FILE) as f:
                return {j: float(us) for j, us in json.load(f).items() if j in REMEMBERED_JOINTS}
        except (OSError, ValueError, AttributeError):
            return {}

    def _save_pulses(self):
        import json
        try:
            with open(PULSE_FILE, "w") as f:
                json.dump({j: us for j, us in self.pulse_now.items() if j in REMEMBERED_JOINTS}, f)
        except OSError:
            pass

    def _write_pulse(self, joint, us):
        channel = JOINTS[joint][0]
        ticks = int(us * 4096 / 20000)
        reg = 0x06 + 4 * channel
        self.bus.write_i2c_block_data(ADDR, reg, [0, 0, ticks & 0xFF, ticks >> 8])

    def _glide(self, joint, target_us):
        """Move to target_us in small steps from the last known position, so the motion is smooth."""
        import time

        start = self.pulse_now.get(joint)
        if start is not None:
            step_us = GLIDE_STEP_US_BY_JOINT.get(joint, GLIDE_STEP_US)
            steps = int(abs(target_us - start) // step_us)
            direction = 1 if target_us > start else -1
            for i in range(1, steps + 1):
                self._write_pulse(joint, start + direction * i * step_us)
                time.sleep(GLIDE_STEP_SECONDS)
        self._write_pulse(joint, target_us)
        self.pulse_now[joint] = target_us
        self._save_pulses()

    def move(self, joint, angle):
        check_angle(joint, angle)
        low_us, high_us = PULSE_RANGE.get(joint, DEFAULT_PULSE_RANGE)
        self._glide(joint, low_us + angle / 180 * (high_us - low_us))

    def move_pulse(self, joint, us):
        """Calibration only: send an exact pulse length, within the safe range."""
        if joint not in JOINTS:
            raise ValueError(f"There's no joint called '{joint}'.")
        check_pulse(us)
        self._glide(joint, us)

    def release(self, joint):
        channel = JOINTS[joint][0]
        reg = 0x06 + 4 * channel
        self.bus.write_i2c_block_data(ADDR, reg, [0, 0, 0, 0x10])   # power off
        self.pulse_now.pop(joint, None)
        self._save_pulses()

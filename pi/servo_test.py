"""Move one joint through a list of angles, then release it.

Examples:
  python3 servo_test.py
  python3 servo_test.py --joint base
  python3 servo_test.py --joint claw --angles 45,60,30 --delay 2
"""
import argparse
import sys
import time

# joint: (channel, lowest angle, highest angle, gentle default moves)
JOINTS = {
    "claw":     (0, 10, 80,  [45, 60, 45, 30, 45]),
    "base":     (1, 10, 170, [90, 105, 90, 75, 90]),
    "shoulder": (2, 60, 120, [90, 105, 90, 75, 90]),
    "elbow":    (3, 50, 130, [90, 105, 90, 75, 90]),
}
MIN_DELAY = 0.2
MAX_DELAY = 10

ADDR = 0x40

parser = argparse.ArgumentParser(description="Test one servo joint.")
parser.add_argument("--joint", choices=JOINTS, default="claw")
parser.add_argument("--angles", help="comma-separated angles, like 45,60,30")
parser.add_argument("--delay", type=float, default=1.0,
                    help="seconds to wait after each move")
args = parser.parse_args()

channel, low, high, angles = JOINTS[args.joint]

# Check everything before touching the hardware.
if args.angles:
    try:
        angles = [int(a) for a in args.angles.split(",")]
    except ValueError:
        sys.exit("Angles must be whole numbers, like 45,60,30. Nothing moved.")

for a in angles:
    if not low <= a <= high:
        sys.exit(f"{a} is outside the {args.joint} limits ({low} to {high}). Nothing moved.")

if not MIN_DELAY <= args.delay <= MAX_DELAY:
    sys.exit(f"Delay must be from {MIN_DELAY} to {MAX_DELAY} seconds. Nothing moved.")

from smbus2 import SMBus  # imported here so the checks above work anywhere

bus = SMBus(1)

# set up the board for 50 Hz (servo speed)
bus.write_byte_data(ADDR, 0x00, 0x10)   # sleep
bus.write_byte_data(ADDR, 0xFE, 121)    # 50 Hz
bus.write_byte_data(ADDR, 0x00, 0x20)   # wake up
time.sleep(0.01)
bus.write_byte_data(ADDR, 0x00, 0xA0)   # restart


def move(channel, angle):
    us = 600 + angle / 180 * 1800        # 600..2400 microseconds
    ticks = int(us * 4096 / 20000)
    reg = 0x06 + 4 * channel
    bus.write_i2c_block_data(ADDR, reg, [0, 0, ticks & 0xFF, ticks >> 8])


def release(channel):
    reg = 0x06 + 4 * channel
    bus.write_i2c_block_data(ADDR, reg, [0, 0, 0, 0x10])   # power off


print(f"Testing {args.joint} on channel {channel}")
try:
    for a in angles:
        print("angle", a)
        move(channel, a)
        time.sleep(args.delay)
except KeyboardInterrupt:
    print("Stopped early.")
finally:
    release(channel)
    print("done")

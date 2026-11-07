"""Move one joint through a list of angles, then release it.

Examples:
  python3 servo_test.py
  python3 servo_test.py --joint base
  python3 servo_test.py --joint claw --angles 45,60,30 --delay 2
"""
import argparse
import sys
import time

from arm import Arm, JOINTS, check_angle

# Gentle moves used when you don't choose your own angles.
DEFAULT_ANGLES = {
    "claw":     [45, 60, 45, 30, 45],
    "base":     [90, 105, 90, 75, 90],
    "shoulder": [90, 105, 90, 75, 90],
    "elbow":    [90, 105, 90, 75, 90],
}
MIN_DELAY = 0.2
MAX_DELAY = 10

parser = argparse.ArgumentParser(description="Test one servo joint.")
parser.add_argument("--joint", choices=JOINTS, default="claw")
parser.add_argument("--angles", help="comma-separated angles, like 45,60,30")
parser.add_argument("--delay", type=float, default=1.0,
                    help="seconds to wait after each move")
args = parser.parse_args()

angles = DEFAULT_ANGLES[args.joint]

# Check everything before touching the hardware.
if args.angles:
    try:
        angles = [int(a) for a in args.angles.split(",")]
    except ValueError:
        sys.exit("Angles must be whole numbers, like 45,60,30. Nothing moved.")

try:
    for a in angles:
        check_angle(args.joint, a)
except ValueError as problem:
    sys.exit(f"{problem} Nothing moved.")

if not MIN_DELAY <= args.delay <= MAX_DELAY:
    sys.exit(f"Delay must be from {MIN_DELAY} to {MAX_DELAY} seconds. Nothing moved.")

arm = Arm()
print(f"Testing {args.joint} on channel {JOINTS[args.joint][0]}")
try:
    for a in angles:
        print("angle", a)
        arm.move(args.joint, a)
        time.sleep(args.delay)
except KeyboardInterrupt:
    print("Stopped early.")
finally:
    arm.release(args.joint)
    print("done")

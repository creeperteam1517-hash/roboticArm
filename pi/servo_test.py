"""Move one joint through a list of angles, then release it.

Examples:
  python3 servo_test.py
  python3 servo_test.py --joint base
  python3 servo_test.py --joint claw --angles 45,60,30 --delay 2
  python3 servo_test.py --joint base --pulses 1500,2400 --delay 3   (calibration: exact pulse lengths)
"""
import argparse
import sys
import time

from arm import Arm, JOINTS, check_angle, check_pulse

# Gentle moves used when you don't choose your own angles.
DEFAULT_ANGLES = {
    "claw":     [45, 60, 45, 30, 45],
    "base":     [90, 105, 90, 75, 90],
    "shoulder": [30, 40, 30, 20, 30],
    "elbow":    [90, 105, 90, 75, 90],
}
MIN_DELAY = 0.2
MAX_DELAY = 10

parser = argparse.ArgumentParser(description="Test one servo joint.")
parser.add_argument("--joint", choices=JOINTS, default="claw")
parser.add_argument("--angles", help="comma-separated angles, like 45,60,30")
parser.add_argument("--delay", type=float, default=1.0,
                    help="seconds to wait after each move")
parser.add_argument("--pulses", help="calibration: comma-separated pulse lengths in microseconds, like 1500,2400")
args = parser.parse_args()

if args.pulses:
    # Calibration mode: exact pulse lengths, checked against the servo-safe range, not the angle limits.
    if args.angles:
        sys.exit("Use either angles or pulses, not both. Nothing moved.")
    try:
        pulses = [int(p) for p in args.pulses.split(",")]
        for p in pulses:
            check_pulse(p)
    except ValueError as problem:
        sys.exit(f"{problem} Pulses must be whole numbers, like 1500,2400. Nothing moved.")
    if not MIN_DELAY <= args.delay <= MAX_DELAY:
        sys.exit(f"Delay must be from {MIN_DELAY} to {MAX_DELAY} seconds. Nothing moved.")
    arm = Arm()
    print(f"Calibrating {args.joint} on channel {JOINTS[args.joint][0]}")
    try:
        for p in pulses:
            print("pulse", p)
            arm.move_pulse(args.joint, p)
            time.sleep(args.delay)
    except KeyboardInterrupt:
        print("Stopped early.")
    finally:
        arm.release(args.joint)
        print("done")
    sys.exit(0)

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

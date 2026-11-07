"""Run a named move from moves.py, then release the joints it used.

Examples:
  python3 run_move.py list
  python3 run_move.py claw_wiggle
  python3 run_move.py claw_wiggle --delay 2
"""
import argparse
import sys
import time

from arm import Arm, check_angle
from moves import DELAYS, MOVES

DEFAULT_DELAY = 1.0
MIN_DELAY = 0.2
MAX_DELAY = 10

parser = argparse.ArgumentParser(description="Run a named arm move.")
parser.add_argument("move", nargs="?", default="list",
                    help="the move's name, or 'list' to see them all")
parser.add_argument("--delay", type=float,
                    help="seconds to wait after each step")
args = parser.parse_args()

if args.move == "list":
    print("Moves you can run:")
    for name in MOVES:
        print(" ", name)
    sys.exit(0)

# Check everything before touching the hardware.
if args.move not in MOVES:
    sys.exit(f"There's no move called '{args.move}'. Run 'list' to see them. Nothing moved.")

steps = MOVES[args.move]
try:
    for joint, angle in steps:
        check_angle(joint, angle)
except ValueError as problem:
    sys.exit(f"{problem} Nothing moved.")

delay = args.delay if args.delay is not None else DELAYS.get(args.move, DEFAULT_DELAY)
if not MIN_DELAY <= delay <= MAX_DELAY:
    sys.exit(f"Delay must be from {MIN_DELAY} to {MAX_DELAY} seconds. Nothing moved.")

arm = Arm()
print(f"Running {args.move}")
try:
    for joint, angle in steps:
        print(joint, angle)
        arm.move(joint, angle)
        time.sleep(delay)
except KeyboardInterrupt:
    print("Stopped early.")
finally:
    for joint in {joint for joint, _ in steps}:
        arm.release(joint)
    print("done")

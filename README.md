# Robotic Arm

A hobby project to build a 3D-printed EEZYbotARM Mk2 that picks up and places objects using a camera. A Windows PC sends commands to a Raspberry Pi 5, and the Pi moves the servos through a PCA9685 driver board.

## Status

This is a work in progress.

| Part | Status |
|---|---|
| Sending commands from the PC to the Pi | Working |
| Claw | Moved on real hardware, from 10 to 80 degrees |
| Base | Moved on real hardware, from 8 to 170 degrees, but sometimes doesn't move |
| Shoulder and elbow | Not tested yet |
| Smooth motion | Planned |
| Chat front end and camera pick-and-place | Planned |

## Hardware

- Raspberry Pi 5 running Raspberry Pi OS, with I2C and SSH turned on
- PCA9685 16-channel servo driver
- 4 servos, powered by a separate 6V supply through a 5A fuse

| Joint | Channel | Allowed angles |
|---|---|---|
| Claw | 0 | 10 to 80 |
| Base | 1 | 8 to 170 |
| Shoulder | 2 | 60 to 120 |
| Elbow | 3 | 50 to 130 |

Only the claw and base ranges have been tried on real hardware. The shoulder and elbow limits still need measuring.

### Wiring

| Raspberry Pi | PCA9685 |
|---|---|
| Pin 1 (3.3V) | VCC |
| Pin 3 (SDA) | SDA |
| Pin 5 (SCL) | SCL |
| Pin 6 (GND) | GND |

Connect the 6V supply to the PCA9685 power block. **Check the polarity with a multimeter before connecting servos,** because the fuse doesn't protect against reversed power.

## Setup

The commands below run on a Windows PC, from the project folder.

1. Download the project:

   ```bash
   git clone https://github.com/creeperteam1517-hash/roboticArm.git
   cd roboticArm
   ```

2. Set up password-free login to the Pi. You only need to do this once on each PC:

   ```bash
   .\setup_ssh
   ```

3. Copy the code to the Pi. This also installs anything missing, and doesn't move the arm:

   ```bash
   .\deploy
   ```

The scripts use this project's Pi name and username by default. For a different Pi, add `-PiAddress <address>` and `-PiUser <username>` to any of these commands.

## Usage

**These commands can move the arm.** Keep your fingers clear, and press Ctrl+C to stop early.

```bash
.\arm claw_wiggle
.\test_servo -Joint base
.\test_servo -Joint claw -Angles 45,60,30 -Delay 2
```

To list the named moves without moving the arm:

```bash
.\arm
```

Angles outside a joint's limits are refused before anything moves. Each joint is released when its move ends.

## Adding a move

1. Add a name and its steps to `pi/moves.py`:

   ```python
   "my_move": [("claw", 30), ("claw", 60)],
   ```

2. Copy it to the Pi with `.\deploy`.
3. Run it with `.\arm my_move`.

## Project layout

| Path | What it is |
|---|---|
| `pi/arm.py` | Shared servo control and joint limits |
| `pi/moves.py` | Named moves |
| `pi/run_move.py` | Runs a named move on the Pi |
| `pi/servo_test.py` | Tests one joint on the Pi |
| `arm.cmd`, `test_servo.cmd`, `deploy.cmd`, `setup_ssh.cmd` | The commands you run on the PC |
| `tools/` | The PowerShell scripts behind those commands |
| `brain.md` | Detailed project notes and next steps |
| `CLAUDE.md` | Instructions for Claude Code |

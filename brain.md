# PROJECT HANDOFF: Vision-guided robot arm with Jarvis as the front end

## ME
- Hobbyist, beginner with electronics. Please go ONE small step at a time, plain English, exact commands, no long code for me to type (write files for me instead). I get scared and frustrated easily, so reassure me kindly. I like real photos or clear images over diagrams.

## GOAL
- Build a 3D-printed EEZYbotARM Mk2 (printed on a Bambu P2S) that does vision-guided pick-and-place.
- "Jarvis" is the front end (a chat/console page I built earlier with Claude): https://claude.ai/artifact/2xNeQuiwphvp232UuiJmPW
- Jarvis sends commands to code running on the Raspberry Pi, and the Pi moves the arm.

## HARDWARE
- Raspberry Pi 5, Raspberry Pi OS 64-bit
  - Hostname: the-coolest-raspberry-pi
  - Username: groot_the_builder (lowercase)
  - SSH is enabled. I2C is enabled.
- PCA9685 16-channel servo driver (blue board)
- 4 servos on the arm:
  - claw (SG90) on channel 0
  - base on channel 1
  - shoulder on channel 2
  - elbow on channel 3
- Old joint limits (degrees): base 10-170, claw 10-80, shoulder 60-120, elbow 50-130
- Servo power: 6V DC wall supply (black, green screw-terminal plug, no +/- marks)
  - Path: supply + -> 5A fuse in an inline holder -> PCA9685 V+ (right screw)
  - Supply - -> PCA9685 GND (left screw)
- The Arduino Uno is dead (reversed polarity), so we switched to the Pi + PCA9685.
- Planned: Pi Camera Module 3 or a USB webcam for vision.
- Budget: about $200 or more.

## WIRING (Pi to PCA9685)
- Pin 1 (3.3V) -> VCC
- Pin 3 (SDA) -> SDA
- Pin 5 (SCL) -> SCL
- Pin 6 (GND) -> GND
- OE and V+ on the logic side are left empty. Don't use 5V pins 2/4.
- Verified: `sudo i2cdetect -y 1` shows 40 (PCA9685) and 70 (all-call).

## STATUS
- Done: I2C wiring verified. 6V supply, fuse and holder wired to the PCA9685 power block.
- **Power polarity not measured yet.** The claw moving is a good sign that it's right, but I chose to skip the meter check, so there's still no reading. Please have me measure DC volts at the PCA9685 V+ (right) and GND (left) with the servo UNPLUGGED. Black probe on GND, red on V+. It should read about +6 (a minus sign means reversed). A fuse does not protect against reversed polarity.
- Multimeter: KAIWEETS KM100, dial on 20 in the DC V section, black probe in COM, red probe in VOmA.
- Done: SSH key login works from my PC. pi/servo_test.py is on the Pi in ~/roboticArm. python3-smbus2 is installed.
- Done on 2026-11-06: the claw (channel 0) moved in the gentle test. An earlier run that same night finished without errors but the claw didn't move, and the cause is unknown. If it happens again, check the 6V power first.
- The claw moved from 10 to 80 with no strain on 2026-11-06, so the claw limits look okay for now.
- The base (channel 1) moved from 10 to 170 with no strain on 2026-11-06, so the base limits look okay for now.
- **The base sometimes doesn't move, even though the script finishes without errors.** It happened in `.\arm wave`, and again in the base sweep right after five claw claps (right after a Pi restart). The base-only sweep moved straight after that. Cause unknown. Next: with the 6V supply unplugged, check the base servo's plug and wires for a loose connection. Then check the power, because the 6V supply is still unmeasured.
- On 2026-11-07 the base once stopped short of 170 during `-Angles 10,170 -Delay 10`, cause unknown. Later, moving to 10 and then to 170 as two separate commands with a 1-second wait reached 170. Commands can't send 180, because the limit is 170.
- The base's lowest limit in pi/arm.py is now 8, confirmed with no strain on 2026-11-07. A move to 6 ran, but I didn't report how it looked. A try at 0 showed no movement, so 0 is unconfirmed. I remember reaching 0 before.
- On 2026-11-07 the Pi stopped answering on the network, and restarting it fixed that. Cause unknown. The Pi's .local name also only works some of the time, so use `-PiAddress 10.0.0.171` if it fails.
- Not done: shoulder and elbow haven't been tested.
- Old servos may have been stressed by the earlier reverse-polarity incident, so test each one.

## CURRENT BLOCKER
- No blockers right now. Worth measuring power polarity (see STATUS) before connecting the other servos.
- To do soon: change the Pi password with `passwd`, because it was accidentally pasted into a Claude chat.

## DEPLOYING TO THE PI
- Code for the Pi lives in the `pi/` folder. It gets copied to `~/roboticArm` on the Pi.
- Run these from the project folder in a terminal on my PC.
- First time only: `.\setup_ssh` (asks for the Pi password once).
- Every time: `.\deploy` copies the files, installs missing packages and restarts the Jarvis page. It doesn't move the arm.
- To also run a script: `.\deploy -Run servo_test.py`. This can move the arm. Check polarity first.
- If the name doesn't work, add `-PiAddress <the Pi's IP>` to either command.
- Tested on the real Pi on 2026-11-06, at 10.0.0.171 on my home Wi-Fi. That address could change. If so, get the new one with `hostname -I` on the Pi.
- The `.cmd` files are launchers, so the scripts in `tools/` run without changing the Windows script security setting.
- Possible later addition: Tailscale, to reach the Pi from any location.

## USING ANOTHER COMPUTER (Windows)
1. Install Git and Claude Code. Windows already includes SSH.
2. Run `git clone https://github.com/creeperteam1517-hash/roboticArm.git`, then `cd roboticArm`.
3. Run `.\setup_ssh` once on that computer. I type the Pi's password in the terminal.
4. Run `.\arm` to list the moves. This doesn't move the arm, and it proves the login works.
- The computer and the Pi must be on the same network, unless Tailscale is set up.
- The scripts don't run on Mac or Linux. Claude would need to write versions for that system.

## MOVING THE PI TO A NEW LOCATION
- The Pi only joins Wi-Fi it already knows, and I may not have a screen there. Before leaving, add the new Wi-Fi details, or a phone hotspot as a backup.
- The address 10.0.0.171 only applies to my home network. Try the Pi's name first. If that fails, find the Pi in the router's or hotspot's device list, then add `-PiAddress <address>` to commands.
- Optional: install Tailscale before leaving, to reach the Pi from anywhere while it's online.

## SERVO TEST
pi/servo_test.py moves one joint through a list of angles, then releases it. It refuses angles outside the old joint limits before anything moves. The real limits still need measuring.

Run from my PC, without copying files first. This can move the arm:

```
.\test_servo
.\test_servo -Joint base
.\test_servo -Joint claw -Angles 45,60,30 -Delay 2
```

Add `-PiAddress 10.0.0.171` if the name doesn't work. If the script has changed, run `.\deploy` first.

## JARVIS WEB PAGE
- Open http://10.0.0.171:8000 in a browser on the same network. No monitor is needed on the Pi. The `the-coolest-raspberry-pi.local` name also works at port 8000 when the name is working.
- It has routine buttons, a slider for each joint, and a Stop button. Loading the page never moves the arm. Shoulder and elbow stay locked until I unlock them.
- A slider holds its position for 10 seconds, then relaxes. Stop cancels the move and relaxes all servos, so a raised arm may drop.
- Files: pi/jarvis_server.py, pi/jarvis.html, pi/jarvis.service. It runs as a user service on the Pi, so `.\deploy` copies and restarts it without a password. It's set to start when the Pi turns on, but that hasn't been tested with a restart yet.
- It has no password, so anyone on the Wi-Fi can use it. Keep it off the public internet. It refuses commands sent from other websites.
- This is separate from the older Jarvis chat page on claude.ai, which isn't connected to it yet.

## NAMED MOVES
- pi/arm.py is the shared code that moves joints and enforces the limits. Every script should use it.
- pi/moves.py holds the named moves. To add one, add a name and its (joint, angle) steps, then run `.\deploy`.
- `.\arm` lists the moves. `.\arm claw_wiggle` runs one and can move the arm. `-Delay 2` waits longer after each step.
- `.\arm claw_wiggle` moved the real claw on 2026-11-06.
- Moves so far are `claw_wiggle`, `clap` (claw 10 to 80, five times), `wave` and `base_sweep` (base), and `victory_dance` (three claps, then a base swing). To add a move, change pi/moves.py and run `.\deploy`. Its button appears on the Jarvis page by itself. Shoulder and elbow haven't been tested, so they have no moves yet. There's no smooth motion yet.
- Possible later addition: a Claude skill that runs these moves, only when I ask for it directly.

The claw servo goes on channel 0: orange/yellow wire on the yellow pin, red in the middle, brown/black on the black pin. 6V supply on.

## NEXT STEPS
1. Confirm polarity with the meter.
2. Test the other servos one at a time (base ch1, shoulder ch2, elbow ch3) with `.\test_servo -Joint base` and so on. Measure the real joint limits.
3. Add smooth motion and moves for all four joints to pi/arm.py and pi/moves.py (limits are done). The old Arduino protocol was B/C/E/H<angle> (base/claw/elbow/shoulder), V<ms per degree>, S (stop), X (release).
4. Connect the older Jarvis chat page to the Jarvis server on the Pi, if I still want that. The Jarvis web page on the Pi already works for button and slider control.
5. Add the camera and vision-guided pick-and-place.
6. Later: redesign the printed plinth for the new hardware.

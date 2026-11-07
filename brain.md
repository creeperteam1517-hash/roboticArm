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
- **NOT verified: power polarity.** I said it was right, but I never gave a multimeter reading. Please have me measure DC volts at the PCA9685 V+ (right) and GND (left) with the servo UNPLUGGED. Black probe on GND, red on V+. It should read about +6 (a minus sign means reversed). A fuse does not protect against reversed polarity.
- Multimeter: KAIWEETS KM100, dial on 20 in the DC V section, black probe in COM, red probe in VOmA.
- Not done: the servo test has never been run on hardware. Whether python3-smbus2 is installed on the Pi is unknown.
- Old servos may have been stressed by the earlier reverse-polarity incident, so test each one.

## CURRENT BLOCKER
- servo_test.py (below) is only on my Windows PC and needs to get onto the Pi.
- I'm at a different location than the Pi. Windows can't resolve the Pi's .local name, and I have no Pi screen, USB drive or Ethernet cable here.
- Options: wait until I'm back on the home Wi-Fi, then use `scp` (get the IP with `hostname -I` on the Pi). Or use a phone hotspot.
- If Claude Code runs on my PC, it may be easiest to have it write the file and scp it over once the networks match.

## servo_test.py
Moves the claw on channel 0 in small steps, then releases it.

```python
import time
from smbus2 import SMBus

ADDR = 0x40
bus = SMBus(1)

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

CH = 0
try:
    for a in (45, 60, 45, 30, 45):
        print("angle", a)
        move(CH, a)
        time.sleep(1)
finally:
    release(CH)
    print("done")
```

Run with:

```
sudo apt install -y python3-smbus2 && python3 servo_test.py
```

The claw servo goes on channel 0: orange/yellow wire on the yellow pin, red in the middle, brown/black on the black pin. 6V supply on.

## NEXT STEPS
1. Get servo_test.py onto the Pi and run it. First confirm polarity with the meter.
2. Test the other servos one at a time (base ch1, shoulder ch2, elbow ch3). Measure the real joint limits.
3. Write a Pi control script for all four joints with limits and smooth motion. The old Arduino protocol was B/C/E/H<angle> (base/claw/elbow/shoulder), V<ms per degree>, S (stop), X (release).
4. Add a small local server on the Pi so Jarvis can send commands. The hosted claude.ai page can't use USB or Web Serial, so it needs a local web page or network API.
5. Add the camera and vision-guided pick-and-place.
6. Later: redesign the printed plinth for the new hardware.

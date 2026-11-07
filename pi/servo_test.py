import time
from smbus2 import SMBus

ADDR = 0x40
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

CH = 0   # channel 0 = the claw servo
try:
    for a in (45, 60, 45, 30, 45):       # small, gentle moves
        print("angle", a)
        move(CH, a)
        time.sleep(1)
finally:
    release(CH)
    print("done")

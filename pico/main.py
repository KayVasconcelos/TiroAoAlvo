# main.py - MicroPython code for Raspberry Pi Pico W
# Usage: copy to Pico (Thonny) as main.py

import machine
import sys
import time
import uselect

# - botão -> GP16
# - LED vermelho (miss) -> GP15
# - LED azul (hit) -> GP12
BTN_PIN = 16        # button input (GP16)
LED_RED = 15        # red LED for miss (GP15)
LED_BLUE = 12       # blue LED for hit (GP12)

# Setup pins
# Pins setup
# Use internal pull-up so the button can be connected to GND when pressed.
# This matches the wiring instructions where the button connects GP16 to GND.
btn = machine.Pin(BTN_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
led_red = machine.Pin(LED_RED, machine.Pin.OUT)
led_blue = machine.Pin(LED_BLUE, machine.Pin.OUT)

# Serial poll for incoming lines from host
poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

# Helper function to flash LED
def flash_led(pin, duration=0.25):
    """Flash an LED for the given duration (seconds)"""
    pin.on()
    time.sleep(duration)
    pin.off()

# State variables
last_btn = 1  # with PULL_UP the idle state is 1
score = 0

# Signal that Pico is ready
print('PICO_READY')

# Main loop
while True:
    # Check button press 
    v = btn.value()
    if (not v) and last_btn:
        # Simple debounce
        time.sleep(0.1)
        if not btn.value():
            # Send FIRE event to PC
            try:
                print('FIRE')
            except Exception:
                pass
    last_btn = v

    # Check serial incoming from PC
    if poll.poll(0):
        try:
            line = sys.stdin.readline()
            if not line:
                continue
            line = line.strip()
            # Expected messages: HIT <score> or MISS <score>
            if line.startswith('HIT'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        score = int(parts[1])
                    except:
                        pass
                # Flash blue LED for successful hit
                flash_led(led_blue, 0.25)
                print(f'SCORE:{score}')
            elif line.startswith('MISS'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        score = int(parts[1])
                    except:
                        pass
                # Flash red LED for miss
                flash_led(led_red, 0.25)
                print(f'SCORE:{score}')
        except Exception:
            # Ignore errors
            pass

    time.sleep(0.01)

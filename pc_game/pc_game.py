# pc_game.py - Pygame host that communicates with Pico via serial
# Usage: python pc_game.py COM4

import pygame
import threading
import queue
import serial
import sys
import time

# Configuration
WINDOW_W = 640
WINDOW_H = 480
TARGET_SIZE = 40
TARGET_SPEED = 120  # pixels per second

# Serial port 
if len(sys.argv) >= 2:
    SERIAL_PORT = sys.argv[1]
else:
    SERIAL_PORT = input('Enter serial port (e.g. COM3): ')

BAUD = 115200

# Thread-safe queues
serial_in_q = queue.Queue()
fire_q = queue.Queue()

# open serial
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
except Exception as e:
    print('Could not open serial port:', e)
    ser = None

# Thread to read serial lines
def serial_reader():
    if not ser:
        return
    buf = b''
    while True:
        try:
            data = ser.read(64)
            if data:
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    line = line.decode('utf-8', errors='ignore').strip()
                    serial_in_q.put(line)
            else:
                time.sleep(0.01)
        except Exception:
            time.sleep(0.1)

# Start reader thread
if ser:
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

# Pygame init
pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

# Game state
target_x = 100
target_y = 120
target_dir = 1
score = 0

# shooter position
shooter_x = WINDOW_W // 2
shooter_y = WINDOW_H - 60

# Crosshair rectangle for hit detection
CROSS_RADIUS = 30
# Bullet settings
BULLET_SPEED = 480  # pixels per second 
BULLET_RADIUS = 6

running = True

# Process serial input messages from Pico
def process_serial_messages():
    global running
    while not serial_in_q.empty():
        line = serial_in_q.get()
        # Pico prints 'PICO_READY' and 'FIRE'
        if line == 'FIRE':
            # enqueue a fire event for main loop
            fire_q.put('FIRE')
        elif line == 'PICO_READY':
            print('Pico ready')
        else:
            # ignore other messages
            pass

# Send result back to Pico
def send_result(hit, score):
    if not ser:
        return
    try:
        if hit:
            ser.write(f'HIT {score}\n'.encode())
        else:
            ser.write(f'MISS {score}\n'.encode())
    except Exception as e:
        pass

# Main loop
last_time = time.time()
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                # local shoot for testing
                fire_q.put('FIRE')

    # read serial messages
    process_serial_messages()

    # update target
    target_x += target_dir * TARGET_SPEED * dt
    if target_x < 0:
        target_x = 0
        target_dir = 1
    elif target_x > WINDOW_W - TARGET_SIZE:
        target_x = WINDOW_W - TARGET_SIZE
        target_dir = -1

    # handle fire events: spawn bullets instead of immediate hit test
    # bullets is a list of dicts: {'x','y','vy'}
    try:
        bullets
    except NameError:
        bullets = []

    while not fire_q.empty():
        _ = fire_q.get()
        # spawn a bullet at shooter position
        bullets.append({'x': float(shooter_x), 'y': float(shooter_y), 'vy': -BULLET_SPEED})

    # update bullets
    for b in list(bullets):
        b['y'] += b['vy'] * dt
        # check collision with target (circle vs circle)
        target_center = (target_x + TARGET_SIZE/2, target_y + TARGET_SIZE/2)
        dx = target_center[0] - b['x']
        dy = target_center[1] - b['y']
        dist = (dx*dx + dy*dy) ** 0.5
        if dist <= (BULLET_RADIUS + TARGET_SIZE/2):
            # hit
            score += 1
            send_result(True, score)
            try:
                bullets.remove(b)
            except ValueError:
                pass
            continue
        # if bullet passed above target (miss)
        if b['y'] < -BULLET_RADIUS:
            send_result(False, score)
            try:
                bullets.remove(b)
            except ValueError:
                pass

    # draw
    screen.fill((30, 30, 40))
    # draw target
    pygame.draw.circle(screen, (200, 60, 60), (int(target_x+TARGET_SIZE/2), int(target_y+TARGET_SIZE/2)), TARGET_SIZE//2)
    # draw shooter
    pygame.draw.rect(screen, (80,160,80), (shooter_x-20, shooter_y, 40, 40))
    # draw crosshair range
    pygame.draw.circle(screen, (200,200,200), (shooter_x, shooter_y), CROSS_RADIUS, 1)

    # draw bullets
    for b in bullets:
        pygame.draw.circle(screen, (255, 220, 60), (int(b['x']), int(b['y'])), BULLET_RADIUS)

    # draw score
    txt = font.render(f'Score: {score}', True, (240,240,240))
    screen.blit(txt, (10, 10))

    pygame.display.flip()

pygame.quit()
if ser:
    ser.close()

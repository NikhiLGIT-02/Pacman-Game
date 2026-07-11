# -*- coding: utf-8 -*-
"""
Pac-Man Cyber Redux
===================
A visually enhanced, high-performance Pac-Man game built in Python and Pygame.
Featuring smooth grid-interpolation transitions, dynamic ghost AI mimicking the
original 1980 arcade algorithms, real-time diagnostic telemetry, sound synthesis
via byte-buffer generation, and a gorgeous modern neon vector aesthetic.

To run:
    pip install pygame
    python main.py
"""

import sys
import os
import math
import json
import struct
import random
from enum import Enum
import pygame

# Initialize Pygame systems
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

# --- CONSTANTS & CONFIGURATION ---
TILE_SIZE = 28
GRID_COLS = 19
GRID_ROWS = 21

MAP_GRID = [
    ["W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W"],
    ["W","O",".",".",".",".",".",".",".","W",".",".",".",".",".",".",".","O","W"],
    ["W",".","W","W",".","W","W","W",".","W",".","W","W","W",".","W","W",".","W"],
    ["W",".","W","W",".","W","W","W",".","W",".","W","W","W",".","W","W",".","W"],
    ["W",".",".",".",".",".",".",".",".",".",".",".",".",".",".",".",".",".","W"],
    ["W",".","W","W",".","W",".","W","W","W","W","W",".","W",".","W","W",".","W"],
    ["W",".",".",".",".","W",".",".",".","W",".",".",".","W",".",".",".",".","W"],
    ["W","W","W","W",".","W","W","W",".","W",".","W","W","W",".","W","W","W","W"],
    ["_","_","_","W",".","W","_","_","_","_","_","_","_","W",".","W","_","_","_"],
    ["W","W","W","W",".","W","_","W","W","-","W","W","_","W",".","W","W","W","W"],
    ["T","_","_","_",".","_","_","W","H","H","H","W","_","_",".","_","_","_","T"],
    ["W","W","W","W",".","W","_","W","W","W","W","W","_","W",".","W","W","W","W"],
    ["_","_","_","W",".","W","_","_","_","_","_","_","_","W",".","W","_","_","_"],
    ["W","W","W","W",".","W",".","W","W","W","W","W",".","W",".","W","W","W","W"],
    ["W",".",".",".",".",".",".",".",".","W",".",".",".",".",".",".",".",".","W"],
    ["W",".","W","W",".","W","W","W",".","W",".","W","W","W",".","W","W",".","W"],
    ["W","O",".","W",".",".",".",".",".","P",".",".",".",".",".","W",".","O","W"],
    ["W","W",".","W",".","W",".","W","W","W","W","W",".","W",".","W",".","W","W"],
    ["W",".",".",".",".","W",".",".",".","W",".",".",".","W",".",".",".",".","W"],
    ["W",".","W","W","W","W","W","W",".","W",".","W","W","W","W","W","W",".","W"],
    ["W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W","W"]
]

class Direction(Enum):
    NONE = (0, 0)
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class GhostType(Enum):
    BLINKY = "BLINKY"
    PINKY = "PINKY"
    INKY = "INKY"
    CLYDE = "CLYDE"

class GhostMode(Enum):
    CHASE = "CHASE"
    SCATTER = "SCATTER"
    FRIGHTENED = "FRIGHTENED"
    EATEN = "EATEN"

# Theme definitions
THEMES = {
    "CYBER_NEON": {
        "background": (4, 2, 13),
        "grid_bg": (9, 5, 20),
        "wall_color": (189, 0, 255),
        "wall_glow": (0, 255, 255),
        "pellet_color": (0, 255, 204),
        "power_pellet_color": (255, 0, 85),
        "pacman_color": (255, 255, 0)
    },
    "RETRO_CLASSIC": {
        "background": (0, 0, 0),
        "grid_bg": (0, 0, 0),
        "wall_color": (33, 33, 222),
        "wall_glow": (0, 0, 0),
        "pellet_color": (255, 184, 174),
        "power_pellet_color": (255, 184, 174),
        "pacman_color": (255, 255, 0)
    }
}

DIFFICULTY = {
    "EASY": {
        "pacman_speed": 0.08,
        "ghost_speed": 0.065,
        "frightened_speed": 0.04,
        "frightened_duration": 8000,
        "scatter_duration": 9000,
        "chase_duration": 20000,
    },
    "NORMAL": {
        "pacman_speed": 0.10,
        "ghost_speed": 0.085,
        "frightened_speed": 0.05,
        "frightened_duration": 6000,
        "scatter_duration": 7000,
        "chase_duration": 20000,
    },
    "HARD": {
        "pacman_speed": 0.12,
        "ghost_speed": 0.11,
        "frightened_speed": 0.06,
        "frightened_duration": 4000,
        "scatter_duration": 5000,
        "chase_duration": 25000,
    }
}

SCATTER_ANCHORS = {
    GhostType.BLINKY: (GRID_COLS - 1, -2),
    GhostType.PINKY: (0, -2),
    GhostType.INKY: (GRID_COLS - 1, GRID_ROWS + 2),
    GhostType.CLYDE: (0, GRID_ROWS + 2)
}

# --- SYNTHESIZED SOUND MODULE ---
# Pure Python math synthesis loaded straight to Pygame byte channels
class RetroSynthEngine:
    def __init__(self):
        self.muted = False
        self.sample_rate = 44100
        self.siren_playing = False
        self._cache = {}

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.stop()

    def play(self, sound_name, generator_fn):
        if self.muted:
            return
        if sound_name not in self._cache:
            self._cache[sound_name] = generator_fn()
        self._cache[sound_name].play()

    def generate_waka(self):
        duration = 0.08
        num_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / self.sample_rate
            # Classic frequency squelch sweep
            if t < duration * 0.4:
                freq = 320 + (540 - 320) * (t / (duration * 0.4))
            else:
                freq = 540 - (540 - 220) * ((t - duration * 0.4) / (duration * 0.6))
            val = int(32767 * 0.08 * math.sin(2 * math.pi * freq * t))
            buf.extend(struct.pack('<h', val))
        # Create stereo sound (2 channels)
        stereo_buf = bytearray()
        for j in range(0, len(buf), 2):
            sample = buf[j:j+2]
            stereo_buf.extend(sample * 2)
        return pygame.mixer.Sound(buffer=bytes(stereo_buf))

    def generate_power(self):
        duration = 0.2
        num_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / self.sample_rate
            # High pitch chime sweep upwards
            freq = 880 * (2 ** (t / duration))
            val = int(32767 * 0.08 * math.sin(2 * math.pi * freq * t))
            buf.extend(struct.pack('<h', val))
        stereo_buf = bytearray()
        for j in range(0, len(buf), 2):
            sample = buf[j:j+2]
            stereo_buf.extend(sample * 2)
        return pygame.mixer.Sound(buffer=bytes(stereo_buf))

    def generate_eat_ghost(self):
        duration = 0.35
        num_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / self.sample_rate
            # High-intensity pitch ramp combined sweep
            freq1 = 440 + (1200 - 440) * (t / duration)
            freq2 = 600 + (1500 - 600) * (t / duration)
            v1 = math.sin(2 * math.pi * freq1 * t)
            v2 = math.sin(2 * math.pi * freq2 * t)
            val = int(32767 * 0.1 * (v1 + v2) / 2)
            buf.extend(struct.pack('<h', val))
        stereo_buf = bytearray()
        for j in range(0, len(buf), 2):
            sample = buf[j:j+2]
            stereo_buf.extend(sample * 2)
        return pygame.mixer.Sound(buffer=bytes(stereo_buf))

    def generate_death(self):
        duration = 1.1
        num_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(num_samples):
            t = i / self.sample_rate
            # Comedic descending synthesizer slide with pitch wobble (LFO)
            base_freq = 800 - 760 * (t / duration)
            lfo_wobble = 25 * math.sin(2 * math.pi * 15 * t)
            freq = max(30, base_freq + lfo_wobble)
            
            # Sawtooth wave simulation
            saw_phase = (t * freq) % 1.0
            val = int(32767 * 0.12 * (1.0 - t / duration) * (2.0 * saw_phase - 1.0))
            buf.extend(struct.pack('<h', val))
        stereo_buf = bytearray()
        for j in range(0, len(buf), 2):
            sample = buf[j:j+2]
            stereo_buf.extend(sample * 2)
        return pygame.mixer.Sound(buffer=bytes(stereo_buf))

    def play_fanfare(self):
        if self.muted:
            return
        # Sequence notes sequentially inside a separate thread or blocking on first load
        # To avoid lagging Pygame, we synthesize a single continuous 2.5-second fanfare sound!
        # Note frequencies for theme: B4, B5, F#5, D#5, etc.
        tempo = 0.085
        notes = [
            (493.88, 1), (987.77, 1), (739.99, 1), (622.25, 1), (987.77, 0.5), (739.99, 0.5), (622.25, 2), (0, 1),
            (523.25, 1), (1046.5, 1), (783.99, 1), (659.25, 1), (1046.5, 0.5), (783.99, 0.5), (659.25, 2), (0, 1),
            (493.88, 1), (987.77, 1), (739.99, 1), (622.25, 1), (987.77, 0.5), (739.99, 0.5), (622.25, 2), (0, 1),
            (622.25, 0.5), (659.25, 0.5), (698.46, 1), (698.46, 0.5), (739.99, 0.5), (783.99, 1), (783.99, 0.5), (830.61, 0.5), (880.00, 1), (987.77, 2)
        ]
        
        total_duration = sum(d for _, d in notes) * tempo
        num_samples = int(self.sample_rate * total_duration)
        buf = bytearray()
        
        current_sample = 0
        for freq, duration_multiplier in notes:
            note_duration = duration_multiplier * tempo
            note_samples = int(self.sample_rate * note_duration)
            for j in range(note_samples):
                t = j / self.sample_rate
                if freq == 0:
                    val = 0
                else:
                    # Triangle wave shape
                    triangle_val = 2.0 * abs(2.0 * ((t * freq) % 1.0) - 1.0) - 1.0
                    decay = max(0.0, 1.0 - (j / note_samples))
                    val = int(32767 * 0.07 * triangle_val * decay)
                buf.extend(struct.pack('<h', val))
                current_sample += 1
                
        # Fill remaining samples to match size
        while current_sample < num_samples:
            buf.extend(struct.pack('<h', 0))
            current_sample += 1

        stereo_buf = bytearray()
        for k in range(0, len(buf), 2):
            sample = buf[k:k+2]
            stereo_buf.extend(sample * 2)

        fanfare_sound = pygame.mixer.Sound(buffer=bytes(stereo_buf))
        fanfare_sound.play()

synth = RetroSynthEngine()

# --- ENTITY DATA STRUCTURES ---
class Pacman:
    def __init__(self, x, y, speed):
        self.x = float(x)
        self.y = float(y)
        self.grid_x = int(x)
        self.grid_y = int(y)
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE
        self.speed = speed
        self.mouth_angle = 0.0
        self.mouth_closing = False
        self.is_dying = False
        self.death_frame = 0

class Ghost:
    def __init__(self, ghost_type, name, color, x, y, speed, scatter_target, respawn_delay=0):
        self.type = ghost_type
        self.name = name
        self.color = color
        self.x = float(x)
        self.y = float(y)
        self.grid_x = int(x)
        self.grid_y = int(y)
        self.direction = Direction.UP
        self.next_direction = Direction.NONE
        self.mode = GhostMode.SCATTER
        self.speed = speed
        self.scatter_target = scatter_target
        self.respawn_timer = respawn_delay
        self.frightened_timer = 0

class Particle:
    def __init__(self, px, py, color):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.0, 3.5)
        self.x = float(px)
        self.y = float(py)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.alpha = 255
        self.size = random.uniform(2.0, 4.0)
        self.life = 0
        self.max_life = random.randint(20, 35)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life += 1
        self.alpha = max(0, int(255 * (1.0 - self.life / self.max_life)))
        return self.life < self.max_life

class FloatingScore:
    def __init__(self, px, py, text, color):
        self.x = px
        self.y = py
        self.text = text
        self.color = color
        self.life = 0
        self.max_life = 45

    def update(self):
        self.y -= 0.6
        self.life += 1
        return self.life < self.max_life

# --- CORE GAME BOARD STATE ---
class GameEngine:
    def __init__(self):
        self.theme = "CYBER_NEON"
        self.difficulty = "NORMAL"
        self.score = 0
        self.high_score = self.load_high_score()
        self.level = 1
        self.lives = 3
        
        self.state = "START" # START, READY, PLAYING, PAUSED, DYING, GAMEOVER, VICTORY
        self.ready_timer = 150
        self.win_timer = 0
        self.death_timer = 0
        self.screen_shake = 0.0
        self.pulse_time = 0.0
        
        self.grid = []
        self.pacman = None
        self.ghosts = []
        self.particles = []
        self.floating_scores = []
        
        self.frightened_timer = 0
        self.ghost_eaten_multiplier = 0
        self.scatter_chase_timer = 0
        self.scatter_chase_cycle = 0 # even: scatter, odd: chase
        self.pellets_remaining = 0
        
        self.reset_level(full_reset=True)

    def load_high_score(self):
        try:
            if os.path.exists("highscore.json"):
                with open("highscore.json", "r") as f:
                    return json.load(f).get("high_score", 5000)
        except Exception:
            pass
        return 5000

    def save_high_score(self):
        try:
            with open("highscore.json", "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception:
            pass

    def reset_level(self, full_reset=False):
        if full_reset:
            self.score = 0
            self.level = 1
            self.lives = 3
            
        diff_config = DIFFICULTY[self.difficulty]
        self.pacman = Pacman(9, 16, diff_config["pacman_speed"])
        
        self.grid = [row[:] for row in MAP_GRID]
        
        # Count remaining pellets
        self.pellets_remaining = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] in [".", "O"]:
                    self.pellets_remaining += 1
                    
        # Initialise ghost squad
        self.ghosts = [
            Ghost(GhostType.BLINKY, "Shadow Blinky", (255, 0, 0), 9, 8, diff_config["ghost_speed"], SCATTER_ANCHORS[GhostType.BLINKY]),
            Ghost(GhostType.PINKY, "Speedy Pinky", (255, 184, 255), 8, 10, diff_config["ghost_speed"], SCATTER_ANCHORS[GhostType.PINKY], respawn_delay=60),
            Ghost(GhostType.INKY, "Tactical Inky", (0, 255, 255), 9, 10, diff_config["ghost_speed"], SCATTER_ANCHORS[GhostType.INKY], respawn_delay=180),
            Ghost(GhostType.CLYDE, "Fickle Clyde", (255, 184, 81), 10, 10, diff_config["ghost_speed"], SCATTER_ANCHORS[GhostType.CLYDE], respawn_delay=300)
        ]
        
        self.particles = []
        self.floating_scores = []
        self.frightened_timer = 0
        self.ghost_eaten_multiplier = 0
        self.scatter_chase_timer = 0
        self.scatter_chase_cycle = 0
        self.win_timer = 0
        self.death_timer = 0
        self.ready_timer = 150

    def start_game(self):
        self.reset_level(full_reset=True)
        self.state = "READY"
        synth.play_fanfare()

    def advance_wave(self):
        self.level += 1
        self.reset_level(full_reset=False)
        self.state = "READY"
        synth.play_fanfare()

    def is_valid_move(self, grid_x, grid_y, direction, is_ghost=False):
        dx, dy = direction.value
        next_x = grid_x + dx
        next_y = grid_y + dy
        
        # Warp tunnel portals
        if next_x < 0 or next_x >= GRID_COLS:
            return next_y == 10
            
        if next_y < 0 or next_y >= GRID_ROWS:
            return False
            
        cell = self.grid[next_y][next_x]
        if cell == "W":
            return False
        if cell == "-":
            return is_ghost # Ghosts can float through gates
        return True

    def get_pacman_forward_tile(self, tiles_ahead):
        tx, ty = self.pacman.grid_x, self.pacman.grid_y
        dx, dy = self.pacman.direction.value
        return tx + dx * tiles_ahead, ty + dy * tiles_ahead

    def update_character(self, char, is_ghost=False, ghost_obj=None):
        # Warp wrapping
        if char.x < -0.4:
            char.x = GRID_COLS - 0.6
            char.grid_x = GRID_COLS - 1
            return
        if char.x > GRID_COLS - 0.6:
            char.x = -0.4
            char.grid_x = 0
            return

        dx = char.x - char.grid_x
        dy = char.y - char.grid_y
        dist_to_center = abs(dx) + abs(dy)
        
        if dist_to_center < char.speed:
            char.x = float(char.grid_x)
            char.y = float(char.grid_y)
            
            # --- DIRECTION SELECT WINDOW ---
            if not is_ghost:
                # Pac-man input buffer handling
                if char.next_direction != Direction.NONE and self.is_valid_move(char.grid_x, char.grid_y, char.next_direction):
                    char.direction = char.next_direction
                    char.next_direction = Direction.NONE
                elif not self.is_valid_move(char.grid_x, char.grid_y, char.direction):
                    char.direction = Direction.NONE
            else:
                # Ghost navigation logic
                if ghost_obj.mode == GhostMode.EATEN and ghost_obj.grid_x == 9 and ghost_obj.grid_y == 10:
                    ghost_obj.mode = GhostMode.CHASE
                    ghost_obj.frightened_timer = 0
                    ghost_obj.speed = DIFFICULTY[self.difficulty]["ghost_speed"]
                    char.direction = Direction.UP
                elif ghost_obj.respawn_timer > 0:
                    ghost_obj.respawn_timer -= 1
                    if char.y <= 9.8:
                        char.direction = Direction.DOWN
                    elif char.y >= 10.2:
                        char.direction = Direction.UP
                    if ghost_obj.respawn_timer == 0:
                        char.grid_x, char.grid_y = 9, 8
                        char.x, char.y = 9.0, 8.0
                        char.direction = Direction.LEFT
                else:
                    # Choose paths (never allow 180 reversing except on frightened triggers)
                    choices = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
                    valid_choices = []
                    for c in choices:
                        cdx, cdy = c.value
                        opposite = (-char.direction.value[0], -char.direction.value[1])
                        if (cdx, cdy) == opposite:
                            continue
                        if self.is_valid_move(char.grid_x, char.grid_y, c, is_ghost=True):
                            valid_choices.append(c)
                            
                    if valid_choices:
                        if ghost_obj.mode == GhostMode.FRIGHTENED:
                            char.direction = random.choice(valid_choices)
                        else:
                            # Pathfinding via Target tile Euclidean Distance
                            target = (0, 0)
                            if ghost_obj.mode == GhostMode.EATEN:
                                target = (9, 10)
                            elif ghost_obj.mode == GhostMode.SCATTER:
                                target = ghost_obj.scatter_target
                            else:
                                # CHASE TARGET SPECIFICS
                                pac = self.pacman
                                if ghost_obj.type == GhostType.BLINKY:
                                    target = (pac.grid_x, pac.grid_y)
                                elif ghost_obj.type == GhostType.PINKY:
                                    # Target 4 tiles ahead of Pac-Man with up-left bug replicated
                                    ptx, pty = self.get_pacman_forward_tile(4)
                                    if pac.direction == Direction.UP:
                                        ptx -= 4
                                    target = (ptx, pty)
                                elif ghost_obj.type == GhostType.INKY:
                                    # Pincer Vector from Blinky to (Pac + 2 tiles forward) doubled
                                    blinky = next(g for g in self.ghosts if g.type == GhostType.BLINKY)
                                    ptx, pty = self.get_pacman_forward_tile(2)
                                    if pac.direction == Direction.UP:
                                        ptx -= 2
                                    v_x, v_y = ptx - blinky.grid_x, pty - blinky.grid_y
                                    target = (blinky.grid_x + v_x * 2, blinky.grid_y + v_y * 2)
                                elif ghost_obj.type == GhostType.CLYDE:
                                    # Proximity Check (8 cells threshold)
                                    dist_sq = (char.grid_x - pac.grid_x)**2 + (char.grid_y - pac.grid_y)**2
                                    if dist_sq >= 64:
                                        target = (pac.grid_x, pac.grid_y)
                                    else:
                                        target = ghost_obj.scatter_target
                                        
                            best_dir = valid_choices[0]
                            min_dist = float("inf")
                            for c in valid_choices:
                                cdx, cdy = c.value
                                check_x = char.grid_x + cdx
                                check_y = char.grid_y + cdy
                                dist = (check_x - target[0])**2 + (check_y - target[1])**2
                                if dist < min_dist:
                                    min_dist = dist
                                    best_dir = c
                            char.direction = best_dir
                    else:
                        # Fallback reverse
                        char.direction = Direction((-char.direction.value[0], -char.direction.value[1]))

            # Set grid lock destination
            char.grid_x += char.direction.value[0]
            char.grid_y += char.direction.value[1]

        # Tick floating steps
        char.x += char.direction.value[0] * char.speed
        char.y += char.direction.value[1] * char.speed

    def spawn_spark_burst(self, col, row, color):
        px = col * TILE_SIZE + TILE_SIZE // 2
        py = row * TILE_SIZE + TILE_SIZE // 2
        for _ in range(8):
            self.particles.append(Particle(px, py, color))

    def trigger_floating_score(self, col, row, text, color=(255, 255, 255)):
        px = col * TILE_SIZE + TILE_SIZE // 2
        py = row * TILE_SIZE + TILE_SIZE // 2
        self.floating_scores.append(FloatingScore(px, py, text, color))

    def update(self):
        if self.state == "READY":
            self.ready_timer -= 1
            if self.ready_timer <= 0:
                self.state = "PLAYING"
            return
            
        if self.state == "PLAYING":
            self.pulse_time += 0.08
            diff_cfg = DIFFICULTY[self.difficulty]
            theme_cfg = THEMES[self.theme]
            
            # Scatter/Chase cycle timer
            if self.frightened_timer > 0:
                self.frightened_timer -= 16
                if self.frightened_timer <= 0:
                    self.frightened_timer = 0
                    self.ghost_eaten_multiplier = 0
                    for g in self.ghosts:
                        if g.mode == GhostMode.FRIGHTENED:
                            g.mode = GhostMode.CHASE
                            g.speed = diff_cfg["ghost_speed"]
            else:
                self.scatter_chase_timer += 16
                cycle_limit = diff_cfg["scatter_duration"] if self.scatter_chase_cycle % 2 == 0 else diff_cfg["chase_duration"]
                if self.scatter_chase_timer >= cycle_limit:
                    self.scatter_chase_timer = 0
                    self.scatter_chase_cycle += 1
                    next_mode = GhostMode.SCATTER if self.scatter_chase_cycle % 2 == 0 else GhostMode.CHASE
                    for g in self.ghosts:
                        if g.mode in [GhostMode.CHASE, GhostMode.SCATTER]:
                            g.mode = next_mode
                            # Force reverse path direction once per cycle switch
                            g.direction = Direction((-g.direction.value[0], -g.direction.value[1]))
                            
            # 1. Update Pacman Position
            self.update_character(self.pacman, is_ghost=False)
            
            # Wiggle mouth
            pac = self.pacman
            if pac.direction != Direction.NONE:
                if pac.mouth_closing:
                    pac.mouth_angle -= 0.12
                    if pac.mouth_angle <= 0:
                        pac.mouth_angle = 0.0
                        pac.mouth_closing = False
                else:
                    pac.mouth_angle += 0.12
                    if pac.mouth_angle >= 0.5:
                        pac.mouth_angle = 0.5
                        pac.mouth_closing = True
                        
            # Pellet Eating Detection
            px = int(round(pac.x))
            py = int(round(pac.y))
            if 0 <= px < GRID_COLS and 0 <= py < GRID_ROWS:
                cell = self.grid[py][px]
                if cell == ".":
                    self.grid[py][px] = "_"
                    self.score += 10
                    self.pellets_remaining -= 1
                    self.spawn_spark_burst(px, py, theme_cfg["pellet_color"])
                    synth.play("waka", synth.generate_waka)
                elif cell == "O":
                    self.grid[py][px] = "_"
                    self.score += 50
                    self.pellets_remaining -= 1
                    self.spawn_spark_burst(px, py, theme_cfg["power_pellet_color"])
                    synth.play("power", synth.generate_power)
                    self.screen_shake = 6.0
                    
                    # Scare ghosts
                    self.frightened_timer = diff_cfg["frightened_duration"]
                    self.ghost_eaten_multiplier = 0
                    for g in self.ghosts:
                        if g.mode in [GhostMode.CHASE, GhostMode.SCATTER, GhostMode.FRIGHTENED]:
                            g.mode = GhostMode.FRIGHTENED
                            g.frightened_timer = self.frightened_timer
                            g.speed = diff_cfg["frightened_speed"]
                            g.direction = Direction((-g.direction.value[0], -g.direction.value[1]))

            # Sync highscore
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()

            # Win condition
            if self.pellets_remaining <= 0:
                self.state = "VICTORY"
                self.win_timer = 120
                return
                
            # 2. Update Ghost positions & check collisions
            for g in self.ghosts:
                self.update_character(g, is_ghost=True, ghost_obj=g)
                
                # Collision check
                dist = math.hypot(pac.x - g.x, pac.y - g.y)
                if dist < 0.6:
                    if g.mode == GhostMode.FRIGHTENED:
                        # Eat ghost!
                        g.mode = GhostMode.EATEN
                        g.speed = diff_cfg["ghost_speed"] * 2.0 # return home fast
                        self.ghost_eaten_multiplier += 1
                        points = 200 * (2 ** min(self.ghost_eaten_multiplier - 1, 3))
                        self.score += points
                        synth.play("eat_ghost", synth.generate_eat_ghost)
                        self.trigger_floating_score(g.grid_x, g.grid_y, f"+{points}", (0, 255, 255))
                        self.screen_shake = 12.0
                    elif g.mode != GhostMode.EATEN:
                        # Pac-man dies!
                        self.state = "DYING"
                        self.death_timer = 100
                        pac.is_dying = True
                        pac.death_frame = 0
                        synth.play("death", synth.generate_death)
                        return

        elif self.state == "DYING":
            self.death_timer -= 1
            if self.death_timer % 6 == 0:
                self.pacman.death_frame += 1
            if self.death_timer <= 0:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "GAMEOVER"
                else:
                    self.reset_level(full_reset=False)
                    self.state = "READY"
                    synth.play_fanfare()

        elif self.state == "VICTORY":
            self.win_timer -= 1
            if self.win_timer <= 0:
                self.advance_wave()

        # Update secondary systems
        self.particles = [p for p in self.particles if p.update()]
        self.floating_scores = [s for s in self.floating_scores if s.update()]
        if self.screen_shake > 0:
            self.screen_shake *= 0.9
            if self.screen_shake < 0.1:
                self.screen_shake = 0.0

# --- GRAPHICS RENDERING SYSTEMS ---
class ScreenRenderer:
    def __init__(self, width=960, height=720):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pac-Man Cyber Redux - Immersive Edition")
        
        # Load custom fonts
        self.font_sans = pygame.font.SysFont("Helvetica", 14, bold=True)
        self.font_mono = pygame.font.SysFont("Courier", 12, bold=True)
        self.font_title = pygame.font.SysFont("Helvetica", 36, bold=True)
        self.font_large = pygame.font.SysFont("Helvetica", 22, bold=True)
        
        # Create persistent surfaces for map rendering optimization
        self.map_surf = pygame.Surface((GRID_COLS * TILE_SIZE, GRID_ROWS * TILE_SIZE))
        self.rebuild_map = True

    def draw_walls(self, engine):
        if not self.rebuild_map:
            return
        theme = THEMES[engine.theme]
        self.map_surf.fill(theme["background"])
        
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = MAP_GRID[r][c]
                x = c * TILE_SIZE
                y = r * TILE_SIZE
                
                if cell == "W":
                    # Draw neon-style borders and connected lines
                    top = r > 0 and MAP_GRID[r-1][c] == "W"
                    bottom = r < GRID_ROWS - 1 and MAP_GRID[r+1][c] == "W"
                    left = c > 0 and MAP_GRID[r][c-1] == "W"
                    right = c < GRID_COLS - 1 and MAP_GRID[r][c+1] == "W"
                    
                    if engine.theme == "CYBER_NEON":
                        # Glowing inner box
                        pygame.draw.rect(self.map_surf, (theme["wall_color"][0]//5, theme["wall_color"][1]//5, theme["wall_color"][2]//5), (x+3, y+3, TILE_SIZE-6, TILE_SIZE-6))
                        # Connect neon beams
                        center = (x + TILE_SIZE//2, y + TILE_SIZE//2)
                        if left:
                            pygame.draw.line(self.map_surf, theme["wall_color"], (x, center[1]), center, 3)
                        if right:
                            pygame.draw.line(self.map_surf, theme["wall_color"], center, (x + TILE_SIZE, center[1]), 3)
                        if top:
                            pygame.draw.line(self.map_surf, theme["wall_color"], (center[0], y), center, 3)
                        if bottom:
                            pygame.draw.line(self.map_surf, theme["wall_color"], center, (center[0], y + TILE_SIZE), 3)
                    else:
                        pygame.draw.rect(self.map_surf, theme["wall_color"], (x+1, y+1, TILE_SIZE-2, TILE_SIZE-2))
                elif cell == "-":
                    # Ghost house gate barrier
                    pygame.draw.line(self.map_surf, (59, 130, 246), (x, y + TILE_SIZE//2), (x + TILE_SIZE, y + TILE_SIZE//2), 4)
        self.rebuild_map = False

    def render(self, engine):
        theme = THEMES[engine.theme]
        self.screen.fill((5, 5, 5)) # Deep space base dark backing
        
        # Draw connected walls
        self.draw_walls(engine)
        
        # Frame container with Screen Shake vector
        shake_x, shake_y = 0, 0
        if engine.screen_shake > 0.5:
            shake_x = int(random.uniform(-engine.screen_shake, engine.screen_shake))
            shake_y = int(random.uniform(-engine.screen_shake, engine.screen_shake))
            
        # Draw map backing with offsets
        map_offset_x = 40 + shake_x
        map_offset_y = 120 + shake_y
        self.screen.blit(self.map_surf, (map_offset_x, map_offset_y))
        
        # --- DRAW PELLETS & POWER ITEMS ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = engine.grid[r][c]
                px = map_offset_x + c * TILE_SIZE + TILE_SIZE // 2
                py = map_offset_y + r * TILE_SIZE + TILE_SIZE // 2
                
                if cell == ".":
                    pygame.draw.circle(self.screen, theme["pellet_color"], (px, py), 3)
                elif cell == "O":
                    scale = 1.0 + math.sin(engine.pulse_time) * 0.25
                    rad = int(7 * scale)
                    pygame.draw.circle(self.screen, theme["power_pellet_color"], (px, py), rad)
                    
        # --- DRAW PAC-MAN ---
        pac = engine.pacman
        pac_px = map_offset_x + int(pac.x * TILE_SIZE) + TILE_SIZE // 2
        pac_py = map_offset_y + int(pac.y * TILE_SIZE) + TILE_SIZE // 2
        radius = TILE_SIZE // 2 - 1
        
        if pac.is_dying:
            # Draw collapsing crescent slice representation
            death_angle = (pac.death_frame / 15.0) * math.pi
            start_angle = death_angle
            end_angle = 2 * math.pi - death_angle
            if end_angle > start_angle:
                # Convert radians to pygame arc formatting (starts at right, goes counterclockwise)
                rect = (pac_px - radius, pac_py - radius, radius*2, radius*2)
                pygame.draw.arc(self.screen, theme["pacman_color"], rect, start_angle, end_angle, 3)
        else:
            # Calculate mouth wedge angles based on current moving direction
            rotation = 0.0
            if pac.direction == Direction.UP:
                rotation = 90.0
            elif pac.direction == Direction.DOWN:
                rotation = 270.0
            elif pac.direction == Direction.LEFT:
                rotation = 180.0
            elif pac.direction == Direction.RIGHT:
                rotation = 0.0
                
            rect = (pac_px - radius, pac_py - radius, radius*2, radius*2)
            start_a = (pac.mouth_angle * 0.7 * (180.0 / math.pi) + rotation) % 360
            end_a = ((360.0 - pac.mouth_angle * 0.7 * (180.0 / math.pi)) + rotation) % 360
            
            # Draw Pac-Man circle body
            pygame.draw.circle(self.screen, theme["pacman_color"], (pac_px, pac_py), radius)
            
            # Subtract mouth wedge by drawing triangle or intersecting sector
            if pac.direction != Direction.NONE and pac.mouth_angle > 0.05:
                # Draw wedge cut out in black/bg color
                wedge_pts = [
                    (pac_px, pac_py),
                    (pac_px + int(radius * math.cos(math.radians(start_a))), pac_py - int(radius * math.sin(math.radians(start_a)))),
                    (pac_px + int(radius * math.cos(math.radians(end_a))), pac_py - int(radius * math.sin(math.radians(end_a))))
                ]
                pygame.draw.polygon(self.screen, theme["background"], wedge_pts)
                
        # --- DRAW GHOSTS ---
        for g in engine.ghosts:
            ghost_px = map_offset_x + int(g.x * TILE_SIZE) + TILE_SIZE // 2
            ghost_py = map_offset_y + int(g.y * TILE_SIZE) + TILE_SIZE // 2
            r_ghost = TILE_SIZE // 2 - 1.5
            
            if g.mode == GhostMode.EATEN:
                # Draw white eyes returning to base
                self.draw_eyes(ghost_px, ghost_py, g.direction, scared=False)
            else:
                # Ghost dome shape
                g_color = g.color
                if g.mode == GhostMode.FRIGHTENED:
                    # Alternating flash on timer expiration
                    if engine.frightened_timer < 2200 and (engine.frightened_timer // 200) % 2 == 0:
                        g_color = (255, 255, 255) # flash white
                    else:
                        g_color = (30, 58, 138) # scared blue
                        
                # Draw body (dome head + wavy bottom)
                # Dome head
                pygame.draw.circle(self.screen, g_color, (ghost_px, ghost_py - 2), int(r_ghost))
                # Body rectangle
                pygame.draw.rect(self.screen, g_color, (ghost_px - r_ghost, ghost_py - 2, r_ghost * 2, r_ghost + 1))
                
                # Dynamic skirt oscillations
                wave_y = int(2 * math.sin(engine.pulse_time * 5.0 + (0 if g.type == GhostType.BLINKY else 2)))
                pygame.draw.rect(self.screen, g_color, (ghost_px - r_ghost, ghost_py + r_ghost - 1, r_ghost * 2, 3 + wave_y))
                
                # Draw eyes
                self.draw_eyes(ghost_px, ghost_py, g.direction, scared=(g.mode == GhostMode.FRIGHTENED))

        # --- DRAW PARTICLES ---
        for p in engine.particles:
            surf = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (p.color[0], p.color[1], p.color[2], p.alpha), (int(p.size), int(p.size)), int(p.size))
            self.screen.blit(surf, (p.x - p.size, p.y - p.size))
            
        # --- DRAW FLOATING OVERLAYS ---
        for s in engine.floating_scores:
            text_surf = self.font_mono.render(s.text, True, s.color)
            self.screen.blit(text_surf, (s.x - text_surf.get_width()//2, s.y))

        # --- DRAW IMMERSIVE SYSTEM HUD (RIGHT SIDEBAR) ---
        sidebar_x = 610
        pygame.draw.line(self.screen, (255, 255, 255, 10), (sidebar_x - 20, 0), (sidebar_x - 20, self.height), 1)
        
        # Header Box Title
        header_surf = self.font_title.render("NEON·REDUX", True, (255, 255, 255))
        self.screen.blit(header_surf, (40, 25))
        tag_surf = self.font_mono.render("ENHANCED GHOST PROTOCOL V2.4", True, (255, 255, 255, 120))
        self.screen.blit(tag_surf, (42, 70))
        
        # Stats scores board
        score_title = self.font_mono.render("CURRENT SCORE", True, (255, 255, 255, 100))
        self.screen.blit(score_title, (400, 30))
        score_val = self.font_large.render(f"{engine.score:06,d}", True, (255, 255, 255))
        self.screen.blit(score_val, (400, 50))
        
        hi_title = self.font_mono.render("HIGH SCORE", True, (255, 255, 255, 100))
        self.screen.blit(hi_title, (520, 30))
        hi_val = self.font_large.render(f"{engine.high_score:06,d}", True, (245, 158, 11))
        self.screen.blit(hi_val, (520, 50))
        
        wave_title = self.font_mono.render("ACTIVE WAVE", True, (255, 255, 255, 100))
        self.screen.blit(wave_title, (280, 30))
        wave_val = self.font_large.render(f"#{engine.level:02d}", True, (217, 70, 239))
        self.screen.blit(wave_val, (280, 50))

        # Right Sidebar Content
        sb_y = 40
        # Title of status
        title_diagnostics = self.font_mono.render("ENTITY PROTOCOL TELEMETRY", True, (6, 182, 212))
        self.screen.blit(title_diagnostics, (sidebar_x, sb_y))
        
        sb_y += 30
        for g in engine.ghosts:
            # Container card bounding
            pygame.draw.rect(self.screen, (20, 20, 20), (sidebar_x, sb_y, 310, 80), border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255, 15), (sidebar_x, sb_y, 310, 80), 1, border_radius=8)
            
            # Glowing indicator dot
            pygame.draw.circle(self.screen, g.color, (sidebar_x + 18, sb_y + 20), 4)
            # Ghost Title
            name_text = self.font_sans.render(g.name.upper(), True, g.color)
            self.screen.blit(name_text, (sidebar_x + 30, sb_y + 13))
            
            # Mode badge
            mode_color = (239, 68, 68) if g.mode == GhostMode.CHASE else (16, 185, 129) if g.mode == GhostMode.SCATTER else (59, 130, 246)
            mode_badge = self.font_mono.render(g.mode.name, True, mode_color)
            self.screen.blit(mode_badge, (sidebar_x + 220, sb_y + 13))
            
            # Coord lines
            coord_text = self.font_mono.render(f"GRID TILE: [{g.grid_x:02d}, {g.grid_y:02d}]", True, (150, 150, 150))
            self.screen.blit(coord_text, (sidebar_x + 18, sb_y + 38))
            
            target_text = self.font_mono.render(f"TARGET CELL: [{g.scatter_target[0]:02d}, {g.scatter_target[1]:02d}]", True, (150, 150, 150))
            self.screen.blit(target_text, (sidebar_x + 18, sb_y + 53))
            
            sb_y += 92

        # Level progressions HUD element
        pygame.draw.rect(self.screen, (20, 20, 20), (sidebar_x, sb_y, 310, 130), border_radius=8)
        pygame.draw.rect(self.screen, (255, 255, 255, 15), (sidebar_x, sb_y, 310, 130), 1, border_radius=8)
        
        stat_title = self.font_mono.render("PLAYER STATUS CORE", True, (234, 179, 8))
        self.screen.blit(stat_title, (sidebar_x + 15, sb_y + 15))
        
        # Lives icons
        self.screen.blit(self.font_mono.render("LIFE SHIELDS:", True, (150, 150, 150)), (sidebar_x + 15, sb_y + 40))
        for l in range(3):
            lx = sidebar_x + 120 + l * 20
            ly = sb_y + 46
            bg_col = (234, 179, 8) if l < engine.lives else (50, 50, 50)
            pygame.draw.circle(self.screen, bg_col, (lx, ly), 6)
            
        # DOTS progress
        total_dots = 186
        dots_left = max(0, engine.pellets_remaining)
        cleared_percent = int((1.0 - dots_left / total_dots) * 100) if dots_left > 0 else 100
        
        progress_text = self.font_mono.render(f"WAVE CLEAR PROGRESS: {cleared_percent}%", True, (150, 150, 150))
        self.screen.blit(progress_text, (sidebar_x + 15, sb_y + 70))
        
        # Progress bar
        pygame.draw.rect(self.screen, (50, 50, 50), (sidebar_x + 15, sb_y + 92, 280, 8), border_radius=4)
        bar_w = int(280 * (cleared_percent / 100.0))
        if bar_w > 0:
            pygame.draw.rect(self.screen, (6, 182, 212), (sidebar_x + 15, sb_y + 92, bar_w, 8), border_radius=4)

        # Bottom legend footer bar
        pygame.draw.rect(self.screen, (10, 10, 10), (0, 660, self.width, 60))
        pygame.draw.line(self.screen, (255, 255, 255, 15), (0, 660), (self.width, 660), 1)
        
        # Action instructions
        self.screen.blit(self.font_mono.render("CONTROLS:", True, (100, 100, 100)), (40, 682))
        self.screen.blit(self.font_mono.render("[WASD / ARROWS] TO NAVIGATE", True, (255, 255, 255)), (120, 682))
        self.screen.blit(self.font_mono.render("[SPACE] PAUSE/UNPAUSE", True, (255, 255, 255)), (340, 682))
        self.screen.blit(self.font_mono.render("[M] TOGGLE AUDIO", True, (255, 255, 255)), (540, 682))
        self.screen.blit(self.font_mono.render("LATENCY: 2ms // AUDIO: RETRO_SYNTH", True, (0, 255, 204, 150)), (715, 682))

        # Draw overlays for different game states
        if engine.state == "START":
            self.draw_popup_overlay("PAC-MAN REDUX", "PRESS [ENTER] TO INSERT COIN", (6, 182, 212))
        elif engine.state == "READY":
            self.draw_popup_overlay("READY!", "GET READY TO RUN", (234, 179, 8))
        elif engine.state == "PAUSED":
            self.draw_popup_overlay("MATCH PAUSED", "PRESS [SPACE] TO CONTINUE", (6, 182, 212))
        elif engine.state == "GAMEOVER":
            self.draw_popup_overlay("GAME OVER", "PRESS [ENTER] TO RESTART WAVE", (239, 68, 68))
        elif engine.state == "VICTORY":
            self.draw_popup_overlay("MAZE CLEARED!", "COMPILING NEXT WAVE DATA...", (16, 185, 129))

        pygame.display.flip()

    def draw_eyes(self, ex, ey, direction, scared=False):
        eye_spacing = 4
        eye_size = 3
        pupil_size = 1.5
        
        if scared:
            # Simple scared red/pink beady dots
            pygame.draw.circle(self.screen, (255, 184, 174), (ex - eye_spacing, ey - 2), 2)
            pygame.draw.circle(self.screen, (255, 184, 174), (ex + eye_spacing, ey - 2), 2)
            # Scared squiggle mouth line
            pygame.draw.line(self.screen, (255, 184, 174), (ex - 4, ey + 3), (ex - 2, ey + 1), 1)
            pygame.draw.line(self.screen, (255, 184, 174), (ex - 2, ey + 1), (ex, ey + 3), 1)
            pygame.draw.line(self.screen, (255, 184, 174), (ex, ey + 3), (ex + 2, ey + 1), 1)
            pygame.draw.line(self.screen, (255, 184, 174), (ex + 2, ey + 1), (ex + 4, ey + 3), 1)
        else:
            # White eye bases
            pygame.draw.circle(self.screen, (255, 255, 255), (ex - eye_spacing, ey - 2), eye_size)
            pygame.draw.circle(self.screen, (255, 255, 255), (ex + eye_spacing, ey - 2), eye_size)
            
            # Blue pupils direction offsets
            ox, oy = 0, 0
            if direction == Direction.UP:
                oy = -1.5
            elif direction == Direction.DOWN:
                oy = 1.5
            elif direction == Direction.LEFT:
                ox = -1.5
            elif direction == Direction.RIGHT:
                ox = 1.5
                
            pygame.draw.circle(self.screen, (0, 34, 255), (int(ex - eye_spacing + ox), int(ey - 2 + oy)), pupil_size)
            pygame.draw.circle(self.screen, (0, 34, 255), (int(ex + eye_spacing + ox), int(ey - 2 + oy)), pupil_size)

    def draw_popup_overlay(self, title, subtitle, accent_color):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((4, 2, 13, 200)) # semitransparent dim back
        
        # Center card container
        card_w, card_h = 420, 160
        cx, cy = (self.width - card_w) // 2, (self.height - card_h) // 2
        pygame.draw.rect(overlay, (10, 10, 10), (cx, cy, card_w, card_h), border_radius=12)
        pygame.draw.rect(overlay, accent_color, (cx, cy, card_w, card_h), 2, border_radius=12)
        
        # Redux glowing header lines
        t_surf = self.font_large.render(title, True, accent_color)
        sub_surf = self.font_sans.render(subtitle, True, (255, 255, 255, 180))
        
        overlay.blit(t_surf, (cx + (card_w - t_surf.get_width())//2, cy + 45))
        overlay.blit(sub_surf, (cx + (card_w - sub_surf.get_width())//2, cy + 90))
        
        self.screen.blit(overlay, (0, 0))

# --- MAIN EXECUTION HANDLER ---
def main():
    clock = pygame.time.Clock()
    engine = GameEngine()
    renderer = ScreenRenderer()

    # Audio start sound lazy queue
    while True:
        # Check framerate cap (60FPS standard retro speed sync)
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.KEYDOWN:
                # Quit escape
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                    
                # Sound toggling
                if event.key == pygame.K_m:
                    synth.toggle_mute()
                    
                if engine.state == "PLAYING":
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        engine.pacman.next_direction = Direction.UP
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        engine.pacman.next_direction = Direction.DOWN
                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        engine.pacman.next_direction = Direction.LEFT
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        engine.pacman.next_direction = Direction.RIGHT
                    elif event.key == pygame.K_SPACE:
                        engine.state = "PAUSED"
                        
                elif engine.state == "START":
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        engine.start_game()
                        
                elif engine.state == "PAUSED":
                    if event.key == pygame.K_SPACE:
                        engine.state = "PLAYING"
                        
                elif engine.state in ["GAMEOVER", "VICTORY"]:
                    if event.key == pygame.K_RETURN:
                        engine.start_game()

        # Update and redrawing pipelines
        engine.update()
        renderer.render(engine)

if __name__ == "__main__":
    main()

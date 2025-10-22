import pygame
import math
import random
import sys
import os
import wave
import struct
import urllib.request
from collections import deque
import numpy as np

# --- Game Configuration ---
# Get screen size and maximize grid
pygame.init()
info = pygame.display.Info()
AVAILABLE_WIDTH = info.current_w
AVAILABLE_HEIGHT = info.current_h

# Calculate optimal grid size to fill screen (responsive for desktop & mobile)
if AVAILABLE_WIDTH < 800:
    # Narrow / mobile layout
    GRID_WIDTH = 8
    GRID_HEIGHT = 10
    UI_HEIGHT = 120
elif AVAILABLE_WIDTH < 1200:
    GRID_WIDTH = 10
    GRID_HEIGHT = 12
    UI_HEIGHT = 140
else:
    GRID_WIDTH = 12
    GRID_HEIGHT = 14
    UI_HEIGHT = 160

# Make cells a reasonable size but keep a minimum for touch targets
CELL_SIZE = max(24, min(AVAILABLE_WIDTH // GRID_WIDTH, (AVAILABLE_HEIGHT - UI_HEIGHT) // GRID_HEIGHT))
SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE + UI_HEIGHT

# Responsive header height used across drawing/interaction
HEADER_HEIGHT = max(50, int(CELL_SIZE * 1.2))
FPS = 60

# --- Modern Gradient Colors & Theme ---
COLOR = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "BACKGROUND": (10, 12, 25),  # Deep blue-black
    "BACKGROUND_GRADIENT_TOP": (20, 25, 45),  # Lighter blue
    "BACKGROUND_GRADIENT_BOTTOM": (5, 8, 15),  # Darker blue-black
    "GRID": (60, 70, 90),
    "GRID_DARK": (25, 30, 45),
    "UI_BACKGROUND": (12, 15, 28),
    "UI_GRADIENT_TOP": (25, 30, 50),
    "UI_GRADIENT_BOTTOM": (10, 12, 22),
    "BUTTON": (45, 55, 80),
    "BUTTON_HOVER": (70, 85, 120),
    "ACCENT": (100, 120, 200),  # Bright blue accent
}

PLAYER_COLORS = [
    (239, 83, 80),    # 1: Red
    (3, 169, 244),     # 2: Light Blue
    (139, 195, 74),   # 3: Light Green
    (255, 238, 88),   # 4: Yellow
    (255, 112, 67),   # 5: Deep Orange
    (171, 71, 188),    # 6: Purple
    (38, 198, 218),    # 7: Cyan
    (255, 183, 77),   # 8: Amber
]

# --- Animation & Effect Parameters ---
PULSATE_SPEED = 0.05
ORB_TRAVEL_SPEED = 300
PLACE_ANIM_DURATION = 0.25 # seconds
EXPLOSION_DELAY = 0.15  # Delay between explosions
SHAKE_INTENSITY = 4
SHAKE_DURATION = 0.15

# Dominance bar animation configuration
DOM_WAVE_ENABLED = True
DOM_WAVE_AMPLITUDE_FACTOR = 0.2  # fraction of bar height
DOM_WAVE_SPEED = 0.06  # animation speed multiplier

# --- Inline asset generation (single-file) ---
def _generate_sine_wave(frequency, duration, sample_rate=44100, amplitude=0.3):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * math.pi * frequency * t)

def _apply_envelope(wave_data, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    length = len(wave_data)
    envelope = np.ones(length)
    attack_samples = max(1, int(length * attack))
    decay_samples = max(1, int(length * decay))
    release_samples = max(1, int(length * release))
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    decay_end = min(length, attack_samples + decay_samples)
    envelope[attack_samples:decay_end] = np.linspace(1, sustain, decay_end - attack_samples)
    envelope[-release_samples:] = np.linspace(sustain, 0, release_samples)
    return wave_data * envelope

def _save_wav(filename, wave_data, sample_rate=44100):
    wave_data = np.clip(wave_data, -1, 1)
    wave_int16 = (wave_data * 32767).astype(np.int16)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(wave_int16.tobytes())

def _gen_place_sound(path):
    sr = 44100
    duration = 0.1
    w1 = _generate_sine_wave(800, duration, sr, 0.2)
    w2 = _generate_sine_wave(1200, duration, sr, 0.15)
    mixed = _apply_envelope(w1 + w2, attack=0.01, decay=0.3, sustain=0.3, release=0.4)
    _save_wav(path, mixed, sr)

def _gen_explode_sound(path):
    sr = 44100
    duration = 0.3
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freq = 100 + (40 - 100) * (t / duration)
    w1 = 0.4 * np.sin(2 * math.pi * freq * t)
    noise = np.random.normal(0, 0.15, len(t))
    w2 = _generate_sine_wave(2000, duration, sr, 0.1)
    mixed = _apply_envelope(w1 + noise * 0.5 + w2 * 0.3, attack=0.001, decay=0.2, sustain=0.4, release=0.4)
    _save_wav(path, mixed, sr)

def _gen_win_sound(path):
    sr = 44100
    duration = 1.0
    notes = [523, 659, 784, 1047]
    per = duration / len(notes)
    full = np.array([], dtype=np.float32)
    for n in notes:
        w = _generate_sine_wave(n, per, sr, 0.25)
        w = _apply_envelope(w, attack=0.05, decay=0.2, sustain=0.7, release=0.3)
        full = np.concatenate([full, w])
    _save_wav(path, full, sr)

def _gen_music(path):
    sr = 44100
    duration = 30
    chords = [
        [262, 330, 392],
        [220, 262, 330],
        [175, 220, 262],
        [196, 247, 294],
    ]
    per = duration / len(chords)
    full = np.array([], dtype=np.float32)
    for chord in chords:
        chord_wave = np.zeros(int(sr * per), dtype=np.float32)
        for f in chord:
            chord_wave += _generate_sine_wave(f, per, sr, 0.08)
        chord_wave = _apply_envelope(chord_wave, attack=0.1, decay=0.2, sustain=0.6, release=0.5)
        full = np.concatenate([full, chord_wave])
    _save_wav(path, full, sr)

def _maybe_download_font():
    # Optional: try to fetch a font; game has system-font fallback if this fails
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"
        dest = os.path.join('assets', 'GameFont.ttf')
        if not os.path.exists(dest):
            urllib.request.urlopen(url)  # quick connectivity check
            urllib.request.urlretrieve(url, dest)
    except Exception:
        pass

def ensure_assets():
    os.makedirs('assets', exist_ok=True)
    # We'll generate WAV files; loader already falls back to WAV if OGG missing
    required = {
        'place': os.path.join('assets', 'place.wav'),
        'explode': os.path.join('assets', 'explode.wav'),
        'win': os.path.join('assets', 'win.wav'),
        'music': os.path.join('assets', 'music.wav'),
    }
    if not os.path.exists(required['place']):
        _gen_place_sound(required['place'])
    if not os.path.exists(required['explode']):
        _gen_explode_sound(required['explode'])
    if not os.path.exists(required['win']):
        _gen_win_sound(required['win'])
    if not os.path.exists(required['music']):
        _gen_music(required['music'])
    _maybe_download_font()

class Particle:
    """Visual particle effect for explosions"""
    def __init__(self, pos, color):
        self.pos = pygame.Vector2(pos)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(100, 250)
        self.vel = pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.color = color
        self.lifetime = random.uniform(0.4, 0.8)
        self.age = 0
        self.size = random.randint(4, 8)
    
    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt
        self.vel *= 0.92  # Friction
        return self.age < self.lifetime
    
    def draw(self, screen):
        alpha = 1 - (self.age / self.lifetime)
        size = int(self.size * alpha)
        if size > 0:
            # Particle with glow
            glow_color = tuple(int(c * alpha * 0.5) for c in self.color)
            main_color = tuple(int(c * alpha) for c in self.color)
            
            # Outer glow
            if size > 2:
                pygame.draw.circle(screen, glow_color, (int(self.pos.x), int(self.pos.y)), size + 2)
            
            # Main particle
            pygame.draw.circle(screen, main_color, (int(self.pos.x), int(self.pos.y)), size)

class Button:
    """A clickable UI button with hover effects."""
    def __init__(self, rect, text, text_color=COLOR["WHITE"]):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.text_color = text_color
        # Responsive font size - reduced
        fsize = max(10, int(CELL_SIZE * 0.5))
        try:
            self.font = pygame.font.Font(FONT_PATH, fsize)
        except Exception:
            self.font = pygame.font.SysFont(None, fsize)
        self.base_color = COLOR["BUTTON"]
        self.hover_color = COLOR["BUTTON_HOVER"]
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            # Could add hover sound here if desired
        if event.type == pygame.MOUSEBUTTONDOWN and self.is_hovered:
            return True
        return False

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.base_color

        # Draw base rounded rect
        pygame.draw.rect(screen, color, self.rect, border_radius=14)

        # Neon accent border
        pygame.draw.rect(screen, COLOR["ACCENT"], self.rect, 2, border_radius=14)

        # Subtle glow when hovered
        if self.is_hovered:
            glow = self.rect.inflate(12, 8)
            glow_surf = pygame.Surface((glow.width, glow.height), pygame.SRCALPHA)
            gc = tuple(min(255, int(c * 0.9)) for c in COLOR["ACCENT"])
            pygame.draw.rect(glow_surf, (*gc, 48), glow_surf.get_rect(), border_radius=16)
            screen.blit(glow_surf, glow.topleft)

        # Text: auto-scale down if it doesn't fit the button rect
        padding = 12
        max_width = max(10, self.rect.width - padding * 2)
        # Start from existing font size if possible
        try:
            current_size = self.font.get_linesize()
        except Exception:
            current_size = max(10, int(CELL_SIZE * 0.5))

        # Try rendering with decreasing sizes until it fits or reaches a minimum
        render_font = self.font
        text_surf = render_font.render(self.text, True, self.text_color)
        # If text too wide, reduce font size
        if text_surf.get_width() > max_width:
            size = int(current_size * 0.9)
            min_size = 10
            while size >= min_size:
                try:
                    if 'FONT_PATH' in globals() and FONT_PATH:
                        render_font = pygame.font.Font(FONT_PATH, size)
                    else:
                        render_font = pygame.font.SysFont(None, size)
                except Exception:
                    render_font = pygame.font.SysFont(None, size)
                text_surf = render_font.render(self.text, True, self.text_color)
                if text_surf.get_width() <= max_width:
                    break
                size -= 1

        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

class Cell:
    """Represents a grid cell, handling its own state and drawing."""
    def __init__(self, row, col):
        self.row, self.col = row, col
        self.orbs, self.owner = 0, None
        self.rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        # Calculate critical mass correctly: corners=2, edges=3, centers=4
        is_corner = (row in (0, GRID_HEIGHT - 1)) and (col in (0, GRID_WIDTH - 1))
        is_edge = not is_corner and (row in (0, GRID_HEIGHT - 1) or col in (0, GRID_WIDTH - 1))
        self.critical_mass = 2 if is_corner else (3 if is_edge else 4)

        # For placement animation
        self.scale = 0
        self.is_placing = False
        self.rotation = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(0.8, 1.2)

    def start_placement(self):
        self.is_placing = True
        self.scale = 0

    def update(self, dt):
        if self.is_placing:
            self.scale += dt / PLACE_ANIM_DURATION
            if self.scale >= 1:
                self.scale = 1
                self.is_placing = False

        if self.orbs > 1:
            self.rotation += self.rotation_speed * dt * math.pi
            self.rotation %= (2 * math.pi)

    def draw(self, screen):
        # Draw cell background - simple solid color for performance
        pygame.draw.rect(screen, COLOR["GRID_DARK"], self.rect)
        
        if self.owner is not None:
            color = PLAYER_COLORS[self.owner]
            center = self.rect.center
            
            # Pulsating effect for critical cells
            pulse = 0
            if self.orbs == self.critical_mass - 1:
                pulse = math.sin(pygame.time.get_ticks() * PULSATE_SPEED) * 2
            
            base_radius = 14
            animate_scale = (self.scale if self.is_placing else 1)

            if self.orbs == 1:
                radius = max(6, int((base_radius + pulse) * animate_scale))
                pos = (int(center[0]), int(center[1]))
                pygame.draw.circle(screen, (20, 20, 30), (pos[0] + 1, pos[1] + 2), radius + 1)
                pygame.draw.circle(screen, color, pos, radius)
                highlight_pos = (pos[0] - int(radius * 0.25), pos[1] - int(radius * 0.25))
                highlight_color = tuple(min(255, int(c * 1.3)) for c in color)
                pygame.draw.circle(screen, highlight_color, highlight_pos, max(3, int(radius * 0.3)))
            else:
                orbit_radius = 16 if self.orbs >= 3 else 12
                orbit_radius += pulse * 0.5
                orbit_radius *= animate_scale
                orb_data = []
                for idx in range(self.orbs):
                    angle = self.rotation + (2 * math.pi * idx) / self.orbs
                    depth = (math.sin(angle) + 1) * 0.5
                    x = center[0] + math.cos(angle) * orbit_radius
                    y = center[1] + math.sin(angle) * orbit_radius * 0.45
                    scale = 0.8 + depth * 0.35
                    orb_data.append({
                        "pos": (x, y),
                        "depth": depth,
                        "scale": scale
                    })

                orb_data.sort(key=lambda item: item["depth"])

                glow_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (*color, 45), (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 2 - 4)
                screen.blit(glow_surface, (self.rect.left, self.rect.top))

                for item in orb_data:
                    pos = (int(item["pos"][0]), int(item["pos"][1]))
                    radius = max(5, int(base_radius * item["scale"]))
                    shadow_offset = 2 - item["depth"]
                    shadow_pos = (pos[0] + int(shadow_offset), pos[1] + int(shadow_offset * 1.5))
                    pygame.draw.circle(screen, (25, 25, 40), shadow_pos, radius + 1)

                    shade_factor = 0.75 + item["depth"] * 0.4
                    shaded_color = tuple(min(255, int(c * shade_factor)) for c in color)
                    pygame.draw.circle(screen, shaded_color, pos, radius)

                    highlight_offset = (math.cos(self.rotation + item["depth"]) * radius * 0.25,
                                        math.sin(self.rotation + item["depth"]) * radius * 0.25)
                    highlight_pos = (pos[0] - int(highlight_offset[0]), pos[1] - int(highlight_offset[1]))
                    highlight_color = tuple(min(255, int(c * 1.35)) for c in color)
                    pygame.draw.circle(screen, highlight_color, highlight_pos, max(3, int(radius * 0.3)))

class AnimatedOrb:
    """An orb that visually travels between cells."""
    def __init__(self, start_cell, end_cell, player_id):
        self.start = pygame.Vector2(start_cell.rect.center)
        self.end = pygame.Vector2(end_cell.rect.center)
        self.pos = self.start.copy()
        self.target_cell = end_cell
        self.player_id = player_id
        dist = self.start.distance_to(self.end)
        self.dir = (self.end - self.start).normalize() if dist > 0 else pygame.Vector2()
        self.progress = 0  # Animation progress 0 to 1

    def update(self, dt):
        # Smooth acceleration/deceleration
        self.progress += dt * (1 / 0.3)  # 0.3 seconds travel time
        if self.progress > 1:
            self.progress = 1
        
        # Ease-in-out interpolation for smooth movement
        t = self.progress
        ease = t * t * (3 - 2 * t)  # Smoothstep function
        
        self.pos = self.start + (self.end - self.start) * ease
        return self.progress >= 1

    def draw(self, screen):
        color = PLAYER_COLORS[self.player_id]
        radius = 14

        pos = (int(self.pos.x), int(self.pos.y))

        # Simple animated orb - clean circle
        shadow_pos = (pos[0] + 1, pos[1] + 2)
        shadow_color = (20, 20, 30, 180)
        pygame.draw.circle(screen, shadow_color, shadow_pos, radius + 1)

        # Main solid circle
        pygame.draw.circle(screen, color, pos, radius)

        # Small highlight
        highlight_pos = (pos[0] - int(radius * 0.25), pos[1] - int(radius * 0.25))
        highlight_color = tuple(min(255, int(c * 1.3)) for c in color)
        pygame.draw.circle(screen, highlight_color, highlight_pos, max(3, int(radius * 0.3)))

class Game:
    """Main class to manage game states, logic, and rendering."""
    def __init__(self):
        # Ensure assets exist when running as a single file
        try:
            ensure_assets()
        except Exception as e:
            print(f"Asset preparation warning: {e}")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("CHAIN REACTION - MODERN EDITION")
        self.clock = pygame.time.Clock()
        self.load_assets()
        self.game_state = "menu"
        self.num_players = 0
        # Create gradient background surface
        self.background_gradient = self.create_gradient_surface(SCREEN_WIDTH, SCREEN_HEIGHT,
            COLOR["BACKGROUND_GRADIENT_TOP"], COLOR["BACKGROUND_GRADIENT_BOTTOM"])
        # Pre-render CRT scanlines
        self.crt_scanline_surface = self._create_crt_scanline_surface()
        self.time = 0

    def _create_crt_scanline_surface(self):
        """Pre-render CRT scanline effect for better performance"""
        scanline_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SCREEN_HEIGHT, 4):
            pygame.draw.line(scanline_surface, (0, 0, 0, 30), (0, y), (SCREEN_WIDTH, y), 2)
        return scanline_surface

    def create_gradient_surface(self, width, height, top_color, bottom_color):
        """Create a vertical gradient surface"""
        surface = pygame.Surface((width, height))
        for y in range(height):
            ratio = y / height
            r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
        return surface

    def load_assets(self):
        global FONT_PATH
        try:
            # Try to load pixel font for retro feel
            FONT_PATH = "assets/GameFont.ttf"
            # Responsive font sizes - reduced multipliers for smaller text
            self.font_small = pygame.font.Font(FONT_PATH, max(10, int(CELL_SIZE * 0.4)))
            self.font_medium = pygame.font.Font(FONT_PATH, max(14, int(CELL_SIZE * 0.8)))
            self.font_large = pygame.font.Font(FONT_PATH, max(20, int(CELL_SIZE * 1.2)))
        except FileNotFoundError:
            try:
                # Fallback to other fonts
                FONT_PATH = "assets/ChakraPetch-SemiBold.ttf"
                self.font_small = pygame.font.Font(FONT_PATH, max(10, int(CELL_SIZE * 0.4)))
                self.font_medium = pygame.font.Font(FONT_PATH, max(14, int(CELL_SIZE * 0.8)))
                self.font_large = pygame.font.Font(FONT_PATH, max(20, int(CELL_SIZE * 1.2)))
            except FileNotFoundError:
                try:
                    FONT_PATH = "assets/SpaceGrotesk-SemiBold.ttf"
                    self.font_small = pygame.font.Font(FONT_PATH, max(10, int(CELL_SIZE * 0.4)))
                    self.font_medium = pygame.font.Font(FONT_PATH, max(14, int(CELL_SIZE * 0.8)))
                    self.font_large = pygame.font.Font(FONT_PATH, max(20, int(CELL_SIZE * 1.2)))
                except FileNotFoundError:
                    # Final fallback to system font
                    FONT_PATH = None
                    self.font_small = pygame.font.SysFont("monospace", max(10, int(CELL_SIZE * 0.4)))
                    self.font_medium = pygame.font.SysFont("monospace", max(14, int(CELL_SIZE * 0.8)), bold=True)
                    self.font_large = pygame.font.SysFont("monospace", max(20, int(CELL_SIZE * 1.2)), bold=True)

        if FONT_PATH:
            self.font_tiny = pygame.font.Font(FONT_PATH, max(8, int(CELL_SIZE * 0.3)))
        else:
            self.font_tiny = pygame.font.SysFont("Arial", max(8, int(CELL_SIZE * 0.3)))
        
        # Title font: use Comic Sans MS for all CHAIN REACTION titles
        try:
            self.title_font = pygame.font.SysFont('Comic Sans MS', max(22, int(CELL_SIZE * 0.9)), bold=True)
        except Exception:
            # Fallback if Comic Sans not available
            if os.path.exists("assets/ChakraPetch-SemiBold.ttf"):
                self.title_font = pygame.font.Font("assets/ChakraPetch-SemiBold.ttf", max(22, int(CELL_SIZE * 0.9)))
            elif os.path.exists("assets/SpaceGrotesk-SemiBold.ttf"):
                self.title_font = pygame.font.Font("assets/SpaceGrotesk-SemiBold.ttf", max(22, int(CELL_SIZE * 0.9)))
            elif FONT_PATH:
                self.title_font = pygame.font.Font(FONT_PATH, max(22, int(CELL_SIZE * 0.9)))
            else:
                self.title_font = pygame.font.SysFont("Arial", max(22, int(CELL_SIZE * 0.9)), bold=True)
        except Exception:
            self.title_font = self.font_large

        self.sounds = {}
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            # Try loading sounds with fallback for file format
            sound_files = ['place', 'explode', 'win']
            for sound_name in sound_files:
                try:
                    self.sounds[sound_name] = pygame.mixer.Sound(f"assets/{sound_name}.ogg")
                except:
                    try:
                        self.sounds[sound_name] = pygame.mixer.Sound(f"assets/{sound_name}.wav")
                    except:
                        print(f"Could not load {sound_name} sound")
            
            # Try loading music
            try:
                pygame.mixer.music.load("assets/music.ogg")
                pygame.mixer.music.play(-1, fade_ms=2000)
                pygame.mixer.music.set_volume(0.3)
            except:
                try:
                    pygame.mixer.music.load("assets/music.wav")
                    pygame.mixer.music.play(-1, fade_ms=2000)
                    pygame.mixer.music.set_volume(0.3)
                except:
                    print("Could not load background music")
                    
        except (pygame.error, FileNotFoundError) as e:
            print(f"Sound loading error: {e}. Running without sound.")
            self.sounds = None

    def play_sound(self, name):
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
            
    def reset_game(self):
        self.grid = [[Cell(row, col) for col in range(GRID_WIDTH)] for row in range(GRID_HEIGHT)]
        self.current_player, self.turn_count, self.winner = 0, 0, None
        self.explosion_queue = deque()
        self.animated_orbs = []
        self.particles = []  # Add particle effects
        self.shake_duration = 0
        self.explosion_timer = 0  # Timer for explosion delay
        self.is_turn_processed = True # Flag to ensure next_turn is called only once

    def get_neighbors(self, row, col):
        neighbors = []
        if row > 0: neighbors.append(self.grid[row-1][col])
        if row < GRID_HEIGHT - 1: neighbors.append(self.grid[row+1][col])
        if col > 0: neighbors.append(self.grid[row][col-1])
        if col < GRID_WIDTH - 1: neighbors.append(self.grid[row][col+1])
        return neighbors

    def handle_click(self, pos):
        if self.explosion_queue or self.animated_orbs:
            return

        col, row = pos[0] // CELL_SIZE, (pos[1] - HEADER_HEIGHT) // CELL_SIZE
        if 0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT:
            cell = self.grid[row][col]
            if cell.owner is None or cell.owner == self.current_player:
                self.play_sound('place')
                self.is_turn_processed = False
                self.turn_count += 1
                cell.owner = self.current_player
                cell.orbs += 1
                cell.start_placement()
                if cell.orbs >= cell.critical_mass:
                    self.explosion_queue.append(cell)

    def trigger_shake(self):
        self.shake_duration = SHAKE_DURATION

    def update(self, dt):
        for row in self.grid:
            for cell in row:
                cell.update(dt)

        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]

        # Handle screen shake
        if self.shake_duration > 0:
            self.shake_duration -= dt

        # Update explosion timer
        if self.explosion_timer > 0:
            self.explosion_timer -= dt

        # Process explosions with delay for better visual feedback
        if self.explosion_queue and not self.animated_orbs and self.explosion_timer <= 0:
            cell = self.explosion_queue.popleft()
            self.play_sound('explode')
            self.trigger_shake()

            # Create particle effects at explosion
            color = PLAYER_COLORS[cell.owner]
            for _ in range(15):
                self.particles.append(Particle(cell.rect.center, color))

            cell.orbs -= cell.critical_mass
            if cell.orbs == 0:
                cell.owner = None

            for neighbor in self.get_neighbors(cell.row, cell.col):
                self.animated_orbs.append(AnimatedOrb(cell, neighbor, self.current_player))

            # Set timer for next explosion
            if self.explosion_queue:
                self.explosion_timer = EXPLOSION_DELAY

        # Update orb animations
        for orb in self.animated_orbs[:]:
            if orb.update(dt):
                self.animated_orbs.remove(orb)
                target = orb.target_cell
                target.owner = orb.player_id
                target.orbs += 1
                if target.orbs >= target.critical_mass:
                    self.explosion_queue.append(target)

        # Check if turn is over
        if not self.explosion_queue and not self.animated_orbs and not self.is_turn_processed:
            self.next_turn()
            self.is_turn_processed = True

    def next_turn(self):
        if self.turn_count >= self.num_players:
            active = {c.owner for r in self.grid for c in r if c.owner is not None}
            if len(active) == 1:
                self.winner = active.pop()
                self.game_state = "game_over"
                self.play_sound('win')
                return

        while True:
            self.current_player = (self.current_player + 1) % self.num_players
            if self.turn_count < self.num_players: break
            if any(c.owner == self.current_player for r in self.grid for c in r): break

    def draw(self):
        # Draw gradient background
        self.screen.blit(self.background_gradient, (0, 0))

        # Draw header with current turn
        self.draw_header()

        offset = [0, 0]
        if self.shake_duration > 0:
            offset[0] = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)
            offset[1] = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY)

        # Get mouse position for hover effect
        mouse_pos = pygame.mouse.get_pos()
        hover_cell = None
        header_height = HEADER_HEIGHT
        if not self.explosion_queue and not self.animated_orbs:
            col, row = mouse_pos[0] // CELL_SIZE, (mouse_pos[1] - header_height) // CELL_SIZE
            if 0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT:
                cell = self.grid[row][col]
                if cell.owner is None or cell.owner == self.current_player:
                    hover_cell = cell

        # Draw cells
        for row in self.grid:
            for cell in row:
                cell.rect.topleft = (cell.col * CELL_SIZE + offset[0], cell.row * CELL_SIZE + offset[1] + header_height)

                # Draw hover highlight
                if cell == hover_cell:
                    hover_color = PLAYER_COLORS[self.current_player]
                    hover_alpha = tuple(int(c * 0.15) for c in hover_color)
                    pygame.draw.rect(self.screen, hover_alpha, cell.rect)

                cell.draw(self.screen)

        # Draw 3D grid lines with player color
        self.draw_3d_grid(offset)

        # Draw particles (behind orbs)
        for particle in self.particles:
            particle.draw(self.screen)

        for orb in self.animated_orbs:
            orb.pos.x += offset[0]
            orb.pos.y += offset[1]
            orb.draw(self.screen)

        self.draw_ui()
        self.draw_crt_scanlines()
        pygame.display.flip()
        self.time += 1
    
    def draw_crt_scanlines(self):
        """Blit pre-rendered CRT scanline surface"""
        self.screen.blit(self.crt_scanline_surface, (0, 0))

    def _draw_gradient_line(self, start, end, base_color, start_alpha, end_alpha, width):
        """Render a line with opacity gradient to give a subtle depth effect."""
        if start[0] == end[0]:
            length = abs(end[1] - start[1])
            if length == 0:
                return
            surf = pygame.Surface((width, length), pygame.SRCALPHA)
            for i in range(length):
                ratio = i / max(1, length - 1)
                alpha = start_alpha + (end_alpha - start_alpha) * ratio
                pygame.draw.line(surf, (*base_color, int(alpha)), (0, i), (width - 1, i))
            top = min(start[1], end[1])
            self.screen.blit(surf, (int(start[0] - width // 2), int(top)))
        else:
            length = abs(end[0] - start[0])
            if length == 0:
                return
            surf = pygame.Surface((length, width), pygame.SRCALPHA)
            for i in range(length):
                ratio = i / max(1, length - 1)
                alpha = start_alpha + (end_alpha - start_alpha) * ratio
                pygame.draw.line(surf, (*base_color, int(alpha)), (i, 0), (i, width - 1))
            left = min(start[0], end[0])
            self.screen.blit(surf, (int(left), int(start[1] - width // 2)))
    
    def draw_3d_grid(self, offset):
        """Draw retro pixel grid lines with pulsing animation and transparency"""
        player_color = PLAYER_COLORS[self.current_player]
        header_height = HEADER_HEIGHT
        
        # Pulsing animation factor
        pulse = 0.85 + 0.25 * math.sin(self.time * 0.06)
        
        # Create retro neon colors with pulse
        grid_bright = tuple(min(255, int(player_color[i] * 0.9 * pulse + 30)) for i in range(3))
        grid_medium = tuple(int(player_color[i] * 0.5 * pulse + COLOR["GRID"][i] * 0.5) for i in range(3))
        
        # Create a transparent surface for grid lines
        grid_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Vertical lines
        for col in range(GRID_WIDTH + 1):
            x = col * CELL_SIZE + offset[0]
            pygame.draw.line(grid_surf, grid_bright + (120,),  # Add alpha for transparency
                             (x, offset[1] + header_height), 
                             (x, GRID_HEIGHT * CELL_SIZE + offset[1] + header_height), 1)
        
        # Horizontal lines
        for row in range(GRID_HEIGHT + 1):
            y = row * CELL_SIZE + offset[1] + header_height
            pygame.draw.line(grid_surf, grid_bright + (120,),  # Add alpha for transparency
                             (offset[0], y),
                             (GRID_WIDTH * CELL_SIZE + offset[0], y), 1)
        
        # Blit the transparent grid to the screen
        self.screen.blit(grid_surf, (0, 0))

    def draw_header(self):
        header_height = HEADER_HEIGHT

        # Background strip for header (keeps it clean)
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, header_height)
        pygame.draw.rect(self.screen, COLOR["UI_BACKGROUND"], header_rect)

        # Thin accent divider
        pygame.draw.line(self.screen, COLOR["ACCENT"], (0, header_height), (SCREEN_WIDTH, header_height), 2)

        # Right-side player card (extra left margin to avoid overlap)
        card_w = max(130, int(CELL_SIZE * 2.7))
        card_h = max(44, int(HEADER_HEIGHT * 0.7))
        card_margin = max(38, int(CELL_SIZE * 0.8))  # Increased margin
        card_rect = pygame.Rect(SCREEN_WIDTH - card_w - card_margin, (HEADER_HEIGHT - card_h) // 2, card_w, card_h)
        # Card background and border
        pygame.draw.rect(self.screen, (6, 8, 16), card_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR["ACCENT"], card_rect, 2, border_radius=10)

        # Modern, beautiful CHAIN REACTION title (always visible, auto-size)
        title_text = "CHAIN REACTION"
        base_title_font = getattr(self, 'title_font', self.font_large)
        max_title_w = card_rect.left - 38  # Space before turn box
        # Try decreasing font size until title fits
        size = base_title_font.get_height()
        min_size = 18
        while size > min_size:
            test_font = pygame.font.SysFont('Comic Sans MS', size, bold=True)
            test_surf = test_font.render(title_text, True, COLOR["WHITE"])
            if test_surf.get_width() <= max_title_w:
                title_font = test_font
                title_surf = test_surf
                break
            size -= 2
        else:
            title_font = pygame.font.SysFont('Comic Sans MS', min_size, bold=True)
            title_surf = title_font.render(title_text, True, COLOR["WHITE"])
        # Left-align title text
        title_rect = title_surf.get_rect(topleft=(28, HEADER_HEIGHT // 2 - title_surf.get_height() // 2))
        # Drop shadow
        shadow = title_font.render(title_text, True, (20, 30, 60))
        shadow_rect = shadow.get_rect(topleft=(title_rect.left + 3, title_rect.top + 3))
        self.screen.blit(shadow, shadow_rect)
        # Accent glow
        glow = title_font.render(title_text, True, COLOR["ACCENT"])
        for off in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            glow_rect = glow.get_rect(topleft=(title_rect.left + off[0], title_rect.top + off[1]))
            self.screen.blit(glow, glow_rect)
        # Gradient overlay
        grad = pygame.Surface(title_surf.get_size(), pygame.SRCALPHA)
        for y in range(title_surf.get_height()):
            ratio = y / title_surf.get_height()
            r = int(COLOR["WHITE"][0] * (1 - ratio) + COLOR["ACCENT"][0] * ratio)
            g = int(COLOR["WHITE"][1] * (1 - ratio) + COLOR["ACCENT"][1] * ratio)
            b = int(COLOR["WHITE"][2] * (1 - ratio) + COLOR["ACCENT"][2] * ratio)
            pygame.draw.line(grad, (r, g, b, 220), (0, y), (title_surf.get_width(), y))
        title_surf.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(title_surf, title_rect)

        # Player turn box: show only a colored orb and the label 'TURN' (no numbers or counts)
        player_color = PLAYER_COLORS[self.current_player]
        small = self.font_small

        # Orb scales with card height to remain visually balanced
        orb_radius = max(10, int(card_h * 0.36))
        orb_center = (card_rect.left + 14 + orb_radius, card_rect.centery)
        # Draw orb shadow + main orb + highlight
        pygame.draw.circle(self.screen, (18, 20, 32), (orb_center[0] + 2, orb_center[1] + 3), orb_radius + 2)
        pygame.draw.circle(self.screen, player_color, orb_center, orb_radius)
        pygame.draw.circle(self.screen, tuple(min(255, int(c * 1.12)) for c in player_color), (orb_center[0] - orb_radius//3, orb_center[1] - orb_radius//3), max(3, orb_radius//4))

        # TURN label: choose a font size that fits the remaining card space
        avail_w = card_rect.right - (orb_center[0] + orb_radius + 12) - 10
        # Start with a size relative to card height, then shrink until it fits
        try:
            base_font_path = FONT_PATH if 'FONT_PATH' in globals() and FONT_PATH else None
            test_size = max(10, int(card_h * 0.45))
            while test_size >= 10:
                try:
                    if base_font_path:
                        test_font = pygame.font.Font(base_font_path, test_size)
                    else:
                        test_font = pygame.font.SysFont(None, test_size, bold=True)
                except Exception:
                    test_font = pygame.font.SysFont(None, test_size, bold=True)
                test_surf = test_font.render("TURN", True, COLOR["WHITE"])
                if test_surf.get_width() <= avail_w or test_size <= 12:
                    turn_font = test_font
                    turn_surf = test_surf
                    break
                test_size -= 1
        except Exception:
            turn_font = self.font_medium
            turn_surf = turn_font.render("TURN", True, COLOR["WHITE"])

        turn_rect = turn_surf.get_rect(midleft=(orb_center[0] + orb_radius + 12, card_rect.centery))
        # Glow behind the TURN text for retro feel
        try:
            glow_surf = turn_font.render("TURN", True, COLOR["ACCENT"]) if turn_font else None
        except Exception:
            glow_surf = None
        if glow_surf:
            goff = max(1, int(test_size * 0.08))
            for off in [(goff, goff), (-goff, goff)]:
                gpos = (turn_rect.left + off[0], turn_rect.top + off[1])
                self.screen.blit(glow_surf, gpos)
        self.screen.blit(turn_surf, turn_rect)

    def draw_player_card(self, rect, player_id, orb_count, is_current, is_eliminated):
        """Render a compact player summary card in the UI strip."""
        base_color = PLAYER_COLORS[player_id]
        blend_color = tuple(int(COLOR["UI_BACKGROUND"][i] * 0.7 + base_color[i] * 0.3) for i in range(3))
        if is_eliminated:
            blend_color = tuple(int(blend_color[i] * 0.55 + 35) for i in range(3))

        pygame.draw.rect(self.screen, blend_color, rect, border_radius=12)

        border_color = COLOR["ACCENT"] if is_current else (70, 80, 105)
        if is_eliminated:
            border_color = (110, 60, 70)
        pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=12)

        # Orb icon
        orb_center = (rect.left + 26, rect.centery)
        shadow_color = (18, 20, 32)
        pygame.draw.circle(self.screen, shadow_color, (orb_center[0] + 2, orb_center[1] + 3), 18)

        orb_color = base_color if not is_eliminated else tuple(int(base_color[i] * 0.35 + 70) for i in range(3))
        pygame.draw.circle(self.screen, orb_color, orb_center, 16)
        highlight_color = tuple(min(255, int(orb_color[i] * 1.3)) for i in range(3))
        pygame.draw.circle(self.screen, highlight_color, (orb_center[0] - 5, orb_center[1] - 5), 6)

        # Draw player number inside the orb (instead of separate P# label)
        num_surf = self.font_tiny.render(str(player_id + 1), True, COLOR["WHITE"])
        num_rect = num_surf.get_rect(center=orb_center)
        self.screen.blit(num_surf, num_rect)

        # Status and counts
        status_text = "Your turn" if is_current else ("Eliminated" if is_eliminated else "In play")
        status_color = COLOR["ACCENT"] if is_current else ((220, 120, 130) if is_eliminated else (190, 200, 218))
        status_surf = self.font_tiny.render(status_text, True, status_color)
        self.screen.blit(status_surf, (rect.left + 54, rect.top + rect.height // 2 - 6))

        count_surf = self.font_tiny.render(f"{orb_count} orbs", True, (210, 215, 230))
        self.screen.blit(count_surf, (rect.left + 54, rect.bottom - 22))

    def draw_ui(self):
        ui_y = SCREEN_HEIGHT - UI_HEIGHT
        ui_rect = pygame.Rect(0, ui_y, SCREEN_WIDTH, UI_HEIGHT)

        # Draw gradient background
        for y in range(UI_HEIGHT):
            ratio = y / UI_HEIGHT
            r = int(COLOR["UI_GRADIENT_TOP"][0] * (1 - ratio) + COLOR["UI_GRADIENT_BOTTOM"][0] * ratio)
            g = int(COLOR["UI_GRADIENT_TOP"][1] * (1 - ratio) + COLOR["UI_GRADIENT_BOTTOM"][1] * ratio)
            b = int(COLOR["UI_GRADIENT_TOP"][2] * (1 - ratio) + COLOR["UI_GRADIENT_BOTTOM"][2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, ui_y + y), (SCREEN_WIDTH, ui_y + y))

        # Top accent line
        pygame.draw.line(self.screen, COLOR["ACCENT"], ui_rect.topleft, ui_rect.topright, 3)
        pygame.draw.line(self.screen, (50, 60, 100), (0, ui_y + 1), (SCREEN_WIDTH, ui_y + 1), 1)

        # Calculate orb counts for dominance bar
        orb_counts = [0] * self.num_players
        for row in self.grid:
            for cell in row:
                if cell.owner is not None:
                    orb_counts[cell.owner] += cell.orbs

        total_orbs = sum(orb_counts)
        
        # Dominance bar below the grid (filled segments + subtle animated overlay)
        if total_orbs > 0:
            bar_h = max(18, int(CELL_SIZE * 0.6))
            bar_padding = max(12, int(CELL_SIZE * 0.5))
            max_w = SCREEN_WIDTH - (bar_padding * 2)
            # Slight overlap with grid bottom to remove visual gap
            bar_y = HEADER_HEIGHT + GRID_HEIGHT * CELL_SIZE - (bar_h // 2)

            bg_rect = pygame.Rect(bar_padding, bar_y, max_w, bar_h)
            # Rounded dark background
            pygame.draw.rect(self.screen, (8, 10, 18), bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR["ACCENT"], bg_rect, 2, border_radius=8)

            # Draw player segments fully filled (no half cut). Use gradient fill per segment.
            # Compute exact pixel widths for each segment so the bar fully fills
            segment_widths = []
            for i in range(self.num_players):
                count = orb_counts[i]
                if count <= 0:
                    segment_widths.append(0)
                else:
                    w = int((count / total_orbs) * max_w)
                    segment_widths.append(max(0, w))
            # Fix rounding: ensure sum == max_w by adding remainder to the last non-zero
            total_assigned = sum(segment_widths)
            if total_assigned < max_w:
                # find last index with non-zero width
                for j in range(self.num_players - 1, -1, -1):
                    if segment_widths[j] > 0:
                        segment_widths[j] += (max_w - total_assigned)
                        break

            # Render the whole dominance bar into an offscreen surface so the water animation
            # is continuous and there are no gaps between segments.
            bar_s = pygame.Surface((max_w, bar_h), pygame.SRCALPHA)
            # Draw rounded dark background on bar surface
            pygame.draw.rect(bar_s, (8, 10, 18), bar_s.get_rect(), border_radius=8)

            # Draw contiguous colored segments onto bar_s (left-to-right), with rounded corners at ends
            bx = 0
            num_segments = sum(1 for w in segment_widths if w > 0)
            seg_idx = 0
            for i, w in enumerate(segment_widths):
                if w <= 0:
                    continue
                seg_rect_local = pygame.Rect(bx, 0, w, bar_h)
                base = PLAYER_COLORS[i]
                # Only one segment: round both ends
                if num_segments == 1:
                    pygame.draw.rect(bar_s, base, seg_rect_local, border_radius=8)
                else:
                    # First segment: round left
                    if seg_idx == 0:
                        pygame.draw.rect(bar_s, base, seg_rect_local, border_top_left_radius=8, border_bottom_left_radius=8)
                    # Last segment: round right
                    elif seg_idx == num_segments - 1:
                        pygame.draw.rect(bar_s, base, seg_rect_local, border_top_right_radius=8, border_bottom_right_radius=8)
                    # Middle segments: no rounding
                    else:
                        pygame.draw.rect(bar_s, base, seg_rect_local, border_radius=0)
                bx += w
                seg_idx += 1

            # Add inner tinted highlight across the whole bar
            highlight = pygame.Surface((max_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(highlight, (255,255,255,18), highlight.get_rect(), border_radius=8)
            bar_s.blit(highlight, (0,0), special_flags=0)

            # Global water wave computed for full width (continuous)
            steps = max(120, max_w // 2)
            phase = self.time * (DOM_WAVE_SPEED * 8.0)
            amp = max(3, int(bar_h * DOM_WAVE_AMPLITUDE_FACTOR))
            wave_points = []
            for sx in range(steps + 1):
                gx = int((sx / steps) * max_w)
                gy = int((bar_h * 0.5) + math.sin(phase + sx * 0.28) * amp)
                wave_points.append((gx, gy))

            # Build polygon for the water (full bar local coords)
            poly = [(max_w, bar_h)] + wave_points + [(0, bar_h)]
            wave_surf = pygame.Surface((max_w, bar_h), pygame.SRCALPHA)
            # For each x, we need the underlying segment color. To avoid per-pixel loops,
            # draw a slightly darker semi-transparent layer on top using a multiply-like tint.
            # We'll create a mask polygon and then blend using per-segment tints by drawing
            # the polygon once with white and multiply visually via alpha.
            # Instead, choose a neutral darkening color (black at low alpha) and then overlay
            # a lighter translucent fill of the segment colors using the original bar_s content.
            pygame.draw.polygon(wave_surf, (0, 0, 0, 120), [(x, y) for x, y in poly])

            # Composite: first blit bar_s, then draw wave_surf on top (alpha blended)
            self.screen.blit(bar_s, (bar_padding, bar_y))
            self.screen.blit(wave_surf, (bar_padding, bar_y))
            
    def run_menu(self):
        # Fresh retro menu design
        title_font = getattr(self, 'title_font', self.font_large)
        header_text = "CHAIN REACTION"

        # Menu options
        options = list(range(2, 10))

        # Tile sizing (slightly smaller)
        tile_w = max(120, int(CELL_SIZE * 3.0))
        tile_h = max(64, int(CELL_SIZE * 1.5))
        cols = 3
        gap = max(14, int(CELL_SIZE * 0.4))

        # Compute grid layout and centering
        rows = (len(options) + cols - 1) // cols
        grid_w = cols * tile_w + (cols - 1) * gap
        grid_h = rows * tile_h + (rows - 1) * gap
        grid_left = (SCREEN_WIDTH - grid_w) // 2
        grid_top = int(SCREEN_HEIGHT * 0.32)

        # Build rects for each option, centering incomplete last row
        rects = []
        for idx, val in enumerate(options):
            r = idx // cols
            c = idx % cols
            # center last row
            items_in_row = cols if (r < rows - 1 or len(options) % cols == 0) else (len(options) % cols)
            row_grid_w = items_in_row * tile_w + (items_in_row - 1) * gap
            row_left = (SCREEN_WIDTH - row_grid_w) // 2
            x = row_left + c * (tile_w + gap)
            y = grid_top + r * (tile_h + gap)
            rects.append(pygame.Rect(x, y, tile_w, tile_h))

        hover_idx = None
        select_idx = 0

        # helper: draw programmatic retro logo (returns surface)
        def make_retro_logo(size):
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            cx = cy = size // 2
            # layered neon circles
            for i, alpha, rad_mul in [(0, 30, 1.0), (1, 60, 0.86), (2, 120, 0.72)]:
                r = int(size * (0.5 * rad_mul))
                col = tuple(min(255, int(c * (0.8 + i * 0.08))) for c in COLOR['ACCENT'])
                pygame.draw.circle(s, (*col, alpha), (cx, cy), r)
            # dark center
            pygame.draw.circle(s, (6, 8, 14), (cx, cy), int(size * 0.42))
            # big CR letters in blocky retro style
            try:
                f = pygame.font.Font(FONT_PATH, int(size * 0.36)) if FONT_PATH else pygame.font.SysFont(None, int(size * 0.36), bold=True)
            except Exception:
                f = pygame.font.SysFont(None, int(size * 0.36), bold=True)
            txt = f.render('CR', True, (230, 240, 255))
            tr = txt.get_rect(center=(cx, cy))
            s.blit(txt, tr)
            # small scanline overlay
            for y in range(0, size, 4):
                pygame.draw.line(s, (255, 255, 255, 6), (0, y), (size, y))
            return s

        logo_s = make_retro_logo(max(64, int(CELL_SIZE * 2.5)))

        instructions_font = self.font_small if hasattr(self, 'font_small') else self.font

        while self.game_state == 'menu':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEMOTION:
                    hover_idx = None
                    for i, r in enumerate(rects):
                        if r.collidepoint(event.pos):
                            hover_idx = i
                            break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for i, r in enumerate(rects):
                        if r.collidepoint(event.pos):
                            select_idx = i
                            self.num_players = options[i]
                            self.reset_game()
                            self.game_state = 'playing'
                            break
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RIGHT, pygame.K_d):
                        select_idx = min(len(options) - 1, select_idx + 1)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        select_idx = max(0, select_idx - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        select_idx = min(len(options) - 1, select_idx + cols)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        select_idx = max(0, select_idx - cols)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.num_players = options[select_idx]
                        self.reset_game()
                        self.game_state = 'playing'

            # Draw
            self.screen.blit(self.background_gradient, (0, 0))

            # Modern, beautiful CHAIN REACTION title with logo
            spacing = max(8, int(CELL_SIZE * 0.3))  # Reduced gap for tighter alignment
            logo_w = logo_s.get_width()
            logo_h = logo_s.get_height()
            # Create styled title
            menu_title_font = getattr(self, 'title_font', self.font_large)
            menu_title_surf = menu_title_font.render(header_text, True, COLOR['WHITE'])
            # Drop shadow
            menu_shadow = menu_title_font.render(header_text, True, (20, 30, 60))
            # Accent glow
            menu_glow = menu_title_font.render(header_text, True, COLOR['ACCENT'])
            # Gradient overlay
            grad = pygame.Surface(menu_title_surf.get_size(), pygame.SRCALPHA)
            for y in range(menu_title_surf.get_height()):
                ratio = y / menu_title_surf.get_height()
                r = int(COLOR['WHITE'][0] * (1 - ratio) + COLOR['ACCENT'][0] * ratio)
                g = int(COLOR['WHITE'][1] * (1 - ratio) + COLOR['ACCENT'][1] * ratio)
                b = int(COLOR['WHITE'][2] * (1 - ratio) + COLOR['ACCENT'][2] * ratio)
                pygame.draw.line(grad, (r, g, b, 220), (0, y), (menu_title_surf.get_width(), y))
            menu_title_surf.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            # Center block for logo + title
            title_w = menu_title_surf.get_width()
            title_h = menu_title_surf.get_height()
            combined_w = logo_w + spacing + title_w
            top_y = int(SCREEN_HEIGHT * 0.055)  # Slightly less top padding
            # Align logo and title to same baseline (centered block, minimal gap)
            combined_h = max(logo_h, title_h)
            start_x = (SCREEN_WIDTH - combined_w) // 2
            logo_x = start_x
            # Align logo and title to same vertical center
            logo_y = top_y + (combined_h - logo_h) // 2
            title_x = logo_x + logo_w + spacing
            title_y = top_y + (combined_h - title_h) // 2
            # Draw logo
            logo_path = os.path.join('assets', 'logo.png')
            if os.path.exists(logo_path):
                try:
                    user_logo = pygame.image.load(logo_path).convert_alpha()
                    us = pygame.transform.smoothscale(user_logo, (logo_w, logo_s.get_height()))
                    self.screen.blit(us, (logo_x, logo_y))
                except Exception:
                    self.screen.blit(logo_s, (logo_x, logo_y))
            else:
                self.screen.blit(logo_s, (logo_x, logo_y))
            # Draw styled title: shadow, glow, gradient
            shadow_rect = menu_shadow.get_rect(topleft=(title_x + 3, title_y + 3))
            self.screen.blit(menu_shadow, shadow_rect)
            for off in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
                glow_rect = menu_glow.get_rect(topleft=(title_x + off[0], title_y + off[1]))
                self.screen.blit(menu_glow, glow_rect)
            self.screen.blit(menu_title_surf, (title_x, title_y))

            # draw grid of tiles
            for i, r in enumerate(rects):
                is_hover = (hover_idx == i)
                is_selected = (select_idx == i)
                # tile background
                base_col = COLOR['BUTTON_HOVER'] if is_hover or is_selected else COLOR['BUTTON']
                pygame.draw.rect(self.screen, base_col, r, border_radius=12)
                pygame.draw.rect(self.screen, COLOR['ACCENT'], r, 2, border_radius=12)
                # label (no orb preview) — center text inside tile with shadow + accent
                label = f"{options[i]} Players"
                try:
                    lf = pygame.font.SysFont('Comic Sans MS', max(14, int(tile_h * 0.26)), bold=True)
                except Exception:
                    try:
                        menu_font_path = os.path.join('assets', 'SpaceGrotesk-SemiBold.ttf')
                        lf = pygame.font.Font(menu_font_path, max(14, int(tile_h * 0.26)))
                    except Exception:
                        try:
                            lf = pygame.font.Font(FONT_PATH, max(14, int(tile_h * 0.26))) if FONT_PATH else pygame.font.SysFont(None, max(14, int(tile_h * 0.26)), bold=True)
                        except Exception:
                            lf = pygame.font.SysFont(None, max(14, int(tile_h * 0.26)), bold=True)
                txt_accent = lf.render(label, True, COLOR['ACCENT'])
                txt_shadow = lf.render(label, True, (6, 8, 14))
                txt = lf.render(label, True, COLOR['WHITE'])
                tx = r.left + (r.w - txt.get_width()) // 2
                ty_label = r.top + (r.h - txt.get_height()) // 2
                # subtle accent halo
                acc_s = txt_accent.copy()
                try:
                    acc_s.set_alpha(120)
                except Exception:
                    pass
                self.screen.blit(acc_s, (tx - 1, ty_label - 1))
                # shadow and main text
                self.screen.blit(txt_shadow, (tx + 2, ty_label + 2))
                self.screen.blit(txt, (tx, ty_label))

                # small hint for selected tile
                if is_selected:
                    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                    pygame.draw.rect(s, (255,255,255,14), s.get_rect(), border_radius=12)
                    self.screen.blit(s, (r.left, r.top))

            # (instructions removed for cleaner look)

            pygame.display.flip()
            self.clock.tick(FPS)

    def run_game_over(self):
        winner_text = self.font_large.render(f"PLAYER {self.winner + 1} WINS!", True, PLAYER_COLORS[self.winner])
        winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 60))
        menu_button = Button((0,0,250,50), "MAIN MENU")
        menu_button.rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 60)

        while self.game_state == "game_over":
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if menu_button.handle_event(event):
                    self.game_state = "menu"
            
            # Draw gradient background
            self.screen.blit(self.background_gradient, (0, 0))
            
            # Draw simple winner text
            self.screen.blit(winner_text, winner_rect)
            
            menu_button.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)

    def run(self):
        while True:
            if self.game_state == "menu": self.run_menu()
            elif self.game_state == "playing":
                dt = self.clock.tick(FPS) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                    if event.type == pygame.MOUSEBUTTONDOWN: self.handle_click(event.pos)
                self.update(dt)
                self.draw()
            elif self.game_state == "game_over": self.run_game_over()

if __name__ == "__main__":
    game = Game()
    game.run()
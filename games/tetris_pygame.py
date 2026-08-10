#!/usr/bin/env python3
"""A polished Pygame Tetris variant."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

try:
    import pygame
except ImportError as exc:
    raise SystemExit(
        "Pygame is required. Activate the environment that provides it, then "
        "run: python tetris_pygame.py"
    ) from exc


WINDOW_WIDTH, WINDOW_HEIGHT = 760, 760
ROWS, COLS = 20, 10
CELL = 30
BOARD_X, BOARD_Y = 92, 92
BOARD_WIDTH, BOARD_HEIGHT = COLS * CELL, ROWS * CELL
FPS = 60
GAME_OVER_SECONDS = 3.0

LOCK_DELAY = 0.50
MAX_LOCK_RESETS = 15
DAS = 0.145                 # Delay before held horizontal movement repeats.
ARR = 0.042                 # Horizontal auto-repeat interval.
SOFT_DROP_INTERVAL = 0.035
LINE_CLEAR_TIME = 0.22
BASE_GRAVITY_INTERVAL = 0.62   # Seconds per gravity step at level 1.
MIN_GRAVITY_INTERVAL = 0.07    # Hard floor on the interval: the game's top speed.
GRAVITY_DECAY = 0.86           # Per-level shrink of the gravity interval.

# First level at which the gravity curve reaches its floor.
SPEED_CAP_LEVEL = math.ceil(math.log(MIN_GRAVITY_INTERVAL / BASE_GRAVITY_INTERVAL)
                            / math.log(GRAVITY_DECAY) + 1)

BLACK = (5, 7, 14)
NAVY = (11, 16, 31)
PANEL = (15, 22, 41)
GRID = (30, 42, 67)
WHITE = (235, 242, 255)
DIM = (100, 119, 151)
CYAN = (53, 220, 255)
YELLOW = (255, 219, 76)
MAGENTA = (220, 91, 255)
GREEN = (91, 231, 91)
RED = (255, 84, 91)
BLUE = (65, 121, 255)
ORANGE = (255, 157, 67)

COLORS = {
    "I": CYAN,
    "O": YELLOW,
    "T": MAGENTA,
    "S": GREEN,
    "Z": RED,
    "J": BLUE,
    "L": ORANGE,
}

PIECE_KEYS = tuple(COLORS)
PIECES = {
    "I": {"cells": ((1, 0), (1, 1), (1, 2), (1, 3)), "size": 4},
    "O": {"cells": ((0, 0), (0, 1), (1, 0), (1, 1)), "size": 2},
    "T": {"cells": ((0, 1), (1, 0), (1, 1), (1, 2)), "size": 3},
    "S": {"cells": ((0, 1), (0, 2), (1, 0), (1, 1)), "size": 3},
    "Z": {"cells": ((0, 0), (0, 1), (1, 1), (1, 2)), "size": 3},
    "J": {"cells": ((0, 0), (1, 0), (1, 1), (1, 2)), "size": 3},
    "L": {"cells": ((0, 2), (1, 0), (1, 1), (1, 2)), "size": 3},
}

LINE_SCORES = (0, 100, 300, 500, 800)
TETRIS_BONUS = 400

# Shared JSON store so future games can reuse the same file with their own key.
HIGH_SCORE_FILE = Path(__file__).resolve().with_name("game_high_scores.json")
GAME_ID = "tetris"


def load_high_score() -> int:
    """Read this game's persistent high score, defaulting to 0."""
    try:
        data = json.loads(HIGH_SCORE_FILE.read_text())
        return max(0, int(data.get(GAME_ID, 0)))
    except (OSError, ValueError, AttributeError):
        return 0


def save_high_score(score: int) -> None:
    """Persist this game's high score without disturbing other games' entries.

    Errors are ignored so gameplay never crashes over a score file.
    """
    try:
        try:
            data = json.loads(HIGH_SCORE_FILE.read_text())
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data[GAME_ID] = score
        HIGH_SCORE_FILE.write_text(json.dumps(data, indent=2) + "\n")
    except OSError:
        pass


def rotate_cells(cells: tuple[tuple[int, int], ...], size: int):
    return tuple((column, size - 1 - row) for row, column in cells)


def build_rotations():
    result = {}
    for key in PIECE_KEYS:
        cells = PIECES[key]["cells"]
        states = [cells]
        for _ in range(3):
            cells = rotate_cells(cells, PIECES[key]["size"])
            states.append(cells)
        result[key] = tuple(states)
    return result


ROTATIONS = build_rotations()

# Practical SRS-style kicks. I pieces receive their wider horizontal kicks;
# the remaining pieces use the common compact kick set.
NORMAL_KICKS = ((0, 0), (0, -1), (0, 1), (-1, 0),
                (-1, -1), (-1, 1), (0, -2), (0, 2), (-2, 0))
I_KICKS = ((0, 0), (0, -1), (0, 1), (0, -2), (0, 2),
           (-1, 0), (-2, 0), (-1, -2), (-1, 2))


@dataclass
class Piece:
    key: str
    rotation: int
    row: int
    column: int

    def copy(self) -> "Piece":
        return Piece(self.key, self.rotation, self.row, self.column)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    life: float


class Tetris:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Tetris")
        self.fullscreen = False
        self.windowed_size = self._initial_window_size()
        self.display = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("Menlo", 15, bold=True)
        self.font_medium = pygame.font.SysFont("Menlo", 24, bold=True)
        self.font_large = pygame.font.SysFont("Menlo", 57, bold=True)
        self.font_huge = pygame.font.SysFont("Menlo", 76, bold=True)
        self.rng = random.Random()
        star_rng = random.Random(1984)
        self.stars = [(star_rng.randrange(WINDOW_WIDTH),
                       star_rng.randrange(WINDOW_HEIGHT),
                       star_rng.choice((1, 1, 1, 2))) for _ in range(80)]
        self.high_score = load_high_score()
        self.last_score: int | None = None
        self.state = "title"
        self.animation_time = 0.0
        self.particles: list[Particle] = []

    @staticmethod
    def _initial_window_size() -> tuple[int, int]:
        info = pygame.display.Info()
        scale = min(info.current_w * 0.92 / WINDOW_WIDTH,
                    info.current_h * 0.90 / WINDOW_HEIGHT)
        scale = max(0.55, scale)
        return round(WINDOW_WIDTH * scale), round(WINDOW_HEIGHT * scale)

    def _toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self.display = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.fullscreen = False
        else:
            self.windowed_size = self.display.get_size()
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.fullscreen = True

    def new_game(self) -> None:
        self.grid: list[list[str | None]] = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.score_fraction = 0.0
        self.lines = 0
        self.level = 1
        self.bag: list[str] = []
        self.next_queue: list[str] = []
        self.held_key: str | None = None
        self.can_hold = True
        self.current: Piece | None = None
        self.gravity_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.horizontal_direction = 0
        self.horizontal_hold = 0.0
        self.horizontal_repeat = 0.0
        self.soft_drop_timer = 0.0
        self.line_clear_rows: list[int] = []
        self.line_clear_timer = 0.0
        self.game_over_timer = 0.0
        self.particles = []
        self.last_score = None
        self._fill_queue()
        self._spawn_piece()
        self.state = "playing"

    def _take_from_bag(self) -> str:
        if not self.bag:
            self.bag = list(PIECE_KEYS)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def _fill_queue(self) -> None:
        while len(self.next_queue) < 4:
            self.next_queue.append(self._take_from_bag())

    def _spawn_piece(self, key: str | None = None) -> None:
        if key is None:
            key = self.next_queue.pop(0)
            self._fill_queue()
        size = PIECES[key]["size"]
        self.current = Piece(key, 0, 0, (COLS - size) // 2)
        self.gravity_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        self.can_hold = True
        if not self._fits(self.current):
            self._game_over()

    def _cells(self, piece: Piece | None = None):
        piece = piece or self.current
        if piece is None:
            return []
        return [(piece.row + row, piece.column + column)
                for row, column in ROTATIONS[piece.key][piece.rotation]]

    def _fits(self, piece: Piece) -> bool:
        for row, column in self._cells(piece):
            if column < 0 or column >= COLS or row >= ROWS:
                return False
            if row >= 0 and self.grid[row][column] is not None:
                return False
        return True

    def _try_move(self, dr: int, dc: int, player_action: bool = False) -> bool:
        if self.current is None:
            return False
        candidate = self.current.copy()
        candidate.row += dr
        candidate.column += dc
        if not self._fits(candidate):
            return False
        self.current = candidate
        if player_action:
            self._after_player_action()
        return True

    def _try_rotate(self, direction: int) -> bool:
        if self.current is None or self.current.key == "O":
            return False
        new_rotation = (self.current.rotation + direction) % 4
        kicks = I_KICKS if self.current.key == "I" else NORMAL_KICKS
        for dr, dc in kicks:
            candidate = self.current.copy()
            candidate.rotation = new_rotation
            candidate.row += dr
            candidate.column += dc
            if self._fits(candidate):
                self.current = candidate
                self._after_player_action()
                return True
        return False

    def _after_player_action(self) -> None:
        if self.current is None:
            return
        below = self.current.copy()
        below.row += 1
        if self._fits(below):
            self.lock_timer = 0.0
        elif self.lock_resets < MAX_LOCK_RESETS:
            self.lock_timer = 0.0
            self.lock_resets += 1

    def _hard_drop(self) -> None:
        if self.current is None:
            return
        distance = 0
        while self._try_move(1, 0):
            distance += 1
        self._award_drop_points(distance, 2)
        self._lock_piece()

    def _hold(self) -> None:
        if not self.can_hold or self.current is None:
            return
        old_key = self.current.key
        self.can_hold = False
        if self.held_key is None:
            self.held_key = old_key
            key = self.next_queue.pop(0)
            self._fill_queue()
        else:
            key, self.held_key = self.held_key, old_key
        size = PIECES[key]["size"]
        self.current = Piece(key, 0, 0, (COLS - size) // 2)
        self.gravity_timer = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        if not self._fits(self.current):
            self._game_over()

    def _lock_piece(self) -> None:
        if self.current is None:
            return
        cells = self._cells()
        if any(row < 0 for row, _ in cells):
            self._game_over()
            return
        for row, column in cells:
            self.grid[row][column] = self.current.key
        self.current = None
        full_rows = [row for row in range(ROWS)
                     if all(self.grid[row][column] is not None for column in range(COLS))]
        if full_rows:
            self.line_clear_rows = full_rows
            self.line_clear_timer = LINE_CLEAR_TIME
            self._make_line_particles(full_rows)
        else:
            self._spawn_piece()

    def _finish_line_clear(self) -> None:
        cleared = len(self.line_clear_rows)
        for row in sorted(self.line_clear_rows, reverse=True):
            del self.grid[row]
        for _ in range(cleared):
            self.grid.insert(0, [None] * COLS)
        # Score this clear at the level and gravity speed it was played at.
        # Clearing all four rows earns an additional scaled Tetris bonus.
        base_points = LINE_SCORES[cleared]
        if cleared == 4:
            base_points += TETRIS_BONUS
        self._award_points(base_points)
        self.lines += cleared
        self.level = self.lines // 10 + 1
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)
        self.line_clear_rows = []
        self.line_clear_timer = 0.0
        self._spawn_piece()

    def _make_line_particles(self, rows: list[int]) -> None:
        for row in rows:
            for column in range(COLS):
                key = self.grid[row][column]
                color = COLORS[key] if key else WHITE
                x = BOARD_X + column * CELL + CELL / 2
                y = BOARD_Y + row * CELL + CELL / 2
                for _ in range(3):
                    self.particles.append(Particle(
                        x, y, self.rng.uniform(-170, 170), self.rng.uniform(-230, -70),
                        color, self.rng.uniform(0.45, 0.9)))

    def _gravity_interval(self) -> float:
        # Smooth modern curve with a useful lower bound at high levels.
        return max(MIN_GRAVITY_INTERVAL,
                   BASE_GRAVITY_INTERVAL * (GRAVITY_DECAY ** (self.level - 1)))

    def _speed_multiplier(self) -> float:
        """Actual gravity-speed increase relative to level 1."""
        return BASE_GRAVITY_INTERVAL / self._gravity_interval()

    def _score_multiplier(self) -> float:
        """Preserve level rewards and add the extra difficulty from speed.

        The speed bonus grows until gravity reaches its floor. After that,
        it remains capped while the level portion keeps increasing.
        Subtracting one avoids counting the level-1 baseline twice.
        """
        return self.level + self._speed_multiplier() - 1.0

    def _award_points(self, base_points: int) -> None:
        """Award scaled points without discarding fractional bonuses."""
        scaled_points = (
            base_points * self._score_multiplier() + self.score_fraction
        )
        awarded = int(scaled_points)
        self.score += awarded
        self.score_fraction = scaled_points - awarded

    def _award_drop_points(self, cells: int, base_per_cell: int) -> None:
        """Score a soft/hard drop with the shared difficulty multiplier."""
        self._award_points(cells * base_per_cell)

    def _game_over(self) -> None:
        if self.state == "game_over":
            return
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)
        self.last_score = self.score
        self.current = None
        self.game_over_timer = GAME_OVER_SECONDS
        self.state = "game_over"

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.animation_time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    # Pygame 2 resizes its display Surface automatically.
                    # Calling set_mode() here creates a resize feedback loop
                    # with Wayland compositors such as Hyprland.
                    self.display = pygame.display.get_surface()
                    self.windowed_size = self.display.get_size()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif self.state == "title":
                        if event.key in (pygame.K_q, pygame.K_ESCAPE):
                            running = False
                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            self.new_game()
                    elif self.state == "paused":
                        if event.key in (pygame.K_q, pygame.K_ESCAPE):
                            running = False
                        elif event.key in (pygame.K_p, pygame.K_SPACE):
                            self.state = "playing"
                    elif self.state == "playing":
                        if event.key in (pygame.K_q, pygame.K_ESCAPE):
                            running = False
                        elif event.key == pygame.K_p:
                            self.state = "paused"
                            self._stop_horizontal()
                        elif not self.line_clear_rows:
                            self._handle_keydown(event.key)
                elif event.type == pygame.KEYUP and self.state == "playing":
                    if ((event.key in (pygame.K_LEFT, pygame.K_a)
                         and self.horizontal_direction < 0)
                            or (event.key in (pygame.K_RIGHT, pygame.K_d)
                                and self.horizontal_direction > 0)):
                        self._switch_to_other_held_direction()

            if self.state == "playing":
                self.update(dt)
            elif self.state == "game_over":
                self._update_game_over(dt)
            else:
                self._update_particles(dt)
            self.draw()
        pygame.quit()

    def _update_game_over(self, dt: float) -> None:
        self.game_over_timer = max(0.0, self.game_over_timer - dt)
        self._update_particles(dt)
        if self.game_over_timer <= 0:
            self.state = "title"

    def _handle_keydown(self, key: int) -> None:
        if key in (pygame.K_LEFT, pygame.K_a):
            self._start_horizontal(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._start_horizontal(1)
        elif key in (pygame.K_UP, pygame.K_w, pygame.K_x):
            self._try_rotate(1)
        elif key == pygame.K_z:
            self._try_rotate(-1)
        elif key == pygame.K_DOWN or key == pygame.K_s:
            if self._try_move(1, 0):
                self._award_drop_points(1, 1)
            self.soft_drop_timer = 0.0
        elif key == pygame.K_SPACE:
            self._hard_drop()
        elif key == pygame.K_c:
            self._hold()

    def _start_horizontal(self, direction: int) -> None:
        self.horizontal_direction = direction
        self.horizontal_hold = 0.0
        self.horizontal_repeat = 0.0
        self._try_move(0, direction, player_action=True)

    def _stop_horizontal(self) -> None:
        self.horizontal_direction = 0
        self.horizontal_hold = 0.0
        self.horizontal_repeat = 0.0

    def _switch_to_other_held_direction(self) -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self._start_horizontal(-1)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self._start_horizontal(1)
        else:
            self._stop_horizontal()

    def update(self, dt: float) -> None:
        self._update_particles(dt)
        if self.line_clear_rows:
            self.line_clear_timer -= dt
            if self.line_clear_timer <= 0:
                self._finish_line_clear()
            return
        if self.current is None:
            return

        if self.horizontal_direction:
            self.horizontal_hold += dt
            if self.horizontal_hold >= DAS:
                self.horizontal_repeat += dt
                while self.horizontal_repeat >= ARR:
                    self._try_move(0, self.horizontal_direction, player_action=True)
                    self.horizontal_repeat -= ARR

        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.soft_drop_timer += dt
            while self.soft_drop_timer >= SOFT_DROP_INTERVAL:
                if self._try_move(1, 0):
                    self._award_drop_points(1, 1)
                self.soft_drop_timer -= SOFT_DROP_INTERVAL
        else:
            self.soft_drop_timer = 0.0

        self.gravity_timer += dt
        interval = self._gravity_interval()
        while self.gravity_timer >= interval:
            if not self._try_move(1, 0):
                break
            self.gravity_timer -= interval

        below = self.current.copy()
        below.row += 1
        if self._fits(below):
            self.lock_timer = 0.0
        else:
            self.lock_timer += dt
            if self.lock_timer >= LOCK_DELAY:
                self._lock_piece()

    def _update_particles(self, dt: float) -> None:
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 420 * dt
            particle.life -= dt
        self.particles = [particle for particle in self.particles if particle.life > 0]

    def draw(self) -> None:
        self.screen.fill(BLACK)
        if self.state == "title":
            self._draw_title()
        else:
            self._draw_game()
            if self.state == "paused":
                self._draw_overlay()
            elif self.state == "game_over":
                self._draw_game_over_animation()
        self._present()

    def _draw_game_over_animation(self) -> None:
        progress = 1.0 - self.game_over_timer / GAME_OVER_SECONDS
        shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, min(188, round(210 * progress))))
        self.screen.blit(shade, (0, 0))

        entrance = min(1.0, progress / 0.25)
        entrance = 1.0 - (1.0 - entrance) ** 3
        scale = 0.42 + 0.58 * entrance
        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 9)
        colors = ((255, round(70 + 100 * pulse), 86),
                  (255, round(135 + 90 * pulse), 65))
        for (text, y), color in zip((("GAME", 328), ("OVER", 420)), colors):
            surface = self.font_huge.render(text, True, color)
            size = (max(1, round(surface.get_width() * scale)),
                    max(1, round(surface.get_height() * scale)))
            surface = pygame.transform.smoothscale(surface, size)
            self.screen.blit(surface,
                             surface.get_rect(center=(WINDOW_WIDTH // 2, y)))
        pygame.draw.line(self.screen, RED, (190, 474), (WINDOW_WIDTH - 190, 474), 3)
        if self.game_over_timer < 0.75:
            self._text("RETURNING TO TITLE…", (WINDOW_WIDTH // 2, 514),
                       self.font_small, WHITE, center=True)

    def _present(self) -> None:
        display_width, display_height = self.display.get_size()
        scale = min(display_width / WINDOW_WIDTH, display_height / WINDOW_HEIGHT)
        target_size = (max(1, round(WINDOW_WIDTH * scale)),
                       max(1, round(WINDOW_HEIGHT * scale)))
        frame = pygame.transform.smoothscale(self.screen, target_size)
        self.display.fill(BLACK)
        self.display.blit(frame, ((display_width - target_size[0]) // 2,
                                  (display_height - target_size[1]) // 2))
        pygame.display.flip()

    def _draw_game(self) -> None:
        for x, y, radius in self.stars:
            pygame.draw.circle(self.screen, (47, 62, 91), (x, y), radius)
        board_outer = pygame.Rect(BOARD_X - 5, BOARD_Y - 5,
                                  BOARD_WIDTH + 10, BOARD_HEIGHT + 10)
        pygame.draw.rect(self.screen, NAVY, board_outer, border_radius=8)
        pygame.draw.rect(self.screen, CYAN, board_outer, width=2, border_radius=8)
        for row in range(ROWS):
            for column in range(COLS):
                rect = pygame.Rect(BOARD_X + column * CELL,
                                   BOARD_Y + row * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, GRID, rect, width=1)
                key = self.grid[row][column]
                if key:
                    flash = row in self.line_clear_rows and int(
                        self.line_clear_timer * 30) % 2 == 0
                    self._draw_block(rect, WHITE if flash else COLORS[key])

        if self.current:
            for row, column in self._cells():
                if row >= 0:
                    rect = pygame.Rect(BOARD_X + column * CELL,
                                       BOARD_Y + row * CELL, CELL, CELL)
                    self._draw_block(rect, COLORS[self.current.key])

        for particle in self.particles:
            pygame.draw.rect(self.screen, particle.color,
                             (round(particle.x), round(particle.y), 5, 5))

        panel = pygame.Rect(430, 92, 256, 600)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.screen, (48, 65, 99), panel, width=2, border_radius=10)
        self._text("NEXT", (458, 116), self.font_medium, WHITE)
        for index, key in enumerate(self.next_queue[:3]):
            self._draw_preview(key, pygame.Rect(451, 153 + index * 91, 214, 72),
                               scale=18 if index else 20)
        self._text("HOLD", (458, 432), self.font_medium, WHITE)
        self._draw_preview(self.held_key, pygame.Rect(451, 466, 214, 76), scale=20)

        self._text(f"SCORE   {self.score:07d}", (458, 565), self.font_small, WHITE)
        self._text(f"HIGH    {self.high_score:07d}", (458, 591), self.font_small, DIM)
        self._text(f"LEVEL   {self.level:02d}", (458, 617), self.font_small, WHITE)
        self._text(f"LINES   {self.lines:03d}", (458, 643), self.font_small, WHITE)

        self._text("←/→ MOVE   ↓ SOFT DROP   SPACE HARD DROP",
                   (WINDOW_WIDTH // 2, 716), self.font_small, DIM, center=True)
        self._text("Z/X ROTATE   C HOLD   P PAUSE   Q QUIT",
                   (WINDOW_WIDTH // 2, 740), self.font_small, DIM, center=True)

    def _draw_block(self, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
        tile = rect.inflate(-2, -2)
        shadow = tuple(max(0, channel - 72) for channel in color)
        highlight = tuple(min(255, channel + 55) for channel in color)
        pygame.draw.rect(self.screen, shadow, tile, border_radius=4)
        face = pygame.Rect(tile.left + 3, tile.top + 3,
                           tile.width - 7, tile.height - 7)
        pygame.draw.rect(self.screen, color, face, border_radius=3)
        pygame.draw.line(self.screen, highlight,
                         (face.left + 2, face.top + 2),
                         (face.right - 3, face.top + 2), 2)
        pygame.draw.line(self.screen, highlight,
                         (face.left + 2, face.top + 2),
                         (face.left + 2, face.bottom - 3), 2)

    def _draw_preview(self, key: str | None, area: pygame.Rect, scale: int) -> None:
        if key is None:
            self._text("—", area.center, self.font_medium, DIM, center=True)
            return
        cells = ROTATIONS[key][0]
        min_row = min(row for row, _ in cells)
        max_row = max(row for row, _ in cells)
        min_col = min(column for _, column in cells)
        max_col = max(column for _, column in cells)
        width = (max_col - min_col + 1) * scale
        height = (max_row - min_row + 1) * scale
        start_x = area.centerx - width / 2
        start_y = area.centery - height / 2
        for row, column in cells:
            rect = pygame.Rect(round(start_x + (column - min_col) * scale),
                               round(start_y + (row - min_row) * scale), scale, scale)
            self._draw_block(rect, COLORS[key])

    def _draw_title(self) -> None:
        for x, y, radius in self.stars:
            pygame.draw.circle(self.screen, (47, 62, 91), (x, y), radius)
        colors = (CYAN, BLUE, MAGENTA, RED, ORANGE, YELLOW)
        title = "TETRIS"
        total_width = sum(self.font_huge.size(letter)[0] for letter in title) + 25
        x = (WINDOW_WIDTH - total_width) / 2
        for index, letter in enumerate(title):
            surface = self.font_huge.render(letter, True, colors[index])
            self.screen.blit(surface, (round(x), 125))
            x += surface.get_width() + 5

        demo = ("T", "I", "S", "Z", "L", "J", "O")
        for index, key in enumerate(demo):
            self._draw_preview(key, pygame.Rect(82 + index * 86, 280, 74, 74), scale=15)

        subtitle = ("STACK • CLEAR • SURVIVE" if self.last_score is None
                    else f"GAME OVER   SCORE {self.last_score:07d}   HIGH {self.high_score:07d}")
        self._text(subtitle, (WINDOW_WIDTH // 2, 430),
                   self.font_medium, WHITE, center=True)
        pulse = 185 + round(70 * (0.5 + 0.5 * math.sin(self.animation_time * 4)))
        self._text("PRESS SPACE OR ENTER TO START", (WINDOW_WIDTH // 2, 500),
                   self.font_medium, (pulse, pulse, 255), center=True)
        self._text("ARROWS/WASD MOVE   Z/X ROTATE   C HOLD",
                   (WINDOW_WIDTH // 2, 585), self.font_small, DIM, center=True)
        self._text("SPACE HARD DROP   P PAUSE", (WINDOW_WIDTH // 2, 618),
                   self.font_small, DIM, center=True)
        self._text("F11 FULLSCREEN     Q OR ESC TO QUIT", (WINDOW_WIDTH // 2, 690),
                   self.font_small, DIM, center=True)

    def _draw_overlay(self) -> None:
        shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 175))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect(170, 290, 420, 180)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, CYAN, panel, width=2, border_radius=12)
        self._text("PAUSED", (WINDOW_WIDTH // 2, 345),
                   self.font_large, WHITE, center=True)
        self._text("P OR SPACE TO CONTINUE", (WINDOW_WIDTH // 2, 420),
                   self.font_small, DIM, center=True)

    def _text(self, text: str, position: tuple[float, float],
              font: pygame.font.Font, color: tuple[int, int, int],
              center: bool = False) -> None:
        surface = font.render(text, True, color)
        if center:
            self.screen.blit(surface, surface.get_rect(
                center=(round(position[0]), round(position[1]))))
        else:
            self.screen.blit(surface, (round(position[0]), round(position[1])))


def main() -> None:
    Tetris().run()


if __name__ == "__main__":
    main()

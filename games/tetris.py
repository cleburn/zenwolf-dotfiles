#!/usr/bin/env python3
"""A full-featured terminal Tetris game."""

import curses
import json
import math
import random
import time
from pathlib import Path

FIELD_HEIGHT = 20
FIELD_WIDTH = 10
CELL_W = 2  # screen columns per tetris cell (terminal cells are ~2:1 tall)

PIECE_KEYS = ["I", "O", "T", "S", "Z", "J", "L"]

PIECES = {
    "I": {"cells": [(1, 0), (1, 1), (1, 2), (1, 3)], "size": 4, "color": curses.COLOR_CYAN},
    "O": {"cells": [(0, 0), (0, 1), (1, 0), (1, 1)], "size": 2, "color": curses.COLOR_YELLOW},
    "T": {"cells": [(0, 1), (1, 0), (1, 1), (1, 2)], "size": 3, "color": curses.COLOR_MAGENTA},
    "S": {"cells": [(0, 1), (0, 2), (1, 0), (1, 1)], "size": 3, "color": curses.COLOR_GREEN},
    "Z": {"cells": [(0, 0), (0, 1), (1, 1), (1, 2)], "size": 3, "color": curses.COLOR_RED},
    "J": {"cells": [(0, 0), (1, 0), (1, 1), (1, 2)], "size": 3, "color": curses.COLOR_BLUE},
    "L": {"cells": [(0, 2), (1, 0), (1, 1), (1, 2)], "size": 3, "color": curses.COLOR_WHITE},
}

LINE_SCORES = [0, 100, 300, 500, 800]
MIN_WIDTH = 46
MIN_HEIGHT = 24
LOCK_DELAY = 0.5
MAX_LOCK_RESETS = 15
GAME_OVER_SECONDS = 3.0
LINE_CLEAR_TIME = 0.2
LEVEL_UP_SECONDS = 0.7
BASE_GRAVITY_INTERVAL = 0.62   # Seconds per gravity step at level 1.
MIN_GRAVITY_INTERVAL = 0.07    # Hard floor on the interval: the game's top speed.
GRAVITY_DECAY = 0.86           # Per-level shrink of the gravity interval.

# First level at which the gravity curve reaches its floor.
SPEED_CAP_LEVEL = math.ceil(math.log(MIN_GRAVITY_INTERVAL / BASE_GRAVITY_INTERVAL)
                            / math.log(GRAVITY_DECAY) + 1)

GAME_ART = (
    " ████   ███  █   █ █████",
    "█      █   █ ██ ██ █    ",
    "█  ██  █████ █ █ █ ████ ",
    "█   █  █   █ █   █ █    ",
    " ████  █   █ █   █ █████",
)
OVER_ART = (
    " ███  █   █ █████ ████ ",
    "█   █ █   █ █     █   █",
    "█   █ █   █ ████  ████ ",
    "█   █  █ █  █     █  █ ",
    " ███    █   █████ █   █",
)

# Shared JSON store so future games can reuse the same file with their own key.
HIGH_SCORE_FILE = Path(__file__).resolve().with_name("game_high_scores.json")
GAME_ID = "terminal tetris"


def load_high_score():
    """Read this game's persistent high score, defaulting to 0."""
    try:
        data = json.loads(HIGH_SCORE_FILE.read_text())
        return max(0, int(data.get(GAME_ID, 0)))
    except (OSError, ValueError, AttributeError):
        return 0


def save_high_score(score):
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


def rotate_cells(cells, size):
    return [(c, size - 1 - r) for (r, c) in cells]


def build_rotations():
    rotations = {}
    for key in PIECE_KEYS:
        cells = PIECES[key]["cells"]
        size = PIECES[key]["size"]
        states = [cells]
        for _ in range(3):
            cells = rotate_cells(cells, size)
            states.append(cells)
        rotations[key] = states
    return rotations


ROTATIONS = build_rotations()
SOLID_PAIRS = {}
TITLE_PAIRS = (8, 9)
GAME_OVER_PAIR = 10
FLASH_PAIR = 11


def drop_interval(level):
    # Smooth exponential curve with a floor, matching the pygame version.
    return max(MIN_GRAVITY_INTERVAL,
               BASE_GRAVITY_INTERVAL * (GRAVITY_DECAY ** (level - 1)))


def speed_multiplier(level):
    """Per-move scoring factor (1.0 at level 1).

    Tracks the true fall speed until gravity reaches its floor, then keeps
    growing linearly with level — continuous at the cap — so per-move
    rewards never plateau while levels keep advancing.
    """
    if level < SPEED_CAP_LEVEL:
        return BASE_GRAVITY_INTERVAL / drop_interval(level)
    top_speed = BASE_GRAVITY_INTERVAL / MIN_GRAVITY_INTERVAL
    return top_speed * level / SPEED_CAP_LEVEL


def drop_points(cells, base_per_cell, level):
    """Points for a soft/hard drop; per-move rewards scale with fall speed."""
    return round(cells * base_per_cell * speed_multiplier(level))


def abs_cells(piece):
    state = ROTATIONS[piece["key"]][piece["rot"]]
    return [(piece["row"] + r, piece["col"] + c) for (r, c) in state]


def fits(grid, cells):
    for (r, c) in cells:
        if r < 0 or r >= FIELD_HEIGHT or c < 0 or c >= FIELD_WIDTH:
            return False
        if grid[r][c] is not None:
            return False
    return True


def new_piece(key):
    size = PIECES[key]["size"]
    col = (FIELD_WIDTH - size) // 2
    return {"key": key, "rot": 0, "row": 0, "col": col}


def try_move(grid, piece, dr, dc):
    cand = dict(piece)
    cand["row"] += dr
    cand["col"] += dc
    return cand if fits(grid, abs_cells(cand)) else None


KICKS = [(0, 0), (0, -1), (0, 1), (0, -2), (0, 2), (-1, 0), (-2, 0)]


def try_rotate(grid, piece, direction=1):
    """Rotate in either direction, trying simple wall/floor kicks."""
    new_rot = (piece["rot"] + direction) % 4
    for (dr, dc) in KICKS:
        cand = dict(piece)
        cand["rot"] = new_rot
        cand["row"] += dr
        cand["col"] += dc
        if fits(grid, abs_cells(cand)):
            return cand
    return None


def clear_lines(grid):
    kept = [row for row in grid if any(cell is None for cell in row)]
    cleared = FIELD_HEIGHT - len(kept)
    while len(kept) < FIELD_HEIGHT:
        kept.insert(0, [None] * FIELD_WIDTH)
    return cleared, kept


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    for idx, key in enumerate(PIECE_KEYS, start=1):
        # A colored background keeps every cell solid; black foreground glyphs
        # supply the fine inset edges between neighboring cells.
        color = PIECES[key]["color"]
        if key == "L" and curses.COLORS >= 256:
            color = 208  # Real orange where the terminal supports it.
        curses.init_pair(idx, curses.COLOR_BLACK, color)
        SOLID_PAIRS[key] = idx
    curses.init_pair(TITLE_PAIRS[0], curses.COLOR_CYAN, -1)
    curses.init_pair(TITLE_PAIRS[1], curses.COLOR_MAGENTA, -1)
    curses.init_pair(GAME_OVER_PAIR, curses.COLOR_RED, -1)
    curses.init_pair(FLASH_PAIR, curses.COLOR_BLACK, curses.COLOR_WHITE)
    SOLID_PAIRS["_flash"] = FLASH_PAIR  # Blink style for clearing rows.


def safe_addstr(stdscr, y, x, s, attr=0):
    if y < 0 or x < 0:
        return
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass


def safe_addch(stdscr, y, x, ch, attr=0):
    if y < 0 or x < 0:
        return
    try:
        stdscr.addch(y, x, ch, attr)
    except curses.error:
        pass


def draw_box(stdscr, y, x, h, w):
    safe_addch(stdscr, y, x, curses.ACS_ULCORNER)
    safe_addch(stdscr, y, x + w - 1, curses.ACS_URCORNER)
    safe_addch(stdscr, y + h - 1, x, curses.ACS_LLCORNER)
    safe_addch(stdscr, y + h - 1, x + w - 1, curses.ACS_LRCORNER)
    for cx in range(x + 1, x + w - 1):
        safe_addch(stdscr, y, cx, curses.ACS_HLINE)
        safe_addch(stdscr, y + h - 1, cx, curses.ACS_HLINE)
    for ry in range(y + 1, y + h - 1):
        safe_addch(stdscr, ry, x, curses.ACS_VLINE)
        safe_addch(stdscr, ry, x + w - 1, curses.ACS_VLINE)


def draw_block(stdscr, y, x, key, has_colors, cell_rows, cell_cols):
    """Draw a solid tile with fine dark bottom/right separation lines."""
    attr = curses.color_pair(SOLID_PAIRS[key]) if has_colors else curses.A_REVERSE
    if cell_rows == 1:
        # Underlining supplies the bottom edge while the final eighth-block
        # makes a narrow right edge, leaving nearly all of the tile color-filled.
        safe_addstr(stdscr, y, x, " " * (cell_cols - 1) + "▕",
                    attr | curses.A_UNDERLINE)
        return

    edge_row = " " * (cell_cols - 1) + "▕"
    for dr in range(cell_rows - 1):
        safe_addstr(stdscr, y + dr, x, edge_row, attr)
    safe_addstr(stdscr, y + cell_rows - 1, x, edge_row,
                attr | curses.A_UNDERLINE)


def compute_scale(height, width):
    # Grow the block size as far as the terminal allows instead of capping it;
    # the fixed 2:1 cell ratio keeps the board's proportions at every scale.
    scale = 1
    while (FIELD_HEIGHT * (scale + 1) + 4 <= height
           and FIELD_WIDTH * CELL_W * (scale + 1) + 26 <= width):
        scale += 1
    return scale


def compute_layout(height, width):
    scale = compute_scale(height, width)
    cell_cols = CELL_W * scale
    cell_rows = scale
    field_w = FIELD_WIDTH * cell_cols + 2
    field_h = FIELD_HEIGHT * cell_rows + 2
    panel_w = max(22, min(30, width - field_w - 2))
    content_w = field_w + 2 + panel_w
    content_h = field_h
    left = max(0, (width - content_w) // 2)
    top = max(0, (height - content_h) // 2)
    fy, fx = top, left
    py, px = top, left + field_w + 2
    return fy, fx, py, px, scale, panel_w, cell_cols, cell_rows


def draw_preview(stdscr, key, top, left, width, has_colors, cell_cols, cell_rows):
    if key is None:
        safe_addstr(stdscr, top + 1, left + max(0, width // 2 - 1), "--", curses.A_DIM)
        return
    cells = ROTATIONS[key][0]
    rs = [r for (r, c) in cells]
    cs = [c for (r, c) in cells]
    minr, minc = min(rs), min(cs)
    piece_w = (max(cs) - minc + 1) * cell_cols
    preview_left = left + max(0, (width - piece_w) // 2)
    for (r, c) in cells:
        draw_block(stdscr, top + (r - minr) * cell_rows,
                   preview_left + (c - minc) * cell_cols,
                   key, has_colors, cell_rows, cell_cols)


def draw_panel(stdscr, py, px, panel_w, next_keys, held_key, score, high_score,
               level, lines, has_colors, cell_cols, cell_rows):
    inside_w = panel_w - 2
    safe_addstr(stdscr, py, px + 2, " INFO ", curses.A_BOLD)
    safe_addstr(stdscr, py + 1, px + 2, "NEXT", curses.A_BOLD)

    stride = 2 * cell_rows + 1
    shown = min(len(next_keys), 3 if cell_rows >= 2 else 1)
    for index in range(shown):
        draw_preview(stdscr, next_keys[index], py + 2 + index * stride, px + 1,
                     inside_w, has_colors, cell_cols, cell_rows)

    hold_label = py + 3 + shown * stride
    safe_addstr(stdscr, hold_label, px + 2, "HOLD", curses.A_BOLD)
    draw_preview(stdscr, held_key, hold_label + 1, px + 1, inside_w,
                 has_colors, cell_cols, cell_rows)

    row = hold_label + 1 + 4 * cell_rows
    safe_addstr(stdscr, row, px + 2, f"SCORE  {score}"); row += 1
    safe_addstr(stdscr, row, px + 2, f"BEST   {high_score}"); row += 1
    safe_addstr(stdscr, row, px + 2, f"LEVEL  {level}"); row += 1
    safe_addstr(stdscr, row, px + 2, f"LINES  {lines}"); row += 2
    safe_addstr(stdscr, row, px + 2, "CONTROLS", curses.A_BOLD); row += 1
    for line in ["L/R move  Up/X turn", "Z counter-rotate", "Dn soft  Spc drop", "C hold   P pause"]:
        safe_addstr(stdscr, row, px + 2, line); row += 1


def center_message(stdscr, lines):
    height, width = stdscr.getmaxyx()
    start_y = max(0, height // 2 - len(lines) // 2)
    for offset, line in enumerate(lines):
        x = max(0, width // 2 - len(line) // 2)
        safe_addstr(stdscr, start_y + offset, x, line[: max(0, width - x)], curses.A_BOLD)


def draw(stdscr, grid, piece, next_keys, held_key, score, high_score, level,
         lines, paused, game_over, has_colors, particles=None):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    fy, fx, py, px, scale, panel_w, cell_cols, cell_rows = compute_layout(height, width)
    field_w = FIELD_WIDTH * cell_cols + 2
    field_h = FIELD_HEIGHT * cell_rows + 2

    draw_box(stdscr, fy, fx, field_h, field_w)
    safe_addstr(stdscr, fy, fx + 2, " TETRIS ", curses.A_BOLD)
    draw_box(stdscr, py, px, field_h, panel_w)

    for r in range(FIELD_HEIGHT):
        for c in range(FIELD_WIDTH):
            key = grid[r][c]
            if key:
                draw_block(stdscr, fy + 1 + r * cell_rows, fx + 1 + c * cell_cols, key, has_colors, cell_rows, cell_cols)

    if piece and not game_over:
        for (r, c) in abs_cells(piece):
            draw_block(stdscr, fy + 1 + r * cell_rows, fx + 1 + c * cell_cols, piece["key"], has_colors, cell_rows, cell_cols)

    draw_panel(stdscr, py, px, panel_w, next_keys, held_key, score, high_score,
               level, lines, has_colors, cell_cols, cell_rows)

    if paused:
        center_message(stdscr, ["PAUSED", "Press P to resume"])
    if particles:
        for p in particles:
            draw_particle(stdscr, p, has_colors)

    stdscr.refresh()


def game_over_animation(stdscr, grid, next_keys, held_key, score, high_score,
                        level, lines, has_colors, duration=GAME_OVER_SECONDS):
    """Animate large block lettering over the frozen final board."""
    started = time.monotonic()
    art = GAME_ART + ("",) + OVER_ART
    max_width = max(len(line) for line in art)
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= duration:
            break
        draw(stdscr, grid, None, next_keys, held_key, score, high_score, level,
             lines, False, False, has_colors)
        height, width = stdscr.getmaxyx()
        top = max(1, (height - len(art) - 2) // 2)
        left = max(1, (width - max_width - 4) // 2)
        box_width = min(width - left - 1, max_width + 4)
        for row in range(len(art) + 2):
            safe_addstr(stdscr, top + row, left, " " * box_width)

        reveal = min(1.0, elapsed / 0.85)
        visible = math.ceil(max_width * reveal)
        attr = curses.A_BOLD
        if has_colors:
            attr |= curses.color_pair(GAME_OVER_PAIR)
        for offset, line in enumerate(art):
            safe_addstr(stdscr, top + 1 + offset,
                        max(left + 2, (width - len(line)) // 2),
                        line[:visible], attr)
        if elapsed > duration - 0.75:
            safe_addstr(stdscr, min(height - 2, top + len(art) + 1),
                        max(0, (width - 19) // 2), "RETURNING TO TITLE…",
                        curses.A_BOLD)
        stdscr.refresh()
        key = stdscr.getch()
        while key != -1:
            key = stdscr.getch()
        time.sleep(1 / 30)


def draw_particle(stdscr, p, has_colors):
    y, x = int(p["y"]), int(p["x"])
    if y < 0 or x < 0:
        return
    if has_colors:
        attr = curses.color_pair(SOLID_PAIRS[p["key"]])
    else:
        attr = curses.A_BOLD
    if p["life"] < 0.3 * p["max"]:
        attr |= curses.A_DIM
    safe_addstr(stdscr, y, x, p["char"], attr)


def celebrate(stdscr, grid, debris, has_colors, next_keys, held_piece, score, high_score, level, lines):
    height, width = stdscr.getmaxyx()
    fy, fx, py, px, scale, panel_w, cell_cols, cell_rows = compute_layout(height, width)

    particles = []
    for (r, c, key) in debris:
        cx = fx + 1 + c * cell_cols + cell_cols / 2.0
        cy = fy + 1 + r * cell_rows + cell_rows / 2.0
        for _ in range(2):
            ang = random.uniform(math.pi, 2 * math.pi)
            spd = random.uniform(12, 24)
            particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * spd, "vy": math.sin(ang) * spd,
                "key": key, "life": random.uniform(0.9, 1.4), "max": 1.4, "char": "\u2588",
            })

    bursts = sorted(
        (random.uniform(0.0, 1.0),
         fx + 1 + random.uniform(0, FIELD_WIDTH * cell_cols),
         fy + 1 + random.uniform(0, FIELD_HEIGHT * cell_rows * 0.6))
        for _ in range(5)
    )

    duration = 1.8
    start = time.time()
    last = start
    bidx = 0
    gravity = 32.0
    while True:
        now = time.time()
        elapsed = now - start
        if elapsed >= duration:
            break
        dt = min(now - last, 0.05)
        last = now

        while bidx < len(bursts) and elapsed >= bursts[bidx][0]:
            _, bx, by = bursts[bidx]
            bkey = random.choice(PIECE_KEYS)
            for _ in range(26):
                ang = random.uniform(0, 2 * math.pi)
                spd = random.uniform(6, 16)
                particles.append({
                    "x": bx, "y": by,
                    "vx": math.cos(ang) * spd, "vy": math.sin(ang) * spd,
                    "key": bkey, "life": random.uniform(0.6, 1.0), "max": 1.0, "char": "*",
                })
            bidx += 1

        for p in particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += gravity * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

        k = stdscr.getch()
        while k != -1:
            k = stdscr.getch()

        draw(stdscr, grid, None, next_keys, held_piece, score, high_score,
             level, lines, False, False, has_colors, particles)
        time.sleep(0.03)


def flash_line_clear(stdscr, grid, rows, has_colors, next_keys, held_key,
                     score, high_score, level, lines):
    """Blink completed rows white briefly before they collapse."""
    started = time.monotonic()
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= LINE_CLEAR_TIME:
            break
        draw(stdscr, grid, None, next_keys, held_key, score, high_score,
             level, lines, False, False, has_colors)
        if int(elapsed * 10) % 2 == 0:
            height, width = stdscr.getmaxyx()
            fy, fx, py, px, scale, panel_w, cell_cols, cell_rows = compute_layout(height, width)
            for r in rows:
                for c in range(FIELD_WIDTH):
                    draw_block(stdscr, fy + 1 + r * cell_rows, fx + 1 + c * cell_cols,
                               "_flash", has_colors, cell_rows, cell_cols)
        stdscr.refresh()
        key = stdscr.getch()
        while key != -1:
            key = stdscr.getch()
        time.sleep(1 / 60)


def level_up_banner(stdscr, grid, has_colors, next_keys, held_key,
                    score, high_score, level, lines):
    """Announce a new level with a brief pause over the refreshed board."""
    curses.beep()
    started = time.monotonic()
    while time.monotonic() - started < LEVEL_UP_SECONDS:
        draw(stdscr, grid, None, next_keys, held_key, score, high_score,
             level, lines, False, False, has_colors)
        center_message(stdscr, [f"LEVEL {level}"])
        stdscr.refresh()
        key = stdscr.getch()
        while key != -1:
            key = stdscr.getch()
        time.sleep(1 / 60)


def title_screen(stdscr, last_score=None, high_score=0):
    """Show a responsive title screen. Return False when the user quits."""
    title = [
        "████████╗███████╗████████╗██████╗ ██╗███████╗",
        "╚══██╔══╝██╔════╝╚══██╔══╝██╔══██╗██║██╔════╝",
        "   ██║   █████╗     ██║   ██████╔╝██║███████╗",
        "   ██║   ██╔══╝     ██║   ██╔══██╗██║╚════██║",
        "   ██║   ███████╗   ██║   ██║  ██║██║███████║",
        "   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚══════╝",
    ]
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            center_message(stdscr, ["Terminal is too small.",
                           f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}.", "Q to quit"])
        else:
            top = max(2, height // 2 - 7)
            for i, line in enumerate(title):
                attr = curses.A_BOLD
                if curses.has_colors():
                    attr |= curses.color_pair(TITLE_PAIRS[i % len(TITLE_PAIRS)])
                safe_addstr(stdscr, top + i, max(0, (width - len(line)) // 2),
                            line, attr)
            subtitle = ("STACK • CLEAR • SURVIVE" if last_score is None
                        else f"GAME OVER  •  SCORE {last_score}  •  BEST {high_score}")
            center_message(stdscr, ["", "", "", "", "", "", "", "",
                           subtitle,
                           "Press SPACE or ENTER to start",
                           "Arrows/WASD move • Z/X rotate • C hold • Q quit"])
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            return False
        if (height >= MIN_HEIGHT and width >= MIN_WIDTH
                and key in (ord(" "), 10, 13, curses.KEY_ENTER)):
            return True
        time.sleep(0.02)


def game(stdscr, show_title=True):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    has_colors = curses.has_colors()
    if has_colors:
        init_colors()

    high_score = load_high_score()
    if show_title and not title_screen(stdscr, high_score=high_score):
        return

    grid = [[None] * FIELD_WIDTH for _ in range(FIELD_HEIGHT)]
    score = 0
    lines = 0
    level = 1
    bag = []

    def next_key():
        nonlocal bag
        if not bag:
            bag = PIECE_KEYS[:]
            random.shuffle(bag)
        return bag.pop()

    def advance_piece():
        nonlocal cur
        cur = new_piece(queue.pop(0))
        queue.append(next_key())

    queue = [next_key() for _ in range(4)]
    cur = new_piece(queue.pop(0))
    held = None
    can_hold = True
    paused = False
    game_over = False
    last_drop = time.monotonic()
    grounded_since = None
    lock_resets = 0

    def do_lock():
        nonlocal cur, score, lines, level, game_over, last_drop
        nonlocal grounded_since, lock_resets, can_hold, high_score
        for (r, c) in abs_cells(cur):
            if 0 <= r < FIELD_HEIGHT and 0 <= c < FIELD_WIDTH:
                grid[r][c] = cur["key"]
        full_rows = [r for r in range(FIELD_HEIGHT) if all(grid[r][c] is not None for c in range(FIELD_WIDTH))]
        cleared = len(full_rows)
        leveled_up = False
        if cleared:
            score += LINE_SCORES[cleared] * level
            lines += cleared
            leveled_up = lines // 10 + 1 > level
            level = lines // 10 + 1
            if score > high_score:
                high_score = score
                save_high_score(high_score)
            flash_line_clear(stdscr, grid, full_rows, has_colors, queue, held,
                             score, high_score, level, lines)
        if cleared == 4:
            debris = [(r, c, grid[r][c]) for r in full_rows for c in range(FIELD_WIDTH)]
            _, compacted = clear_lines(grid)
            grid[:] = compacted
            celebrate(stdscr, grid, debris, has_colors, queue, held, score, high_score, level, lines)
        else:
            _, compacted = clear_lines(grid)
            grid[:] = compacted
        if leveled_up:
            level_up_banner(stdscr, grid, has_colors, queue, held,
                            score, high_score, level, lines)
        advance_piece()
        last_drop = time.monotonic()
        grounded_since = None
        lock_resets = 0
        can_hold = True
        if not fits(grid, abs_cells(cur)):
            game_over = True

    def after_player_move():
        """Apply a bounded lock-delay reset after movement or rotation."""
        nonlocal grounded_since, lock_resets
        if try_move(grid, cur, 1, 0):
            grounded_since = None
        elif lock_resets < MAX_LOCK_RESETS:
            grounded_since = time.monotonic()
            lock_resets += 1

    while not game_over:
        height, width = stdscr.getmaxyx()
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            stdscr.erase()
            center_message(stdscr, ["PAUSED — TERMINAL TOO SMALL",
                           f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}.", "Q to quit"])
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                return
            last_drop = time.monotonic()
            grounded_since = None
            time.sleep(0.03)
            continue

        key = stdscr.getch()
        while key != -1:
            if key in (ord("q"), ord("Q"), 27):
                return
            if key in (ord("p"), ord("P")):
                paused = not paused
                last_drop = time.monotonic()
                grounded_since = None
            elif not paused:
                if key in (curses.KEY_LEFT, ord("a"), ord("A")):
                    m = try_move(grid, cur, 0, -1)
                    if m:
                        cur = m
                        after_player_move()
                elif key in (curses.KEY_RIGHT, ord("d"), ord("D")):
                    m = try_move(grid, cur, 0, 1)
                    if m:
                        cur = m
                        after_player_move()
                elif key in (curses.KEY_DOWN, ord("s"), ord("S")):
                    m = try_move(grid, cur, 1, 0)
                    if m:
                        cur = m
                        score += drop_points(1, 1, level)
                        last_drop = time.monotonic()
                        grounded_since = None
                    else:
                        if grounded_since is None:
                            grounded_since = time.monotonic()
                elif key in (curses.KEY_UP, ord("w"), ord("W"), ord("x"), ord("X")):
                    m = try_rotate(grid, cur, 1)
                    if m:
                        cur = m
                        after_player_move()
                elif key in (ord("z"), ord("Z")):
                    m = try_rotate(grid, cur, -1)
                    if m:
                        cur = m
                        after_player_move()
                elif key == ord(" "):
                    dropped = 0
                    while True:
                        m = try_move(grid, cur, 1, 0)
                        if not m:
                            break
                        cur = m
                        dropped += 1
                    score += drop_points(dropped, 2, level)
                    do_lock()
                elif key in (ord("c"), ord("C")) and can_hold:
                    old_key = cur["key"]
                    if held is None:
                        held = old_key
                        advance_piece()
                    else:
                        cur = new_piece(held)
                        held = old_key
                    can_hold = False
                    grounded_since = None
                    lock_resets = 0
                    last_drop = time.monotonic()
                    if not fits(grid, abs_cells(cur)):
                        game_over = True
            key = stdscr.getch()

        if not paused:
            now = time.monotonic()
            interval = drop_interval(level)
            if now - last_drop >= interval:
                m = try_move(grid, cur, 1, 0)
                if m:
                    cur = m
                    grounded_since = None
                else:
                    if grounded_since is None:
                        grounded_since = now
                # Keep the leftover fraction of the interval so the fall pace
                # stays exact; clamp so a stalled frame can't queue extra drops.
                last_drop = max(last_drop + interval, now - interval)
            if grounded_since is not None and now - grounded_since >= LOCK_DELAY:
                do_lock()

        draw(stdscr, grid, cur, queue, held, score, high_score, level, lines, paused, game_over, has_colors)
        time.sleep(0.015)

    # Return automatically to the same startup screen. One SPACE/ENTER begins
    # the next game; Q or Escape exits from there.
    if score > high_score:
        high_score = score
        save_high_score(high_score)
    game_over_animation(stdscr, grid, queue, held, score, high_score, level, lines, has_colors)
    if title_screen(stdscr, score, high_score):
        game(stdscr, show_title=False)


def main():
    curses.wrapper(game)


if __name__ == "__main__":
    main()

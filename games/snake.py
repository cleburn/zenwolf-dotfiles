#!/usr/bin/env python3
"""A polished, dependency-free terminal Snake game."""

from __future__ import annotations

import curses
import json
import math
import random
import time
from collections import deque
from pathlib import Path


CELL_WIDTH = 2  # Terminal characters are about twice as tall as they are wide.
START_LENGTH = 5
MIN_WIDTH = 44
MIN_HEIGHT = 16
MAX_BOARD_WIDTH = 36
MAX_BOARD_HEIGHT = 22
START_TICK = 0.205
MIN_TICK = 0.065
SCORE_PER_LEVEL = 50
TICK_DECREASE_PER_LEVEL = 0.015

SNAKE_PAIR = 1
HEAD_PAIR = 2
FOOD_PAIR = 3
BORDER_PAIR = 4
GAME_OVER_SECONDS = 3.0

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

UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

# Shared JSON store so future games can reuse the same file with their own key.
HIGH_SCORE_FILE = Path(__file__).resolve().with_name("game_high_scores.json")
GAME_ID = "snake"


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


def safe_addstr(screen, y, x, text, attr=0):
    height, width = screen.getmaxyx()
    if y < 0 or y >= height or x >= width - 1:
        return
    if x < 0:
        text, x = text[-x:], 0
    try:
        screen.addstr(y, x, text[:max(0, width - x - 1)], attr)
    except curses.error:
        pass


def center_text(screen, y, text, attr=0):
    _, width = screen.getmaxyx()
    safe_addstr(screen, y, max(0, (width - len(text)) // 2), text, attr)


def center_message(screen, lines, attr=curses.A_BOLD):
    height, _ = screen.getmaxyx()
    start_y = max(0, height // 2 - len(lines) // 2)
    for offset, line in enumerate(lines):
        center_text(screen, start_y + offset, line, attr)


def board_size(height, width):
    """Return board dimensions in square-ish logical cells."""
    logical_width = min(MAX_BOARD_WIDTH, (width - 2) // CELL_WIDTH)
    logical_height = min(MAX_BOARD_HEIGHT, height - 2)
    return logical_height, logical_width


def board_origin(screen_height, screen_width, board_height, board_width):
    rendered_width = board_width * CELL_WIDTH + 2
    rendered_height = board_height + 2
    return ((screen_height - rendered_height) // 2,
            (screen_width - rendered_width) // 2)


def place_food(snake, height, width, rng=None):
    """Choose an unoccupied logical cell, or None when the board is full."""
    rng = rng or random
    occupied = set(snake)
    empty = [(y, x) for y in range(height) for x in range(width)
             if (y, x) not in occupied]
    return rng.choice(empty) if empty else None


# Keep the old public name for anyone importing this small game as a module.
place_dot = place_food


def tick_seconds(score):
    """Reduce the movement interval once per displayed level."""
    completed_levels = score // SCORE_PER_LEVEL
    return max(MIN_TICK,
               START_TICK - completed_levels * TICK_DECREASE_PER_LEVEL)


def next_head(head, direction, height, width):
    """Move one logical cell with wraparound at board edges."""
    return ((head[0] + direction[0]) % height,
            (head[1] + direction[1]) % width)


def init_colors():
    if not curses.has_colors():
        return False
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(SNAKE_PAIR, curses.COLOR_GREEN, -1)
        curses.init_pair(HEAD_PAIR, curses.COLOR_CYAN, -1)
        curses.init_pair(FOOD_PAIR, curses.COLOR_RED, -1)
        curses.init_pair(BORDER_PAIR, curses.COLOR_GREEN, -1)
        return True
    except curses.error:
        return False


def draw_border(screen, top, left, board_height, board_width, has_colors):
    width = board_width * CELL_WIDTH + 2
    attr = curses.color_pair(BORDER_PAIR) if has_colors else curses.A_NORMAL
    safe_addstr(screen, top, left, "┌" + "─" * (width - 2) + "┐", attr)
    for y in range(board_height):
        safe_addstr(screen, top + y + 1, left, "│", attr)
        safe_addstr(screen, top + y + 1, left + width - 1, "│", attr)
    safe_addstr(screen, top + board_height + 1, left,
                "└" + "─" * (width - 2) + "┘", attr)


def draw(screen, snake, food, score, high_score, board_height, board_width,
         direction, has_colors, paused=False, game_over=False, won=False):
    """Render logical cells as two-column blocks with a 1:1 visual aspect."""
    screen.erase()
    height, width = screen.getmaxyx()
    top, left = board_origin(height, width, board_height, board_width)
    draw_border(screen, top, left, board_height, board_width, has_colors)

    level = 1 + score // SCORE_PER_LEVEL
    rendered_width = board_width * CELL_WIDTH + 2
    if rendered_width >= 66:
        status = f" SCORE {score:04d}  BEST {high_score:04d}  LEVEL {level} "
    else:
        status = f" SCORE {score:04d}  LEVEL {level} "
    safe_addstr(screen, top, left + 2, status, curses.A_BOLD)
    hint = " P PAUSE  Q QUIT "
    if rendered_width - len(status) >= len(hint) + 4:
        safe_addstr(screen, top, left + rendered_width - 1 - len(hint), hint, curses.A_DIM)

    if food is not None:
        fy, fx = food
        food_attr = curses.color_pair(FOOD_PAIR) | curses.A_BOLD if has_colors else curses.A_BOLD
        safe_addstr(screen, top + 1 + fy, left + 1 + fx * CELL_WIDTH, "● ", food_attr)

    body_attr = curses.color_pair(SNAKE_PAIR) | curses.A_BOLD if has_colors else curses.A_BOLD
    head_attr = curses.color_pair(HEAD_PAIR) | curses.A_BOLD if has_colors else curses.A_REVERSE
    for index in range(len(snake) - 1, -1, -1):
        y, x = snake[index]
        text = "██" if index == 0 else "▓▓"
        attr = head_attr if index == 0 else body_attr
        safe_addstr(screen, top + 1 + y, left + 1 + x * CELL_WIDTH, text, attr)

    if paused:
        draw_overlay(screen, "PAUSED", "P or SPACE to continue")
    elif game_over:
        title = "YOU FILLED THE BOARD!" if won else "GAME OVER"
        draw_overlay(screen, title, f"Score {score}  •  R title menu  •  Q quit")

    screen.refresh()


def draw_overlay(screen, title, subtitle):
    height, width = screen.getmaxyx()
    box_width = min(width - 4, max(len(title), len(subtitle)) + 6)
    left = max(1, (width - box_width) // 2)
    top = height // 2 - 2
    safe_addstr(screen, top, left, "╔" + "═" * (box_width - 2) + "╗", curses.A_BOLD)
    for row in range(1, 4):
        safe_addstr(screen, top + row, left, "║" + " " * (box_width - 2) + "║",
                    curses.A_BOLD)
    safe_addstr(screen, top + 4, left, "╚" + "═" * (box_width - 2) + "╝", curses.A_BOLD)
    center_text(screen, top + 1, title, curses.A_BOLD)
    center_text(screen, top + 3, subtitle)


def game_over_animation(screen, snake, food, score, high_score,
                        board_height, board_width, direction, has_colors,
                        duration=GAME_OVER_SECONDS):
    """Animate a large block-letter overlay over the frozen final board."""
    started = time.monotonic()
    art = GAME_ART + ("",) + OVER_ART
    max_width = max(len(line) for line in art)
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= duration:
            break
        draw(screen, snake, food, score, high_score, board_height, board_width,
             direction, has_colors)
        height, width = screen.getmaxyx()
        top = max(1, (height - len(art) - 2) // 2)
        left = max(1, (width - max_width - 4) // 2)
        box_width = min(width - left - 1, max_width + 4)
        for row in range(len(art) + 2):
            safe_addstr(screen, top + row, left, " " * box_width)

        reveal = min(1.0, elapsed / 0.85)
        visible = math.ceil(max_width * reveal)
        attr = curses.A_BOLD
        if has_colors:
            attr |= curses.color_pair(FOOD_PAIR)
        for offset, line in enumerate(art):
            text = line[:visible]
            safe_addstr(screen, top + 1 + offset,
                        max(left + 2, (width - len(line)) // 2), text, attr)
        if elapsed > duration - 0.75:
            center_text(screen, min(height - 2, top + len(art) + 1),
                        "RETURNING TO TITLE…", curses.A_BOLD)
        screen.refresh()
        key = screen.getch()
        while key != -1:
            key = screen.getch()
        time.sleep(1 / 30)


def title_screen(screen, has_colors, last_score=None):
    art = (
        "███████╗███╗   ██╗ █████╗ ██╗  ██╗███████╗",
        "██╔════╝████╗  ██║██╔══██╗██║ ██╔╝██╔════╝",
        "███████╗██╔██╗ ██║███████║█████╔╝ █████╗  ",
        "╚════██║██║╚██╗██║██╔══██║██╔═██╗ ██╔══╝  ",
        "███████║██║ ╚████║██║  ██║██║  ██╗███████╗",
        "╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝",
    )
    color = curses.color_pair(SNAKE_PAIR) if has_colors else curses.A_NORMAL
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            center_message(screen, ["Terminal is too small",
                           f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}", "Q to quit"])
        else:
            top = max(2, height // 2 - 7)
            if width >= 51:
                for offset, line in enumerate(art):
                    center_text(screen, top + offset, line, color | curses.A_BOLD)
            else:
                center_text(screen, top + 2, "S N A K E", color | curses.A_BOLD)
            if last_score is None:
                subtitle = "GROW • WRAP • DON'T BITE YOUR TAIL"
            else:
                subtitle = f"GAME OVER  •  SCORE {last_score}"
            center_text(screen, top + 8, subtitle, curses.A_BOLD)
            center_text(screen, top + 10, "Press SPACE or ENTER to start",
                        curses.A_REVERSE | curses.A_BOLD)
            center_text(screen, top + 12, "Arrows/WASD move  •  P pause  •  Q quit", curses.A_DIM)
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), ord("Q"), 27):
            return False
        if (height >= MIN_HEIGHT and width >= MIN_WIDTH
                and key in (ord(" "), 10, 13, curses.KEY_ENTER)):
            return True
        time.sleep(0.02)


def play_round(screen, high_score, has_colors):
    screen_height, screen_width = screen.getmaxyx()
    board_height, board_width = board_size(screen_height, screen_width)
    start_y = board_height // 2
    start_x = board_width // 2
    snake = deque((start_y, start_x - i) for i in range(START_LENGTH))
    direction = RIGHT
    turn_queue = deque(maxlen=2)
    food = place_food(snake, board_height, board_width)
    score = 0
    paused = False
    won = False
    next_tick = time.monotonic() + tick_seconds(score)

    turns = {
        curses.KEY_UP: UP, curses.KEY_DOWN: DOWN,
        curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT,
        ord("w"): UP, ord("W"): UP, ord("s"): DOWN, ord("S"): DOWN,
        ord("a"): LEFT, ord("A"): LEFT, ord("d"): RIGHT, ord("D"): RIGHT,
    }

    while True:
        height, width = screen.getmaxyx()
        required_height = board_height + 2
        required_width = board_width * CELL_WIDTH + 2
        if height < required_height or width < required_width:
            screen.erase()
            center_message(screen, ["PAUSED — TERMINAL TOO SMALL",
                           f"Resize to at least {required_width}x{required_height}", "Q to quit"])
            screen.refresh()
            key = screen.getch()
            if key in (ord("q"), ord("Q"), 27):
                return high_score, None
            next_tick = time.monotonic() + tick_seconds(score)
            time.sleep(0.03)
            continue

        key = screen.getch()
        while key != -1:
            if key in (ord("q"), ord("Q"), 27):
                return high_score, None
            if key in (ord("p"), ord("P"), ord(" ")):
                paused = not paused
                next_tick = time.monotonic() + tick_seconds(score)
            elif not paused and key in turns:
                candidate = turns[key]
                base = turn_queue[-1] if turn_queue else direction
                if candidate != (-base[0], -base[1]) and candidate != base:
                    turn_queue.append(candidate)
            key = screen.getch()

        if paused:
            draw(screen, snake, food, score, high_score, board_height, board_width,
                 direction, has_colors, paused=True)
            time.sleep(1 / 60)
            continue

        now = time.monotonic()
        if now >= next_tick:
            if turn_queue:
                direction = turn_queue.popleft()
            new_head = next_head(snake[0], direction, board_height, board_width)
            grows = new_head == food
            body_to_check = snake if grows else list(snake)[:-1]
            if new_head in body_to_check:
                break

            snake.appendleft(new_head)
            if grows:
                score += 10
                high_score = max(high_score, score)
                food = place_food(snake, board_height, board_width)
                if food is None:
                    won = True
                    break
            else:
                snake.pop()
            next_tick = now + tick_seconds(score)

        draw(screen, snake, food, score, high_score, board_height, board_width,
             direction, has_colors)
        time.sleep(1 / 120)

    high_score = max(high_score, score)
    game_over_animation(screen, snake, food, score, high_score,
                        board_height, board_width, direction, has_colors)
    return high_score, score


def game(screen):
    curses.curs_set(0)
    screen.nodelay(True)
    screen.keypad(True)
    has_colors = init_colors()
    high_score = load_high_score()
    last_score = None
    while True:
        if not title_screen(screen, has_colors, last_score):
            return
        high_score, result = play_round(screen, high_score, has_colors)
        save_high_score(high_score)
        if result is None:
            return
        last_score = result


def main():
    try:
        curses.wrapper(game)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

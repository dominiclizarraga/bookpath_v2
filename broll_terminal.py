"""Temporary terminal animation for filming B-roll."""

import math
import random
import shutil
import string
import sys
import time


DURATION_SECONDS = 18
FRAME_DELAY_SECONDS = 0.054
CHARACTERS = string.ascii_letters + string.digits + "<>[]{}/*-=+_"
GREEN_PROBABILITY = 0.05
STATIONS = ("東京", "新横浜", "名古屋", "京都", "新大阪")


def joke_frame(elapsed: float, width: int, height: int) -> list[str] | None:
    """Pause the noise long enough for viewers to read the joke."""
    if 5 <= elapsed < 8:
        message = [
            "[ MOUNT FUJI DETECTED ]",
            "",
            "       /\\       ",
            "      /  \\      ",
            "     /____\\     ",
            "",
            "EVERYONE LOOK OUT THE WINDOW",
        ]
    elif 8 <= elapsed < 13:
        message = [
            "[ CORRECTION ]",
            "",
            "       /\\       ",
            "      /  \\      ",
            "     / ## \\     ",
            "    /__##__\\    ",
            "",
            "FALSE ALARM: THAT WAS AN ONIGIRI",
            "",
            "Please stop pointing the laptop at your lunch.",
        ]
    elif 15 <= elapsed < 18:
        message = [
            "[ SYSTEM STATUS ]",
            "",
            "TRAIN:  300 km/h",
            "CODE:   0 lines/h",
            "",
            "Productivity is a matter of perspective.",
        ]
    else:
        return None

    message = message[:height]
    top_padding = (height - len(message)) // 2
    lines = [""] * top_padding + message
    lines += [""] * (height - len(lines))
    return ["\033[39m" + line[:width].center(width) for line in lines]


def random_line(
    width: int,
    train_column: int | None = None,
    station: str = "",
) -> str:
    """Build a random line with sparse green characters."""
    characters = random.choices(CHARACTERS + " " * 5, k=width)
    if train_column is not None:
        marker = f"🚅{station}"
        characters[train_column : train_column + len(marker)] = marker

    return "".join(
        f"\033[38;5;46m{character}\033[39m"
        if character not in (" ", "🚅") and random.random() < GREEN_PROBABILITY
        else character
        for character in characters
    )


def main() -> None:
    """Animate random characters until the recording window ends."""
    deadline = time.monotonic() + DURATION_SECONDS
    sys.stdout.write("\033[0m\033[40m\033[2J\033[H\033[?25l")

    try:
        while time.monotonic() < deadline:
            columns, rows = shutil.get_terminal_size((100, 30))
            columns = max(1, columns - 1)
            visible_rows = max(1, rows - 1)
            elapsed = DURATION_SECONDS - (deadline - time.monotonic())
            hop = elapsed / 0.75
            hop_number = int(hop)
            hop_height = math.sin((hop % 1) * math.pi)
            train_row = (hop_number - round(hop_height)) % visible_rows
            station = STATIONS[hop_number % len(STATIONS)]
            train_column = int((hop * 8) % max(1, columns - len(station) - 2))
            lines = [
                random_line(
                    columns,
                    train_column if row == train_row else None,
                    station,
                )
                for row in range(visible_rows)
            ]
            lines = joke_frame(elapsed, columns, visible_rows) or lines
            frame = "\033[H" + "\n".join(lines)
            sys.stdout.write(frame)
            sys.stdout.flush()
            time.sleep(FRAME_DELAY_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

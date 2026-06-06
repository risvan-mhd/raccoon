from __future__ import annotations
from typing import Self
from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass

from pyray import Color, ConfigFlags, Font, KeyboardKey as Key, TextureFilter
import pyray as ray


FONT_SIZE = 24.0
SPACING = 1.0

FG_COLOR = Color(255, 255, 255, 255)
BG_COLOR = Color(30, 30, 30, 255)

SELECTION_COLOR = Color(61, 123, 255, 100)

DIR_COLOR = Color(66, 135, 245, 255)
FILE_COLOR = Color(66, 245, 87, 255)

font_regular: Font | None = None
font_bold: Font | None = None


class EntryType(Enum):
    FILE = auto()
    DIR = auto()


@dataclass(frozen=True)
class Entry:
    name: str
    etype: EntryType
    path: Path
    color: Color

    @classmethod
    def of(cls, path: Path) -> Self:
        name = path.name
        etype = EntryType.FILE if path.is_file() else EntryType.DIR
        color = FILE_COLOR if path.is_file() else DIR_COLOR
        return cls(name=name, etype=etype, path=path, color=color)


@dataclass
class State:
    cwd: Path
    files: list[Entry]
    selected_idx: int


def draw_text(
    text: str, x: int, y: int, color: Color = FG_COLOR, bold: bool = False
) -> None:
    assert font_regular and font_bold

    font = font_bold if bold else font_regular
    ray.draw_text_ex(
        font, text, (float(x), float(y)), FONT_SIZE, SPACING, color
    )


def get_line_height() -> int:
    assert font_regular
    text_size = ray.measure_text_ex(font_regular, "M", FONT_SIZE, SPACING)
    return int(text_size.y)


def draw_line(line: int, color: Color) -> None:
    assert font_regular
    width = ray.get_screen_width()
    height = get_line_height()

    x = 0
    y = line * height
    ray.draw_rectangle(x, y, width, height, color)


def list_dir(path: Path) -> list[Entry]:
    assert path.resolve().is_dir()
    return list(
        map(
            lambda p: Entry.of(p),
            sorted(
                filter(lambda p: not p.name.startswith("."), path.iterdir()),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            ),
        )
    )


def load_fonts() -> None:
    global font_regular, font_bold

    font_regular = ray.load_font(
        "./fonts/JetBrainsMonoNerdFontMono-Regular.ttf"
    )
    ray.set_texture_filter(
        font_regular.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )

    font_bold = ray.load_font("./fonts/JetBrainsMonoNerdFontMono-Bold.ttf")
    ray.set_texture_filter(
        font_bold.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )


def is_key_pressed(key: int, repeat: bool = True) -> bool:
    return ray.is_key_pressed(key) or (
        repeat and ray.is_key_pressed_repeat(key)
    )


def handle_input(state: State) -> None:
    if is_key_pressed(Key.KEY_J):
        state.selected_idx = min(state.selected_idx + 1, len(state.files) - 1)

    elif is_key_pressed(Key.KEY_K):
        state.selected_idx = max(0, state.selected_idx - 1)

    elif is_key_pressed(Key.KEY_ENTER, False) and state.files:
        file = state.files[state.selected_idx]
        if file.etype == EntryType.DIR:
            state.cwd = file.path
            state.files = list_dir(state.cwd)
            state.selected_idx = 0

    elif is_key_pressed(Key.KEY_H):
        state.cwd = state.cwd.parent
        state.files = list_dir(state.cwd)
        state.selected_idx = 0


def main():
    cwd = Path.cwd()
    files = list_dir(cwd)
    selected_idx = 0

    state = State(cwd, files, selected_idx)

    ray.set_config_flags(ConfigFlags.FLAG_WINDOW_RESIZABLE)

    ray.init_window(800, 800, "Raccoon")
    ray.set_target_fps(60)
    ray.set_exit_key(Key.KEY_Q)
    load_fonts()

    pad_x = 18
    line_height = get_line_height()
    while not ray.window_should_close():
        handle_input(state)

        ray.begin_drawing()
        ray.clear_background(BG_COLOR)

        draw_line(0, Color(20, 20, 20, 150))
        draw_text(state.cwd.as_posix(), pad_x, 0)

        line = 1
        for i, file in enumerate(state.files):
            bold = False
            if i == state.selected_idx:
                bold = True
                draw_line(line, SELECTION_COLOR)

            x = pad_x
            y = line_height * line
            draw_text(file.name, x, y, color=file.color, bold=bold)
            line += 1

        ray.end_drawing()

    ray.close_window()


if __name__ == "__main__":
    main()

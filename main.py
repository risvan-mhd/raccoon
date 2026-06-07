from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Self

from pyray import Color, ConfigFlags, Font, KeyboardKey as Key, TextureFilter
import pyray as ray

from icons import (
    ICONS,
    DIR_ICON,
    FILE_ICON,
    ICONS,
    LICENSE_ICON,
    MAKE_FILE_ICON,
    Icon,
    icon_map,
)


FONT_SIZE = 24.0
SPACING = 1.0

FG_COLOR = Color(255, 255, 255, 255)
BG_COLOR = Color(30, 30, 30, 255)

SELECTION_COLOR = Color(52, 52, 52, 100)

DIR_COLOR = Color(66, 135, 245, 255)
FILE_COLOR = Color(255, 255, 255, 255)

font_regular: Font | None = None
font_bold: Font | None = None


class EntryType(Enum):
    FILE = auto()
    DIR = auto()


@dataclass(frozen=True)
class Entry:
    name: str
    icon: Icon
    etype: EntryType
    path: Path
    color: Color

    @classmethod
    def of(cls, path: Path) -> Self:
        name = path.name
        icon = get_icon(path)
        etype = EntryType.FILE if path.is_file() else EntryType.DIR
        color = FILE_COLOR if path.is_file() else DIR_COLOR
        return cls(
            name=name,
            icon=icon,
            etype=etype,
            path=path,
            color=color,
        )


@dataclass
class State:
    cwd: Path
    files: list[Entry]
    selected_idx: int


def get_icon(path: Path) -> Icon:
    if path.is_dir():
        return DIR_ICON

    name_lower = path.name.lower()
    if name_lower == "license":
        return LICENSE_ICON

    if name_lower == "makefile":
        return MAKE_FILE_ICON

    return icon_map.get(path.suffix, FILE_ICON)


def draw_text(
    text: str, x: int, y: int, color: Color = FG_COLOR, bold: bool = False
) -> None:
    assert font_regular and font_bold

    font = font_bold if bold else font_regular
    ray.draw_text_ex(
        font, text, (float(x), float(y)), FONT_SIZE, SPACING, color
    )


def get_line_size() -> tuple[int, int]:
    assert font_regular
    text_size = ray.measure_text_ex(font_regular, "M", FONT_SIZE, SPACING)
    return int(text_size.x), int(text_size.y)


def draw_line(line: int, color: Color) -> None:
    assert font_regular
    width = ray.get_screen_width()
    _, height = get_line_size()

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

    # Standard 95 printable ASCII characters (codes 32 to 126)
    codepoints = tuple(range(32, 127))
    codepoints = codepoints + tuple(ord(icon.char) for icon in ICONS)

    count = len(codepoints)
    c_codepoints = ray.ffi.new(f"int[]", codepoints)
    c_ptr = ray.ffi.cast("int *", c_codepoints)

    font_regular = ray.load_font_ex(
        "./fonts/JetBrainsMonoNerdFontMono-Regular.ttf",
        int(FONT_SIZE),
        c_ptr,
        count,
    )
    ray.set_texture_filter(
        font_regular.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )

    font_bold = ray.load_font_ex(
        "./fonts/JetBrainsMonoNerdFontMono-Bold.ttf",
        int(FONT_SIZE),
        c_ptr,
        count,
    )
    ray.set_texture_filter(
        font_bold.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )


def unload_fonts() -> None:
    if font_regular:
        ray.unload_font(font_regular)

    if font_bold:
        ray.unload_font(font_bold)


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
    line_width, line_height = get_line_size()
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
            icon = file.icon
            draw_text(icon.char, x, y, color=icon.color, bold=bold)

            x += 2 * line_width
            draw_text(file.name, x, y, color=file.color, bold=bold)

            line += 1

        ray.end_drawing()

    unload_fonts()
    ray.close_window()


if __name__ == "__main__":
    main()

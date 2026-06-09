from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Self

from pyray import (
    Color,
    ConfigFlags,
    Font,
    KeyboardKey as Key,
    TextureFilter,
)
import pyray as ray

from icons import (
    Icon,
    ICONS,
    DIR_ICON,
    FILE_ICON,
    LICENSE_ICON,
    MAKE_FILE_ICON,
    icon_map,
)


FG_COLOR = Color(255, 255, 255, 255)
BG_COLOR = Color(30, 30, 30, 255)

SELECTION_COLOR = Color(52, 52, 52, 100)

DIR_COLOR = Color(66, 135, 245, 255)
FILE_COLOR = Color(255, 255, 255, 255)


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
    grid: Grid
    scroll_top: int = 0


@dataclass(frozen=True)
class Grid:
    cell_width: int
    cell_height: int
    font_size: float
    font_regular: Font
    font_bold: Font

    def rows(self) -> int:
        return ray.get_screen_height() // self.cell_height

    def cell_to_pixel(self, col: int, row: int) -> tuple[int, int]:
        return col * self.cell_width, row * self.cell_height

    def draw_line(self, row: int, fill: Color) -> None:
        w = ray.get_screen_width() // self.cell_width
        self.draw_rect(0, row, w, 1, fill)

    def draw_rect(
        self, col: int, row: int, width: int, height: int, fill: Color
    ) -> None:
        x, y = self.cell_to_pixel(col, row)
        w, h = self.cell_to_pixel(width, height)
        ray.draw_rectangle(x, y, w, h, fill)

    def draw_text(
        self,
        text: str,
        col: int,
        row: int,
        color: Color = FG_COLOR,
        bold: bool = False,
    ) -> None:
        font = self.font_bold if bold else self.font_regular
        ray.draw_text_ex(
            font,
            text,
            self.cell_to_pixel(col, row),
            self.font_size,
            1.0,
            color,
        )


def get_icon(path: Path) -> Icon:
    if path.is_dir():
        return DIR_ICON

    name_lower = path.name.lower()
    if name_lower == "license":
        return LICENSE_ICON

    if name_lower == "makefile":
        return MAKE_FILE_ICON

    return icon_map.get(path.suffix, FILE_ICON)


def get_char_size(font: Font, font_size: float) -> tuple[int, int]:
    text_size = ray.measure_text_ex(font, "M", font_size, 1.0)
    return int(text_size.x), int(text_size.y)


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


def load_fonts(font_size: int) -> tuple[Font, Font]:
    # Standard 95 printable ASCII characters (codes 32 to 126)
    codepoints = tuple(range(32, 127))
    codepoints = codepoints + tuple(ord(icon.char) for icon in ICONS)

    count = len(codepoints)
    c_codepoints = ray.ffi.new(f"int[]", codepoints)
    c_ptr = ray.ffi.cast("int *", c_codepoints)

    font_regular = ray.load_font_ex(
        "./fonts/JetBrainsMonoNerdFontMono-Regular.ttf",
        font_size,
        c_ptr,
        count,
    )
    ray.set_texture_filter(
        font_regular.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )

    font_bold = ray.load_font_ex(
        "./fonts/JetBrainsMonoNerdFontMono-Bold.ttf",
        font_size,
        c_ptr,
        count,
    )
    ray.set_texture_filter(
        font_bold.texture, TextureFilter.TEXTURE_FILTER_BILINEAR
    )

    return font_regular, font_bold


def unload_fonts(*fonts: Font) -> None:
    for font in fonts:
        ray.unload_font(font)


def is_key_pressed(key: int, repeat: bool = True) -> bool:
    return ray.is_key_pressed(key) or (
        repeat and ray.is_key_pressed_repeat(key)
    )


def handle_input(state: State) -> None:
    visible_rows = state.grid.rows() - 1  # For top bar

    if is_key_pressed(Key.KEY_J):
        state.selected_idx = min(state.selected_idx + 1, len(state.files) - 1)
        if state.selected_idx >= state.scroll_top + visible_rows:
            state.scroll_top = state.selected_idx - visible_rows + 1

    elif is_key_pressed(Key.KEY_K):
        state.selected_idx = max(0, state.selected_idx - 1)
        if state.selected_idx < state.scroll_top:
            state.scroll_top = state.selected_idx

    elif (
        is_key_pressed(Key.KEY_ENTER, False) or is_key_pressed(Key.KEY_L, False)
    ) and state.files:
        file = state.files[state.selected_idx]
        if file.etype == EntryType.DIR:
            state.cwd = file.path
            state.files = list_dir(state.cwd)
            state.selected_idx = 0
            state.scroll_top = 0

    elif is_key_pressed(Key.KEY_H):
        state.cwd = state.cwd.parent
        state.files = list_dir(state.cwd)
        state.selected_idx = 0
        state.scroll_top = 0


def main():
    cwd = Path.cwd()
    files = list_dir(cwd)
    selected_idx = 0

    ray.set_config_flags(ConfigFlags.FLAG_WINDOW_RESIZABLE)

    ray.init_window(800, 800, "Raccoon")
    ray.set_target_fps(60)
    ray.set_exit_key(Key.KEY_Q)

    font_size = 24
    font_regular, font_bold = load_fonts(font_size)

    pad_col = 2
    char_width, char_height = get_char_size(font_regular, float(font_size))
    grid = Grid(char_width, char_height, font_size, font_regular, font_bold)
    state = State(cwd, files, selected_idx, grid)
    while not ray.window_should_close():
        handle_input(state)

        ray.begin_drawing()
        ray.clear_background(BG_COLOR)

        grid.draw_line(0, Color(20, 20, 20, 150))
        grid.draw_text(state.cwd.as_posix(), pad_col, 0)

        visible_rows = (ray.get_screen_height() // char_height) - 1
        visible_files = state.files[
            state.scroll_top : state.scroll_top + visible_rows
        ]

        line = 1
        for visible_i, file in enumerate(visible_files):
            real_idx = state.scroll_top + visible_i

            bold = False
            if real_idx == state.selected_idx:
                bold = True
                grid.draw_line(line, SELECTION_COLOR)

            col = pad_col
            row = line
            icon = file.icon
            grid.draw_text(icon.char, col, row, color=icon.color, bold=bold)

            col += 2
            grid.draw_text(file.name, col, row, color=file.color, bold=bold)

            line += 1

        ray.end_drawing()

    unload_fonts(font_regular, font_bold)
    ray.close_window()


if __name__ == "__main__":
    main()

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
INACTIVE_COLOR = Color(40, 40, 40, 255)

DIR_COLOR = Color(66, 135, 245, 255)
FILE_COLOR = Color(255, 255, 255, 255)


class EntryType(Enum):
    FILE = auto()
    DIR = auto()


class Layout(Enum):
    VERTICAL = auto()
    HORIZONTAL = auto()


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
    buffer_1: FileBuffer
    buffer_2: FileBuffer
    active_buffer: FileBuffer
    layout: Layout = Layout.HORIZONTAL

    def swap_active(self) -> None:
        self.active_buffer = (
            self.buffer_2
            if self.active_buffer is self.buffer_1
            else self.buffer_1
        )

    def swap_layout(self) -> None:
        self.layout = (
            Layout.VERTICAL
            if self.layout == Layout.HORIZONTAL
            else Layout.HORIZONTAL
        )

    def swap_buffers(self) -> None:
        self.buffer_1, self.buffer_2 = self.buffer_2, self.buffer_1


@dataclass(frozen=True)
class Grid:
    cell_width: int
    cell_height: int
    font_size: float
    font_regular: Font
    font_bold: Font

    def rows(self) -> int:
        return ray.get_screen_height() // self.cell_height

    def cols(self) -> int:
        return ray.get_screen_width() // self.cell_width

    def cell_to_pixel(self, col: int, row: int) -> tuple[int, int]:
        return col * self.cell_width, row * self.cell_height

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


class FileBuffer:
    def __init__(self) -> None:
        self.path: Path = Path(".")
        self.entries: list[Entry] = []
        self.selected_idx = 0
        self.scroll_top = 0

    def set_path(self, path: Path) -> None:
        self.path = path
        self.entries = list_dir(path)
        self.selected_idx = 0
        self.scroll_top = 0

    def move_down(self, visible_rows: int) -> None:
        if not self.entries:
            return

        visible_rows -= 1  # First row is for header
        self.selected_idx = min(self.selected_idx + 1, len(self.entries) - 1)
        if self.selected_idx >= self.scroll_top + visible_rows:
            self.scroll_top = self.selected_idx - visible_rows + 1

    def move_up(self) -> None:
        if not self.entries:
            return

        self.selected_idx = max(0, self.selected_idx - 1)
        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx

    def enter(self) -> None:
        if not self.entries:
            return

        file = self.entries[self.selected_idx]
        if file.etype == EntryType.DIR:
            self.set_path(file.path)

    def parent(self) -> None:
        self.set_path(self.path.parent)


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


def draw_file_buffer(
    buffer: FileBuffer,
    grid: Grid,
    col: int,
    row: int,
    width: int,
    height: int,
    col_pad: int,
    row_pad: int,
    is_active: bool,
) -> None:
    visible_files = buffer.entries[
        buffer.scroll_top : buffer.scroll_top + height - 1
    ]

    if not is_active:
        grid.draw_rect(col, row, width, height, INACTIVE_COLOR)

    grid.draw_rect(col, row, width, 1, Color(20, 20, 20, 150))
    grid.draw_text(buffer.path.as_posix(), col + col_pad, row + row_pad)

    line = 1
    for visible_i, file in enumerate(visible_files):
        real_idx = buffer.scroll_top + visible_i

        bold = False
        if is_active and real_idx == buffer.selected_idx:
            bold = True
            grid.draw_rect(col, row + line, width, 1, SELECTION_COLOR)

        line_col = col + col_pad
        line_row = row + line + row_pad
        icon = file.icon
        grid.draw_text(
            icon.char, line_col, line_row, color=icon.color, bold=bold
        )

        line_col += 2
        grid.draw_text(
            file.name, line_col, line_row, color=file.color, bold=bold
        )

        line += 1


def draw(state: State, grid: Grid) -> None:
    pad_x = 2
    pad_y = 0

    width = grid.cols()
    height = grid.rows()

    b1_x = 0
    b1_y = 0

    b2_x = 0
    b2_y = 0

    if state.layout == Layout.HORIZONTAL:
        width //= 2
        b2_x = width
    else:
        height //= 2
        b2_y = height

    draw_file_buffer(
        state.buffer_1,
        grid,
        b1_x,
        b1_y,
        width,
        height,
        pad_x,
        pad_y,
        state.buffer_1 is state.active_buffer,
    )
    draw_file_buffer(
        state.buffer_2,
        grid,
        b2_x,
        b2_y,
        width,
        height,
        pad_x,
        pad_y,
        state.buffer_2 is state.active_buffer,
    )


def handle_input(state: State, visible_rows: int) -> None:
    buffer = state.active_buffer
    if is_key_pressed(Key.KEY_J):
        buffer.move_down(visible_rows)

    elif is_key_pressed(Key.KEY_K):
        buffer.move_up()

    elif is_key_pressed(Key.KEY_ENTER, False) or is_key_pressed(
        Key.KEY_L, False
    ):
        buffer.enter()

    elif is_key_pressed(Key.KEY_H, False):
        buffer.parent()

    elif is_key_pressed(Key.KEY_TAB):
        state.swap_active()

    elif is_key_pressed(Key.KEY_O):
        state.swap_layout()

    elif is_key_pressed(Key.KEY_S):
        state.swap_buffers()
        state.swap_active()  # Keep the same side active after swapping buffers


def main():
    ray.set_config_flags(ConfigFlags.FLAG_WINDOW_RESIZABLE)

    ray.init_window(800, 800, "Raccoon")
    ray.set_target_fps(60)
    ray.set_exit_key(Key.KEY_Q)

    font_size = 24
    font_regular, font_bold = load_fonts(font_size)

    cwd = Path.cwd()
    char_width, char_height = get_char_size(font_regular, float(font_size))
    grid = Grid(char_width, char_height, font_size, font_regular, font_bold)

    b1 = FileBuffer()
    b1.set_path(cwd)

    b2 = FileBuffer()
    b2.set_path(cwd)

    state = State(b1, b2, b1)
    while not ray.window_should_close():
        handle_input(state, grid.rows())
        ray.begin_drawing()
        ray.clear_background(BG_COLOR)
        draw(state, grid)
        ray.end_drawing()

    unload_fonts(font_regular, font_bold)
    ray.close_window()


if __name__ == "__main__":
    main()

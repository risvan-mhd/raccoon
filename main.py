from __future__ import annotations
from dataclasses import astuple, dataclass, field
from typing import Iterator, Self
from enum import Enum, auto
from pathlib import Path

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


class Mode(Enum):
    NORMAL = auto()
    MARK_PENDING = auto()


@dataclass
class State:
    pane_1: Pane
    pane_2: Pane
    active_pane: Pane
    mode: Mode = Mode.NORMAL
    layout: Layout = Layout.HORIZONTAL
    zoomed: bool = False
    marks: dict[int, Path] = field(default_factory=dict)

    def toggle_zoom(self) -> None:
        self.zoomed = not self.zoomed

    def swap_active(self) -> None:
        self.active_pane = (
            self.pane_2 if self.active_pane is self.pane_1 else self.pane_1
        )

    def swap_layout(self) -> None:
        self.layout = (
            Layout.VERTICAL
            if self.layout == Layout.HORIZONTAL
            else Layout.HORIZONTAL
        )

    def swap_panes(self) -> None:
        self.pane_1, self.pane_2 = self.pane_2, self.pane_1


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
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: list[Entry] = []
        self.selected_idx = 0

        self.set_path(path)

    def selected(self) -> Entry:
        assert self.entries
        return self.entries[self.selected_idx]

    def set_path(self, path: Path) -> None:
        self.path = path
        self.entries = list_dir(path)
        self.selected_idx = 0

    def set_selected_idx(self, idx: int) -> None:
        self.selected_idx = max(0, min(idx, len(self.entries) - 1))

    def change_idx(self, by: int) -> None:
        self.set_selected_idx(self.selected_idx + by)


@dataclass(frozen=True)
class Geometry:
    x: int
    y: int
    width: int
    height: int

    def __iter__(self) -> Iterator[int]:
        return iter(astuple(self))


class Pane:
    def __init__(self, path: Path) -> None:
        self.scroll_top: int = 0
        self.buffer = FileBuffer(path)
        self.geometry = Geometry(0, 0, 0, 0)

    def selected_idx(self) -> int:
        return self.buffer.selected_idx

    def path(self) -> Path:
        return self.buffer.path

    def visible_files(self) -> list[Entry]:
        return self.buffer.entries[
            self.scroll_top : self.scroll_top + self.geometry.height - 1
        ]

    def has_entries(self) -> bool:
        return len(self.buffer.entries) != 0

    def set_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.geometry = Geometry(x, y, width, height)

    def move_down(self) -> None:
        if not self.has_entries():
            return

        visible_rows = self.geometry.height - 1  # First row is for header
        self.buffer.change_idx(1)
        if self.selected_idx() >= self.scroll_top + visible_rows:
            self.scroll_top = self.selected_idx() - visible_rows + 1

    def move_up(self) -> None:
        if not self.has_entries():
            return

        self.buffer.change_idx(-1)
        if self.selected_idx() < self.scroll_top:
            self.scroll_top = self.selected_idx()

    def enter(self) -> None:
        if not self.has_entries():
            return

        file = self.buffer.selected()
        if file.etype == EntryType.DIR:
            self.buffer.set_path(file.path)

    def parent(self) -> None:
        self.buffer.set_path(self.buffer.path.parent)


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


def draw_pane(
    pane: Pane,
    grid: Grid,
    col_pad: int,
    row_pad: int,
    is_active: bool,
) -> None:
    visible_files = pane.visible_files()
    x, y, width, height = pane.geometry

    if not is_active:
        grid.draw_rect(x, y, width, height, INACTIVE_COLOR)

    grid.draw_rect(x, y, width, 1, Color(20, 20, 20, 150))
    grid.draw_text(pane.path().as_posix(), x + col_pad, y + row_pad)

    line = 1
    for visible_i, file in enumerate(visible_files):
        real_idx = pane.scroll_top + visible_i

        bold = False
        if is_active and real_idx == pane.selected_idx():
            bold = True
            grid.draw_rect(x, y + line, width, 1, SELECTION_COLOR)

        line_col = x + col_pad
        line_row = y + line + row_pad
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
    if state.zoomed:
        draw_pane(state.active_pane, grid, pad_x, pad_y, True)
        return

    draw_pane(
        state.pane_1,
        grid,
        pad_x,
        pad_y,
        state.pane_1 is state.active_pane,
    )
    draw_pane(
        state.pane_2,
        grid,
        pad_x,
        pad_y,
        state.pane_2 is state.active_pane,
    )


def update_panes(state: State, screen_cols: int, screen_rows: int) -> None:
    if state.zoomed:
        state.active_pane.set_geometry(0, 0, screen_cols, screen_rows)
        return

    p1_x = 0
    p1_y = 0

    p2_x = 0
    p2_y = 0

    if state.layout == Layout.HORIZONTAL:
        screen_cols //= 2
        p2_x = screen_cols
    else:
        screen_rows //= 2
        p2_y = screen_rows

    state.pane_1.set_geometry(p1_x, p1_y, screen_cols, screen_rows)
    state.pane_2.set_geometry(p2_x, p2_y, screen_cols, screen_rows)


def handle_input_normal(state: State) -> None:
    pane = state.active_pane
    if is_key_pressed(Key.KEY_J):
        pane.move_down()

    elif is_key_pressed(Key.KEY_K):
        pane.move_up()

    elif is_key_pressed(Key.KEY_ENTER, False) or is_key_pressed(
        Key.KEY_L, False
    ):
        pane.enter()

    elif is_key_pressed(Key.KEY_H, False):
        pane.parent()

    elif is_key_pressed(Key.KEY_TAB):
        state.swap_active()

    elif is_key_pressed(Key.KEY_O):
        state.swap_layout()

    elif is_key_pressed(Key.KEY_S):
        state.swap_panes()
        state.swap_active()  # Keep the same side active after swapping buffers

    elif is_key_pressed(Key.KEY_Z, False):
        state.toggle_zoom()

    elif is_key_pressed(Key.KEY_M, False):
        state.mode = Mode.MARK_PENDING


def handle_input_mark_pending(state: State) -> None:
    key = ray.get_char_pressed()
    if not key:
        return

    state.marks[key] = state.active_pane.path()
    state.mode = Mode.NORMAL


def handle_input(state: State) -> None:
    match state.mode:
        case Mode.NORMAL:
            handle_input_normal(state)

        case Mode.MARK_PENDING:
            handle_input_mark_pending(state)


def main() -> None:
    ray.set_config_flags(ConfigFlags.FLAG_WINDOW_RESIZABLE)

    ray.init_window(800, 800, "Raccoon")
    ray.set_target_fps(60)
    ray.set_exit_key(Key.KEY_Q)

    font_size = 24
    font_regular, font_bold = load_fonts(font_size)

    cwd = Path.cwd()
    char_width, char_height = get_char_size(font_regular, float(font_size))
    grid = Grid(char_width, char_height, font_size, font_regular, font_bold)

    p1 = Pane(cwd)
    p2 = Pane(cwd)

    state = State(p1, p2, p1)
    while not ray.window_should_close():
        update_panes(state, grid.cols(), grid.rows())
        handle_input(state)

        ray.begin_drawing()
        ray.clear_background(BG_COLOR)
        draw(state, grid)
        ray.end_drawing()

    unload_fonts(font_regular, font_bold)
    ray.close_window()


if __name__ == "__main__":
    main()

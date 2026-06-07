from dataclasses import dataclass

from pyray import Color


@dataclass(frozen=True)
class Icon:
    char: str
    color: Color


DIR_ICON = Icon(
    "",
    Color(66, 135, 245, 255),
)
FILE_ICON = Icon(
    "",
    Color(255, 255, 255, 255),
)
LICENSE_ICON = Icon(
    "",
    Color(255, 213, 0, 255),
)
MAKE_FILE_ICON = Icon(
    "",
    Color(227, 168, 87, 255),
)
IMAGE_ICON = Icon(
    "",
    Color(222, 0, 255, 255),
)

VIDEO_ICON = Icon(
    "",
    Color(222, 0, 255, 255),
)

AUDIO_ICON = Icon(
    "",
    Color(222, 0, 255, 255),
)

icon_map: dict[str, Icon] = {
    ".py": Icon("", Color(69, 239, 255, 255)),
    ".c": Icon("", Color(0, 145, 255, 255)),
    ".txt": Icon("", Color(222, 222, 222, 255)),
    ".sh": Icon("", Color(68, 255, 0, 255)),
    ".bash": Icon("", Color(68, 255, 0, 255)),
    ".json": Icon("", Color(245, 255, 56, 255)),
    ".toml": Icon("", Color(0, 200, 255, 255)),
    ".md": Icon("", Color(0, 123, 255, 255)),
    ".lock": Icon("󰌾", Color(255, 145, 0, 255)),
    ".ttf": Icon("", Color(125, 125, 125, 255)),
    ".png": IMAGE_ICON,
    ".jpg": IMAGE_ICON,
    ".jpeg": IMAGE_ICON,
    ".mp3": AUDIO_ICON,
    ".wav": AUDIO_ICON,
    ".mp4": VIDEO_ICON,
    ".mkv": VIDEO_ICON,
}

ICONS = set([DIR_ICON, FILE_ICON, LICENSE_ICON, MAKE_FILE_ICON]) | set(
    icon_map.values()
)

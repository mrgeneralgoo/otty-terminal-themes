"""Convert user-supplied Otty TOML themes to macOS Terminal profiles."""

from __future__ import annotations

import argparse
import plistlib
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

PALETTE_KEYS = ("Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White")


class ThemeError(ValueError):
    """Raised when an Otty theme is unsupported or invalid."""


def _color(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value) is None:
        raise ThemeError(f"{label} must be #RRGGBB or #RRGGBBAA")
    raw = value[1:]
    channels = tuple(int(raw[index : index + 2], 16) / 255 for index in range(0, len(raw), 2))
    return (*channels[:3], channels[3] if len(channels) == 4 else 1.0)


def _profile_color(value: tuple[float, float, float, float]) -> bytes:
    """Serialize device RGB components in Terminal's NSKeyedArchiver format."""
    red, green, blue, alpha = value
    components = f"{red!r} {green!r} {blue!r} {alpha!r}".encode("ascii") + b"\0"
    archive = {
        "$archiver": "NSKeyedArchiver",
        "$version": 100000,
        "$objects": [
            "$null",
            {"$class": plistlib.UID(2), "NSColorSpace": 2, "NSRGB": components},
            {"$classes": ["NSColor", "NSObject"], "$classname": "NSColor"},
        ],
        "$top": {"root": plistlib.UID(1)},
    }
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def convert_theme(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Validate a parsed theme and return its filename stem and Terminal profile."""
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise ThemeError("missing [meta]")
    name = meta.get("name")
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 80
        or not name[0].isalnum()
        or any(not (char.isalnum() or char in " _.-") for char in name)
    ):
        raise ThemeError("meta.name must be a safe filename (Unicode letters, digits, spaces, _.-)")
    if any(key in data for key in ("inherits", "extends")) or meta.get("inherits") or meta.get("extends"):
        raise ThemeError(f"{name}: inherited themes are not supported")
    mode = meta.get("mode")
    if mode not in ("dark", "light"):
        raise ThemeError(f"{name}: meta.mode must be dark or light")

    foreground = _color(_nested(data, "terminal", "foreground"), "terminal.foreground")
    raw_background = _nested(data, "terminal", "background")
    transparent = raw_background == "none"
    background = (
        (0.0, 0.0, 0.0, 0.0) if mode == "dark" else (1.0, 1.0, 1.0, 0.0)
    ) if transparent else _color(raw_background, "terminal.background")

    palette = _nested(data, "terminal", "palette")
    if not isinstance(palette, list) or len(palette) != 16:
        raise ThemeError(f"{name}: terminal.palette must contain exactly 16 colors")
    colors: dict[str, tuple[float, float, float, float]] = {}
    for index, key in enumerate((*PALETTE_KEYS, *PALETTE_KEYS)):
        group = "Bright" if index >= 8 else ""
        colors[f"ANSI{group}{key}Color"] = _color(palette[index], f"terminal.palette[{index}]")

    cursor_value = _nested(data, "cursor", "color")
    if cursor_value is None:
        cursor_value = _nested(data, "terminal", "cursor")
    cursor = _color(cursor_value, "cursor color") if cursor_value is not None else foreground

    profile: dict[str, Any] = {
        "type": "Window Settings",
        "name": f"Otty — {name}",
        "TextColor": _profile_color(foreground),
        "TextBoldColor": _profile_color(foreground),
        "BackgroundColor": _profile_color(background),
        "CursorColor": _profile_color(cursor),
        **{key: _profile_color(value) for key, value in colors.items()},
    }
    selection = _nested(data, "selection", "background")
    if selection is None:
        selection = _nested(data, "terminal", "selection-background")
    if selection is not None:
        profile["SelectionColor"] = _profile_color(_color(selection, "selection background"))
    if transparent:
        profile["BackgroundAlpha"] = 0.0
    return name, profile


def _load(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
        return convert_theme(data)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ThemeError(f"{path.name}: {exc}") from exc


def convert(source: Path, output: Path) -> list[Path]:
    """Convert all .ottytheme files after validating every input."""
    inputs = [source] if source.is_file() else sorted(source.glob("*.ottytheme")) if source.is_dir() else []
    if not inputs:
        raise ThemeError(f"no .ottytheme files found at {source}")
    converted = [_load(path) for path in inputs]
    names = [name.casefold() for name, _ in converted]
    if len(set(names)) != len(names):
        raise ThemeError("duplicate theme names")
    output.mkdir(parents=True, exist_ok=True)
    destinations = [output / f"{name}.terminal" for name, _ in converted]
    for destination, (_, profile) in zip(destinations, converted, strict=True):
        destination.write_bytes(plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=True))
    return destinations


def main() -> int:
    """Run the command-line converter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help=".ottytheme TOML file or directory")
    parser.add_argument("output", type=Path, help="directory for generated .terminal profiles")
    args = parser.parse_args()
    try:
        for path in convert(args.source, args.output):
            print(path)
    except ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

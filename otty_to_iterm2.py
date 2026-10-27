"""Convert Otty TOML themes to iTerm2 color presets."""

from __future__ import annotations

import argparse
import plistlib
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


class ThemeError(ValueError):
    """Raised when an Otty theme is unsupported or invalid."""


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _color(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, str) or re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value) is None:
        raise ThemeError(f"{label} must be #RRGGBB or #RRGGBBAA")
    raw = value[1:]
    channels = tuple(int(raw[index:index + 2], 16) / 255 for index in range(0, len(raw), 2))
    return (*channels[:3], channels[3] if len(channels) == 4 else 1.0)


def _iterm_color(value: tuple[float, float, float, float]) -> dict[str, Any]:
    red, green, blue, alpha = value
    return {
        "Color Space": "sRGB",
        "Red Component": red,
        "Green Component": green,
        "Blue Component": blue,
        "Alpha Component": alpha,
    }


def convert_theme(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Validate a parsed theme and return its safe name and iTerm2 preset."""
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise ThemeError("missing [meta]")
    name = meta.get("name")
    if (
        not isinstance(name, str) or not name or len(name) > 80 or not name[0].isalnum()
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
    if raw_background == "none":
        background = (0.0, 0.0, 0.0, 1.0) if mode == "dark" else (1.0, 1.0, 1.0, 1.0)
    else:
        background = _color(raw_background, "terminal.background")
    palette = _nested(data, "terminal", "palette")
    if not isinstance(palette, list) or len(palette) != 16:
        raise ThemeError(f"{name}: terminal.palette must contain exactly 16 colors")

    colors = {
        f"Ansi {index} Color": _color(value, f"terminal.palette[{index}]")
        for index, value in enumerate(palette)
    }
    colors["Foreground Color"] = foreground
    colors["Background Color"] = background
    colors["Bold Color"] = foreground

    cursor = _nested(data, "cursor", "color")
    if cursor is None:
        cursor = _nested(data, "terminal", "cursor")
    colors["Cursor Color"] = _color(cursor, "cursor color") if cursor is not None else foreground

    overrides = (
        ("Selection Color", "selection", "background", "terminal", "selection-background"),
        ("Selected Text Color", "selection", "foreground", "terminal", "selection-foreground"),
        ("Cursor Text Color", "cursor", "text", "terminal", "cursor-text"),
    )
    for key, section, field, legacy_section, legacy_field in overrides:
        value = _nested(data, section, field)
        if value is None:
            value = _nested(data, legacy_section, legacy_field)
        if value is not None:
            colors[key] = _color(value, key)
    return name, {key: _iterm_color(value) for key, value in colors.items()}


def _load(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        with path.open("rb") as stream:
            return convert_theme(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ThemeError(f"{path.name}: {exc}") from exc


def convert(source: Path, output: Path) -> list[Path]:
    """Convert all source themes after validating the full input batch."""
    inputs = [source] if source.is_file() else sorted(source.glob("*.ottytheme")) if source.is_dir() else []
    if not inputs:
        raise ThemeError(f"no .ottytheme files found at {source}")
    converted = [_load(path) for path in inputs]
    names = [name.casefold() for name, _ in converted]
    if len(set(names)) != len(names):
        raise ThemeError("duplicate theme names")
    destinations = [output / f"Otty - {name}.itermcolors" for name, _ in converted]
    serialized = [plistlib.dumps(preset, fmt=plistlib.FMT_XML, sort_keys=True) for _, preset in converted]
    output.mkdir(parents=True, exist_ok=True)
    for destination, contents in zip(destinations, serialized, strict=True):
        destination.write_bytes(contents)
    return destinations


def main() -> int:
    """Run the command-line converter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help=".ottytheme TOML file or directory")
    parser.add_argument("output", type=Path, help="directory for generated .itermcolors files")
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

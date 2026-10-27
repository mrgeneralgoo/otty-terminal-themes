"""Tests for the converter and the checked-in Otty theme snapshots."""

import hashlib
import json
import tomllib
import plistlib
import tempfile
import unittest
from pathlib import Path

from otty_to_terminal import ThemeError, convert, convert_theme


COLORS = [f"#{index:02x}{(index + 16):02x}{(index + 32):02x}" for index in range(16)]
KEYS = ("Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White")


def theme(name: str = "Synthetic", background: str = "#123456") -> dict:
    return {
        "meta": {"name": name, "mode": "dark"},
        "terminal": {"foreground": "#abcdef", "background": background, "palette": COLORS.copy()},
    }


def rgb(profile: dict, key: str) -> tuple[float, float, float, float]:
    archive = plistlib.loads(profile[key])
    raw = archive["$objects"][1]["NSRGB"]
    assert isinstance(raw, bytes) and raw.endswith(b"\0")
    return tuple(float(part) for part in raw[:-1].decode("ascii").split())  # type: ignore[return-value]


class ConverterTests(unittest.TestCase):
    def test_array_palette_maps_sixteen_distinct_colors_in_index_order(self) -> None:
        _, profile = convert_theme(theme())
        self.assertEqual(len([key for key in profile if key.startswith("ANSI")]), 16)
        self.assertEqual(profile["name"], "Otty — Synthetic")
        self.assertEqual(profile["type"], "Window Settings")
        for index, color in enumerate(COLORS):
            name = f"ANSI{'Bright' if index >= 8 else ''}{KEYS[index % 8]}Color"
            expected = tuple(int(color[position : position + 2], 16) / 255 for position in (1, 3, 5)) + (1.0,)
            self.assertEqual(rgb(profile, name), expected)
        self.assertEqual(rgb(profile, "TextColor"), (171 / 255, 205 / 255, 239 / 255, 1.0))

    def test_unicode_name_and_cursor_fallback_and_overrides(self) -> None:
        _, profile = convert_theme(theme("Rosé Pine"))
        self.assertEqual(profile["name"], "Otty — Rosé Pine")
        self.assertEqual(rgb(profile, "CursorColor"), rgb(profile, "TextColor"))
        data = theme()
        data["terminal"]["cursor"] = "#010203"
        data["cursor"] = {"color": "#aabbcc"}
        _, profile = convert_theme(data)
        self.assertEqual(rgb(profile, "CursorColor"), (170 / 255, 187 / 255, 204 / 255, 1.0))
        data["selection"] = {"background": "#778899"}
        _, profile = convert_theme(data)
        self.assertEqual(rgb(profile, "SelectionColor"), (119 / 255, 136 / 255, 153 / 255, 1.0))

    def test_legacy_selection_and_transparent_background(self) -> None:
        data = theme("Clear", "none")
        data["meta"]["mode"] = "light"
        data["terminal"]["selection-background"] = "#010203"
        _, profile = convert_theme(data)
        self.assertEqual(profile["BackgroundAlpha"], 0.0)
        self.assertEqual(rgb(profile, "BackgroundColor"), (1.0, 1.0, 1.0, 0.0))
        self.assertEqual(rgb(profile, "SelectionColor"), (1 / 255, 2 / 255, 3 / 255, 1.0))

    def test_invalid_colors_palette_mode_names_and_inheritance(self) -> None:
        for mutation in (
            lambda data: data["terminal"].update(foreground="red"),
            lambda data: data["terminal"].update(palette=COLORS[:-1]),
            lambda data: data["meta"].update(mode="auto"),
            lambda data: data["meta"].update(inherits="base"),
            lambda data: data.update(inherits="base"),
            lambda data: data["meta"].update(name="../unsafe"),
        ):
            data = theme()
            mutation(data)
            with self.subTest(data=data), self.assertRaises(ThemeError):
                convert_theme(data)

    def test_snapshot_inventory_hashes_and_generated_colors(self) -> None:
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / "manifest.json").read_text())
        rows = manifest["themes"]
        self.assertEqual(len(rows), 25)
        self.assertEqual(sorted(row["name"] for row in rows), manifest["builtin_theme_names"])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            paths = convert(root / "sources", output)
            self.assertEqual(len(paths), 25)
            first = {path.name: path.read_bytes() for path in paths}
            for row in rows:
                raw = (root / "sources" / row["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["snapshot_sha256"])
                source = tomllib.loads(raw.decode())
                profile = plistlib.loads(first[f'{row["name"]}.terminal'])
                self.assertEqual(profile["name"], f'Otty — {row["name"]}')
                for index, color in enumerate(source["terminal"]["palette"]):
                    key = f"ANSI{'Bright' if index >= 8 else ''}{KEYS[index % 8]}Color"
                    expected = tuple(int(color[p:p + 2], 16) / 255 for p in (1, 3, 5)) + (1.0,)
                    self.assertEqual(rgb(profile, key), expected)
                    self.assertEqual(plistlib.loads(profile[key])["$objects"][1]["NSColorSpace"], 2)
            convert(root / "sources", output)
            self.assertEqual(first, {path.name: path.read_bytes() for path in paths})

    def test_missing_selection_and_dark_transparency(self) -> None:
        _, profile = convert_theme(theme(background="none"))
        self.assertNotIn("SelectionColor", profile)
        self.assertEqual(rgb(profile, "BackgroundColor"), (0.0, 0.0, 0.0, 0.0))
        self.assertEqual(profile["BackgroundAlpha"], 0.0)

    def test_directory_validation_has_no_partial_outputs_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / "in", root / "out"
            source.mkdir()
            (source / "valid.ottytheme").write_text(
                '[meta]\nname="Good"\nmode="dark"\n[terminal]\nforeground="#ffffff"\nbackground="#000000"\npalette=['
                + ",".join(f'"{color}"' for color in COLORS)
                + "]\n",
                encoding="utf-8",
            )
            (source / "bad.ottytheme").write_text("not = [valid toml", encoding="utf-8")
            with self.assertRaises(ThemeError):
                convert(source, output)
            self.assertFalse(output.exists())
            (source / "bad.ottytheme").unlink()
            paths = convert(source, output)
            first = paths[0].read_bytes()
            convert(source, output)
            self.assertEqual(paths[0].read_bytes(), first)
            self.assertEqual(plistlib.loads(first)["name"], "Otty — Good")


if __name__ == "__main__":
    unittest.main()

"""Tests for Otty to iTerm2 preset conversion."""

import hashlib
import json
import plistlib
import tempfile
import tomllib
import unittest
from pathlib import Path

from otty_to_iterm2 import ThemeError, convert, convert_theme


PALETTE = [f"#{index:02x}{index + 16:02x}{index + 32:02x}" for index in range(16)]


def theme(name: str = "Synthetic", background: str = "#123456") -> dict:
    return {
        "meta": {"name": name, "mode": "dark"},
        "terminal": {"foreground": "#abcdef", "background": background, "palette": PALETTE.copy()},
    }


def rgb(preset: dict, key: str) -> tuple[float, float, float, float]:
    color = preset[key]
    assert color["Color Space"] == "sRGB"
    return tuple(color[f"{channel} Component"] for channel in ("Red", "Green", "Blue", "Alpha"))


class Iterm2ConverterTests(unittest.TestCase):
    def test_palette_mapping_rgba_and_srgb_schema(self) -> None:
        data = theme()
        data["terminal"]["foreground"] = "#abcdef80"
        _, preset = convert_theme(data)
        self.assertEqual(len(preset), 20)
        for index, value in enumerate(PALETTE):
            expected = tuple(int(value[pos:pos + 2], 16) / 255 for pos in (1, 3, 5)) + (1.0,)
            self.assertEqual(rgb(preset, f"Ansi {index} Color"), expected)
        self.assertEqual(rgb(preset, "Foreground Color"), (171 / 255, 205 / 255, 239 / 255, 128 / 255))
        self.assertEqual(set(preset["Foreground Color"]), {
            "Color Space", "Red Component", "Green Component", "Blue Component", "Alpha Component"
        })

    def test_unicode_name_and_overrides_and_absent_optional_colors(self) -> None:
        name, preset = convert_theme(theme("Rosé Pine"))
        self.assertEqual(name, "Rosé Pine")
        self.assertNotIn("Selection Color", preset)
        self.assertNotIn("Selected Text Color", preset)
        self.assertNotIn("Cursor Text Color", preset)
        data = theme()
        data.update(cursor={"color": "#010203", "text": "#040506"},
                    selection={"background": "#070809", "foreground": "#0a0b0c"})
        _, preset = convert_theme(data)
        self.assertEqual(rgb(preset, "Cursor Color"), (1 / 255, 2 / 255, 3 / 255, 1.0))
        self.assertEqual(rgb(preset, "Cursor Text Color"), (4 / 255, 5 / 255, 6 / 255, 1.0))
        self.assertEqual(rgb(preset, "Selection Color"), (7 / 255, 8 / 255, 9 / 255, 1.0))
        self.assertEqual(rgb(preset, "Selected Text Color"), (10 / 255, 11 / 255, 12 / 255, 1.0))
        with tempfile.TemporaryDirectory() as directory:
            # Verify the output filename preserves Unicode theme names.
            source = Path(directory) / "theme.ottytheme"
            source.write_text('[meta]\nname="Rosé Pine"\nmode="dark"\n[terminal]\nforeground="#ffffff"\nbackground="#000000"\npalette=[' + ",".join(f'"{c}"' for c in PALETTE) + "]\n", encoding="utf-8")
            outputs = convert(source, Path(directory) / "out")
            self.assertEqual(outputs[0].name, "Otty - Rosé Pine.itermcolors")

    def test_none_background_is_opaque_mode_fallback(self) -> None:
        for mode, expected in (("dark", 0.0), ("light", 1.0)):
            data = theme(background="none")
            data["meta"]["mode"] = mode
            _, preset = convert_theme(data)
            self.assertEqual(rgb(preset, "Background Color"), (expected, expected, expected, 1.0))

    def test_invalid_inputs_and_batch_validation(self) -> None:
        mutations = (
            lambda d: d["terminal"].update(foreground="red"),
            lambda d: d["terminal"].update(palette=PALETTE[:-1]),
            lambda d: d["meta"].update(name="../unsafe"),
            lambda d: d["meta"].update(mode="auto"),
            lambda d: d["meta"].update(inherits="base"),
            lambda d: d.update(inherits="base"),
        )
        for mutate in mutations:
            data = theme()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ThemeError):
                convert_theme(data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "sources", root / "out"
            source.mkdir()
            valid = '[meta]\nname="Good"\nmode="dark"\n[terminal]\nforeground="#ffffff"\nbackground="#000000"\npalette=[' + ",".join(f'"{c}"' for c in PALETTE) + "]\n"
            (source / "good.ottytheme").write_text(valid, encoding="utf-8")
            (source / "bad.ottytheme").write_text(valid.replace('name="Good"', 'name="../bad"'), encoding="utf-8")
            with self.assertRaises(ThemeError):
                convert(source, output)
            self.assertFalse(output.exists())
            (source / "bad.ottytheme").write_text(valid.replace('name="Good"', 'name="good"'), encoding="utf-8")
            with self.assertRaises(ThemeError):
                convert(source, output)
            self.assertFalse(output.exists())

    def test_all_snapshots_manifest_hashes_colors_and_determinism(self) -> None:
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / "manifest.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            paths = convert(root / "sources", output)
            self.assertEqual(len(paths), 25)
            first = {path.name: path.read_bytes() for path in paths}
            for row in manifest["themes"]:
                raw = (root / "sources" / row["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["snapshot_sha256"])
                source = tomllib.loads(raw.decode())
                preset = plistlib.loads(first[f'Otty - {row["name"]}.itermcolors'])
                self.assertEqual(set(preset), {f"Ansi {i} Color" for i in range(16)} | {
                    "Foreground Color", "Background Color", "Bold Color", "Cursor Color"
                } | ({"Selection Color"} if source["terminal"].get("selection-background") else set())
                | ({"Selected Text Color"} if source["terminal"].get("selection-foreground") else set())
                | ({"Cursor Text Color"} if source["terminal"].get("cursor-text") else set()))
                for index, value in enumerate(source["terminal"]["palette"]):
                    expected = tuple(int(value[pos:pos + 2], 16) / 255 for pos in (1, 3, 5)) + (1.0,)
                    self.assertEqual(rgb(preset, f"Ansi {index} Color"), expected)
            convert(root / "sources", output)
            self.assertEqual(first, {path.name: path.read_bytes() for path in paths})
            checked_in = root / "iterm2"
            if checked_in.exists():
                self.assertEqual(first, {path.name: path.read_bytes() for path in checked_in.glob("*.itermcolors")})


if __name__ == "__main__":
    unittest.main()

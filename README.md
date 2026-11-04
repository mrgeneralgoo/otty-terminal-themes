# Otty → macOS Terminal / iTerm2

标准库实现的本地转换器，将仓库 `sources/` 中的 Otty `.ottytheme`（TOML）快照转换为 macOS Terminal `.terminal` 配置文件和 iTerm2 `.itermcolors` 配色预设。当前仓库包含 25 个主题快照及 `manifest.json`。请阅读 `NOTICE.md` 了解来源和版权说明。程序只读取命令行指定的源文件或目录，不会扫描其他 Otty 配置目录、联网或上传数据。

## 安装已生成的主题

两种格式均包含全部 25 个主题（9 个浅色、16 个深色），安装不需要 Python：

- `themes/`：macOS Terminal 的 `.terminal` 文件。
- `iterm2/`：iTerm2 的 `.itermcolors` 文件。

### macOS Terminal

在 Finder 中双击主题文件，或在仓库目录运行：

```sh
open "themes/Nord.terminal"
```

然后在 Terminal → 设置 → 描述文件中选择导入的 `Otty — Nord`；如果希望默认使用它，再手动设为默认。也可从描述文件列表底部的操作菜单导入其他主题。本仓库不会自动更改默认描述文件。

### iTerm2

1. 打开 **iTerm2 → Settings → Profiles → Colors → Color Presets → Import**。
2. 选择 `iterm2/` 中的 `.itermcolors` 文件，可一次选择多个。
3. 在 **Color Presets** 菜单中选择导入的预设，例如 `Otty - Nord`。导入只添加预设，需要手动选择才能应用。

iTerm2 的预设名取自文件名，因此增加 `Otty - ` 前缀以方便辨认。这些是颜色预设，不会替换字体、启动命令或整套 Profile。

这些配色来自 Otty 1.6.2 的主题文件，包含可能的个人修改，不保证等同于未经修改的出厂配色。

## 用法

需要 Python 3.11 或更高版本（使用标准库 `tomllib`）。重新生成仓库内全部 25 个配置：

```sh
python3.14 otty_to_terminal.py sources themes
python3.14 otty_to_iterm2.py sources iterm2
```

也可指定单个文件或其他主题目录。单文件示例：

```sh
python3 otty_to_terminal.py /path/to/theme.ottytheme /path/to/terminal-profiles
```

转换目录中的所有 `*.ottytheme` 文件：

```sh
python3 otty_to_terminal.py /path/to/themes /path/to/terminal-profiles
```

确认输出后，在 Terminal 中通过“设置 → 描述文件 → 操作菜单 → 导入描述文件”导入生成的 `.terminal` 文件。

## 映射与限制

### macOS Terminal

`terminal.foreground` 映射为 `TextColor` 和 `TextBoldColor`；`terminal.background` 映射为 `BackgroundColor`；`terminal.palette` 中 16 项按索引映射为 ANSI 黑、红、绿、黄、蓝、品红、青、白，再映射为对应的亮色；光标颜色优先使用 `cursor.color`，其次 `terminal.cursor`，否则回退到前景色。只在明确提供 `selection.background` 或 `terminal.selection-background` 时生成选择色。

颜色必须为 `#RRGGBB` 或 `#RRGGBBAA`，调色板必须恰有 16 色；模式仅接受 `dark` 或 `light`。不支持继承主题。`background = "none"` 会设置透明背景，并为深色主题使用黑色、浅色主题使用白色作为透明 RGB 底色；macOS Terminal 的背景模糊、材质及桌面合成效果无法由颜色配置复现。字体、窗口外观、光标文字色、选区前景色及其他 UI 设置不映射。每个输入全部验证成功后才写出文件，重名会报错。

### iTerm2

- `terminal.palette[0..15]` → `Ansi 0 Color` 至 `Ansi 15 Color`，顺序和颜色保持一致。
- 前景、背景、粗体、光标 → `Foreground Color`、`Background Color`、`Bold Color`、`Cursor Color`；粗体色使用前景色，未指定光标色时也回退到前景色。
- 显式选区背景、选区前景、光标文字色 → `Selection Color`、`Selected Text Color`、`Cursor Text Color`。优先使用 `[selection]` / `[cursor]` 的字段，再使用 `[terminal]` 对应字段；未指定的可选项不写入预设，由 iTerm2 决定。
- 颜色采用 sRGB 的 RGBA 分量字典，不使用 Terminal 的 NSColor 归档。
- `.itermcolors` 不是完整 Profile，不能用它完整复刻 Otty 的玻璃材质或窗口透明度。`background = "none"` 的 Glass Dark / Glass Light 分别输出不透明黑色 / 白色基色；如需透明效果，请在 **Profiles → Window → Transparency** 中手动调整，也可按需开启 Blur。即使显式颜色包含 alpha，也不要将其等同于窗口透明度。
- 不覆盖字体、窗口布局和启动命令，不修改既有 Terminal 主题。

格式及使用方式参考 [iTerm2 Colors 文档](https://iterm2.com/documentation-preferences-profiles-colors.html)、[Window 文档](https://iterm2.com/documentation-preferences-profiles-window.html) 和 [官方配色预设](https://github.com/gnachman/iTerm2/blob/master/plists/ColorPresets.plist)。

仓库内快照仅用于个人主题转换，`NOTICE.md` 记录相关来源与版权信息，本转换器不改变主题原有授权。

## 验证

```sh
python3.14 -m unittest -v
find themes -name '*.terminal' -exec plutil -lint {} +
find iterm2 -name '*.itermcolors' -exec plutil -lint {} +
```

测试覆盖 ANSI 顺序、Unicode 名称、光标/选区回退、透明背景、无效输入、快照哈希、25 个主题的完整性和可重复生成。Terminal 版本此前还通过 macOS AppKit 原生解码独立核对了 509 个颜色值；iTerm2 版本按官方预设格式检查 sRGB/RGBA 字段并与源快照逐色比对。

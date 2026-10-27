# Otty → macOS Terminal

标准库实现的本地转换器，将仓库 `sources/` 中的 Otty `.ottytheme`（TOML）快照转换为 macOS Terminal `.terminal` 配置文件。当前仓库包含 25 个主题快照及 `manifest.json`。这些是本地快照，可能经过用户定制；请阅读 `NOTICE.md` 了解来源和版权说明。程序只读取命令行指定的源文件或目录，不会扫描其他 Otty 配置目录、联网或上传数据。

## 安装已生成的主题

`themes/` 已包含全部 25 个可直接使用的 `.terminal` 文件（9 个浅色、16 个深色），安装不需要 Python。

在 Finder 中双击主题文件，或在仓库目录运行：

```sh
open "themes/Nord.terminal"
```

然后在 Terminal → 设置 → 描述文件中选择导入的 `Otty — Nord`；如果希望默认使用它，再手动设为默认。也可从描述文件列表底部的操作菜单导入其他主题。本仓库不会自动更改默认描述文件。

这些配色来自 Otty 1.6.2 的本机主题文件，包含可能的个人修改，不保证等同于未经修改的出厂配色。仓库保持 **PRIVATE**，仅供个人使用。

## 用法

需要 Python 3.11 或更高版本（使用标准库 `tomllib`）。重新生成仓库内全部 25 个配置：

```sh
python3.14 otty_to_terminal.py sources themes
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

`terminal.foreground` 映射为 `TextColor` 和 `TextBoldColor`；`terminal.background` 映射为 `BackgroundColor`；`terminal.palette` 中 16 项按索引映射为 ANSI 黑、红、绿、黄、蓝、品红、青、白，再映射为对应的亮色；光标颜色优先使用 `cursor.color`，其次 `terminal.cursor`，否则回退到前景色。只在明确提供 `selection.background` 或 `terminal.selection-background` 时生成选择色。

颜色必须为 `#RRGGBB` 或 `#RRGGBBAA`，调色板必须恰有 16 色；模式仅接受 `dark` 或 `light`。不支持继承主题。`background = "none"` 会设置透明背景，并为深色主题使用黑色、浅色主题使用白色作为透明 RGB 底色；macOS Terminal 的背景模糊、材质及桌面合成效果无法由颜色配置复现。字体、窗口外观、光标文字色、选区前景色及其他 UI 设置不映射。每个输入全部验证成功后才写出文件，重名会报错。

仓库内快照仅用于个人主题转换；如果你将其公开发布或重新分发，请先核实来源和许可。`NOTICE.md` 记录相关来源与版权信息。本转换器不改变主题原有授权，也不会访问或导出本机其他用户配置。

## 验证

```sh
python3.14 -m unittest -v
find themes -name '*.terminal' -exec plutil -lint {} +
```

测试覆盖 ANSI 顺序、Unicode 名称、光标/选区回退、透明背景、无效输入、快照哈希、25 个主题的完整性和可重复生成。本次生成还通过 macOS AppKit 原生解码独立核对了 509 个颜色值。未自动导入 Terminal，也未进行逐主题视觉截图比对。

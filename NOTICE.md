# 来源与使用范围

此仓库用于仓库所有者的个人使用，保持 **PRIVATE**。私有存储不改变原始主题的权利归属；不要据此将主题重新公开发布或宣称拥有其版权。本仓库未对 Otty 主题授予新的开源许可证。

## 快照

- 来源：本机 Otty 1.6.2 的 25 个 `.ottytheme` 文件。
- `sources/` 仅保留主题名称、明暗类型、终端前景/背景、ANSI 调色板及光标/选区颜色；不包含应用主配置、历史记录、密钥、字体或其他界面资源。
- 文件可能包含本机的个人修改；不是经过逐色比对的出厂默认主题。25 个主题名称与该版本 CLI 的内置主题列表逐一对应。
- `manifest.json` 记录源文件 SHA-256 和精简后快照 SHA-256。原始完整文件不上传。
- `.terminal` 文件是这些配色的格式转换；Terminal 无法复刻 Otty 的窗口材质、卡片、边框和全部选区/光标行为。

## Otty 的主题鸣谢

Otty 安装包的 `CREDITS.md` 在 “Built-in Themes” 节中列出以下来源。这些是 Otty 的鸣谢，不表示其中任意许可证自动覆盖全部主题，也不是将同名上游主题替换为本地快照的依据。

- Ayu — dempfi — https://github.com/dempfi/ayu
- Catppuccin — Catppuccin community — https://catppuccin.com
- Dracula — Dracula family — https://draculatheme.com
- Gruvbox — morhetz — https://github.com/morhetz/gruvbox
- Monokai — Wimer Hazenberg
- Night — Typora — https://typora.io
- Night Owl — Sarah Drasner — https://github.com/sdras/night-owl-vscode-theme
- Nord — arcticicestudio — https://www.nordtheme.com
- One Dark / One Light — Atom — https://github.com/atom/atom
- Rosé Pine — Rosé Pine community — https://rosepinetheme.com
- Solarized — Ethan Schoonover
- Tokyo Night — https://github.com/folke/tokyonight.nvim

Otty: https://otty.sh/

许可协议：https://docs.otty.sh/license

主题文档：https://docs.otty.sh/customization/themes

主题格式：https://docs.otty.sh/reference/theme-format

官方鸣谢：https://docs.otty.sh/reference/credits

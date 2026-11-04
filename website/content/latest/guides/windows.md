# Windows and WSL

hueman runs inside WSL and writes to the Windows disk through `/mnt/c`. That
covers theming Windows Terminal, WezTerm, qutebrowser, the taskbar (via
Windhawk), YASB, and Flow Launcher. This guide shows the patterns.

![YASB bar, WezTerm and Flow Launcher on a Windows desktop, all themed by one hueman palette](assets/img/windows-desktop.webp)

YASB (top), WezTerm and Flow Launcher, all painted from one palette.

## Paths in `outputs`

Windows paths appear from WSL as `/mnt/c/Users/<user>/...`. To avoid repeating
them, define a variable in `vars` (see [Variables](../configuration.md#variables)):

```yaml
vars:
  win_home: "/mnt/c/Users/<user>"
```

`${win_home}` is substituted in `outputs` and `skip_unless_path_exists`, but not
in `reload`, `post_apply`, or patch markers. `~` also works in those paths
(there it is the WSL home, not Windows). `--var win_home=...` can override from
the command line.

## Windows Terminal

`json_scheme_upsert` strategy: insert or update a scheme inside `settings.json`
from the palette's `kitty` section, with no template.

```yaml
targets:
  windows_terminal:
    mode: patch
    palette_key: kitty
    outputs:
      - "${win_home}/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
    patch:
      strategy: json_scheme_upsert
      palette_section: kitty
      scheme_name: Dotfiles
```

`scheme_name` is the scheme name (default `Dotfiles`). Assign it once in
Windows Terminal (`"colorScheme": "Dotfiles"` on the profile); after that every
`hueman set` updates it. The file must exist and be valid JSON.

## WezTerm

Uses the packaged template `wezterm_colors.lua.j2` (`kitty` section), which
defines `config.colors = { ... }`. `patch` mode with `marker_begin`/`marker_end`:

```yaml
targets:
  wezterm_windows:
    template: wezterm_colors.lua.j2
    mode: patch
    palette_key: kitty
    outputs:
      - "${win_home}/.wezterm.lua"
    patch:
      marker_begin: "-- BEGIN hueman managed colors"
      marker_end: "-- END hueman managed colors"
```

Markers are text you choose; they only need to match between the config and
`.wezterm.lua`. hueman replaces everything between them. Patch mode never
creates files: `.wezterm.lua` must exist. If the markers are missing, the block
is appended at the end of the file, which can land after `return config`; the
usual approach is to place both markers by hand in the right spot, before the
`return`:

```lua
-- BEGIN hueman managed colors
-- END hueman managed colors
```

## qutebrowser on Windows

Overwrite of the generated theme, guarded by `skip_if_missing_parent`: if the
directory does not exist (qutebrowser not installed or without that folder) it
is skipped without error.

```yaml
targets:
  qutebrowser_windows:
    template: qutebrowser_theme.py.j2
    mode: overwrite
    palette_key: polybar
    skip_if_missing_parent: true
    outputs:
      - "${win_home}/AppData/Roaming/qutebrowser/config/modules/themes/current.py"
```

Your qutebrowser `config.py` must import that module.

## Taskbar with Windhawk

Windhawk's `windows-11-taskbar-styler` mod stores colors in the registry
(`HKLM`), which WSL cannot write. The fix is two parts:

1. hueman writes a JSON with `fill` and `text` (template
   `windhawk_taskbar.json.j2`, `polybar` section: `background` and `primary`).
2. A Windows scheduled task with elevated privileges reads that JSON and
   applies the colors. A task is used because `schtasks.exe /run` can launch it
   from WSL without a UAC prompt; elevation is granted once when installing it.

```yaml
targets:
  windhawk_taskbar:
    template: windhawk_taskbar.json.j2
    mode: overwrite
    palette_key: polybar
    skip_if_missing_parent: true
    skip_unless_path_exists: /mnt/c/Windows/System32/schtasks.exe
    outputs:
      - "${win_home}/AppData/Local/DotfilesTheme/taskbar-colors.json"
    reload: "schtasks.exe /run /tn <TaskName> >/dev/null 2>&1 || true"
```

- `skip_unless_path_exists` skips the whole target outside WSL.
- `reload` runs only after an effective write; with `|| true` it is
  best-effort even if the task is not installed (see also `reload_failure` in
  [Configuration](../configuration.md)).

One-time task install, from an Administrator PowerShell, with the repo examples
([`examples/windows/`](https://github.com/NeanderTeam/hueman/tree/main/examples/windows))
(`install-windhawk-taskbar-task.ps1` and `windhawk-taskbar-apply.ps1`, same
folder):

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windhawk-taskbar-task.ps1 -TaskName <TaskName>
```

The default task name is `DotfilesThemeWindhawk` and the default JSON lives at
`$env:LOCALAPPDATA\DotfilesTheme\taskbar-colors.json`; if you change either
(`-TaskName`, `-DataFile`), adjust the target to match. The scripts are
examples to adapt and were not tested on Windows; read them before use.

## YASB

[YASB](https://github.com/amnweb/yasb) is a Qt status bar that also hosts the
system tray. hueman only owns the `:root { ... }` variables block of its
`styles.css`; widgets and the rest of the CSS stay yours. Template
`yasb_root.css.j2` (`polybar` section, plus `kitty` border colors).

```yaml
targets:
  yasb_theme:
    template: yasb_root.css.j2
    palette_key: polybar
    extra_vars:
      border_active: kitty.active_border_color
      border_inactive: kitty.inactive_border_color
    mode: patch
    outputs:
      - "${win_home}/.config/yasb/styles.css"
    skip_unless_path_exists: "${win_home}/.config/yasb/styles.css"
    patch:
      strategy: regex_splice
      marker_regex: ':root\s*\{.*?\}'
```

- Patch mode never creates files: run YASB's wizard first so `styles.css`
  exists. Otherwise the target is skipped.
- No `reload` needed: with `watch_stylesheet: true` (the wizard default) YASB
  reloads on file change.
- Keep `}` out of the generated block (comments included): `marker_regex` is
  non-greedy and would stop there.
- Transparencies are written as `rgba(r, g, b, a)`, never `#rrggbbaa`: Qt reads
  8-digit hex as `#AARRGGBB`.
- Besides the `--yasb-*` variables, the block defines `--hueman-border` and
  `--hueman-border-active`, so hand-written CSS can use palette colors.

Add the systray styling once, at the end of your `styles.css` (outside the
`:root` block). It only uses variables, so it follows every `hueman set`:

```css
/* systray */
.systray { background: transparent; border: none; margin: 0 6px; }
.systray .unpinned-container,
.systray .pinned-container { background: transparent; }
.systray .pinned-container[forceshow=true] {
    background-color: var(--yasb-white-alpha-10);
    border-radius: 4px;
}
.systray .button { border-radius: 4px; padding: 2px; }
.systray .button:hover,
.systray .unpinned-visibility-btn:hover { background-color: var(--yasb-white-alpha-10); }
.systray .unpinned-visibility-btn { border-radius: 4px; padding: 0 4px; color: var(--yasb-icon-fg); }
.systray-popup {
    background-color: var(--yasb-popup-bg);
    border: 1px solid var(--hueman-border-active);
    padding: 6px;
}
/* line between the bar and the windows (use border-top if the bar is at the bottom) */
.yasb-bar { border-bottom: 1px solid var(--hueman-border); }
```

Related notes:

- **WezTerm fullscreen:** with the bar on top, `toggle_fullscreen()` in
  `gui-startup` covers YASB, because WezTerm fullscreen takes the whole monitor
  and ignores the work area. Use `window:gui_window():maximize()` plus
  `config.window_decorations = "RESIZE"` (F11 still gives real fullscreen).
  Remember that the `wezterm_windows` target redeploys your `.wezterm.lua` on
  each `set`, so make the change in the source file, not in a copy on `C:\`.
- **`windhawk_taskbar`:** if you hide the native taskbar and use YASB, that
  target recolors a taskbar you no longer see; consider removing it.
- **Hiding the taskbar:** the Windhawk `taskbar-auto-hide-keyboard-only` mod
  needs the native auto-hide enabled (Settings > Personalization > Taskbar).
- **Systray limits** (from the YASB docs): apps that ignore `TaskbarCreated`
  do not appear, some apps opened before YASB ignore clicks, and
  `use_hook: true` injects a DLL into `explorer.exe` (YASB falls back to legacy
  mode if an antivirus blocks it).

## Flow Launcher

[Flow Launcher](https://www.flowlauncher.com/) themes are WPF `ResourceDictionary`
files. hueman writes its own theme, `Hueman.xaml`, in the user themes folder and
never touches the themes that ship with Flow. Template
`flowlauncher_theme.xaml.j2` (`polybar` section, plus `kitty.active_border_color`
for the window border).

```yaml
targets:
  flowlauncher_theme:
    template: flowlauncher_theme.xaml.j2
    palette_key: polybar
    extra_vars:
      border_active: kitty.active_border_color
    mode: overwrite
    outputs:
      - "${win_home}/AppData/Roaming/FlowLauncher/Themes/Hueman.xaml"
    skip_unless_path_exists: "${win_home}/AppData/Roaming/FlowLauncher/Themes"
```

- **Select the theme manually, once:** Settings > Appearance > Theme > `Hueman`.
  Editing `Settings.json` does not work while Flow is open, because Flow
  rewrites it on exit.
- **No automatic reload:** Flow did not pick up a rewritten `.xaml` on its own.
  After `hueman set`, select the theme again or restart Flow. The target has no
  `reload` on purpose; restarting Flow on every `set` would close it while you
  use it.
- The theme header declares `IsDark` from the palette background, so light
  palettes are flagged correctly in Flow's theme list.

## Telegram

hueman can also theme Telegram on Android: the packaged template
`telegram.attheme.j2` renders a `.attheme` from the palette, and a reload
command pushes it to a Telegram cloud theme that your devices sync by
themselves. Uploading needs Telethon and a user session, which hueman does not
install or ship. A sanitized script, setup steps, known limits and the Terms of
Service note live in
[`examples/telegram/`](https://github.com/NeanderTeam/hueman/tree/main/examples/telegram);
the matching `telegram_theme` target is commented out in
`hueman/data/hueman.config.example.yaml`. It is an example to adapt and was not
tested on a device from this repo.

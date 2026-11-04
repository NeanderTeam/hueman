# Windows examples

Example PowerShell scripts for using hueman from WSL on Windows. They are
starting points to adapt, not part of the product. The full guide is in
`website/content/latest/guides/windows.md` ("Windows and WSL").

| File | Purpose |
|------|---------|
| `install-windhawk-taskbar-task.ps1` | One-time install (PowerShell as Administrator): copies the apply script to `$env:ProgramData\DotfilesTheme` and registers the elevated scheduled task `DotfilesThemeWindhawk`. `-Uninstall` removes it. |
| `windhawk-taskbar-apply.ps1` | Run by the task: reads `taskbar-colors.json` (`fill`, `text`) and updates the colors of Windhawk's `windows-11-taskbar-styler` mod. It only reloads the mod if something changed. |

## Usage

From an elevated PowerShell, in the folder with both files:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windhawk-taskbar-task.ps1
```

Options: `-TaskName <TaskName>` and `-DataFile <PATH>`. By default the JSON
file is `$env:LOCALAPPDATA\DotfilesTheme\taskbar-colors.json`; the hueman target
must write there (`/mnt/c/Users/<user>/AppData/Local/DotfilesTheme/...`).

## Security

- The apply script lives in a `ProgramData` folder that only SYSTEM and
  Administrators can write to (users get read and execute).
- The JSON file, which the user can write to, is treated only as data: every
  value must match `^#[0-9A-Fa-f]{6}$` or the script aborts without changes.
- It only touches values under the mod's settings key and its `Disabled` flag.

## Notice

These scripts were not tested in this repository (there is no PowerShell or
Windows in the development environment). Read them and test them carefully
before use.

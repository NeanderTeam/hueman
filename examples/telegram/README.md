# Example: sync the Telegram theme (Android)

Example script for using hueman with Telegram. It is a starting point to adapt,
not part of the product: it is not included in the pip package and hueman does
not depend on Telethon. It has not been tested on a device from this repo;
review the script before running it.

`hueman set <palette>` regenerates a Telegram Android `.attheme` theme from the
active palette and uploads it to a **cloud theme**. Devices that already applied
that theme pick it up on their own; after the first time there is nothing to
import by hand.

```
hueman set <palette>
  └─ target telegram_theme
       ├─ telegram.attheme.j2 (packaged)  →  current.attheme
       └─ reload: telegram-theme-sync current.attheme  (background, 60 s)
                    └─ Telethon (MTProto user session) → account.updateTheme
```

Why a cloud theme: Android cannot apply a theme from another app (there is no
intent or API), and a `.attheme` sent to a chat asks you to tap "Apply" every
time. A cloud theme (`t.me/addtheme/<slug>`) is synced by Telegram itself, so
editing it on the server updates every device that applied it.

## Files

| Path | What it is for |
|------|----------------|
| `telegram-theme-sync` | Telethon script in this folder: uploads the file and updates the cloud theme. |
| `hueman/templates/telegram.attheme.j2` | Packaged template: palette → `.attheme` keys (signed ARGB integers, converted in Jinja). |
| `hueman.config.example.yaml` → `telegram_theme` | Commented target: renders the template and triggers the upload. |
| `~/.config/hueman/telegram.env` | `TG_API_ID`, `TG_API_HASH` and optionally `TG_THEME_SLUG` (mode 600, kept out of git). |
| `~/.config/hueman/telegram.session` | Telethon session (mode 600, kept out of git). |

The config directory can be changed with `HUEMAN_TELEGRAM_DIR`. If
`~/.config/hueman` is a symlink to a dotfiles repo, `telegram.env` and
`telegram.session` end up inside the repo tree: add them to `.gitignore`.

## Palette mapping

The target uses `palette_key: polybar` plus `extra_vars` from `kitty`, so it
works with all 25 packaged palettes:

| Template variable | Source |
|-------------------|--------|
| `background`, `background_alt`, `foreground` | `polybar.*` |
| `primary`, `secondary`, `success`, `alert` | `polybar.*` (accents, counters, checks, errors) |
| `muted` | `polybar.muted` (secondary text and `dim`) |
| `bg0h`, `bg2` | `kitty.color0`, `kitty.inactive_border_color` |
| `blu`, `pur`, `aqu` | `kitty.color12`, `color13`, `color14` |

Secondary text (`fg2`) uses `foreground` and the greys (`dim`) use `muted`.
The template does not read the `pi` section, which belongs to another tool.

## One-time setup

1. **Create the cloud theme** in the app: Settings → Chat Settings → Theme →
   Create new theme. Note its `t.me/addtheme/<slug>` link. The account that
   runs the script must be the one that created it.
2. **Get API credentials** at https://my.telegram.org → API development
   tools → create an application (platform "Other", without "Telegram" in the
   name). Do not paste the `api_hash` anywhere shared.
3. **Store them** in `~/.config/hueman/telegram.env` and `chmod 600` it (edit it
   with an editor, not with `echo`, so it does not end up in your shell history):
   ```
   TG_API_ID=<your api_id>
   TG_API_HASH=<your api_hash>
   TG_THEME_SLUG=<theme slug>
   ```
4. **Install Telethon** in its own venv (not in hueman's environment):
   ```bash
   python3 -m venv ~/.local/share/hueman-telegram
   ~/.local/share/hueman-telegram/bin/pip install telethon
   ```
5. **Copy the script** to a path of your own and point its first line (`#!`) at
   that venv's python, for example `~/.local/bin/telegram-theme-sync`.
6. **Log in once** (interactive: your phone number with country code, the code
   Telegram sends to the app, and your 2FA password if you have one):
   ```bash
   ~/.local/bin/telegram-theme-sync --login
   ```
7. **Enable the `telegram_theme` target** in the example config (uncomment it
   and adjust `outputs` and the script path in `reload`).
8. **Apply the theme on the phone** by opening its `t.me/addtheme/<slug>` link.

## Usage

```bash
hueman set dracula                         # applies everything, including the Telegram upload
hueman set --only telegram_theme <palette> # try just this target
telegram-theme-sync something.attheme      # upload any file
```

The example's reload only runs if `telegram.session` exists, so other nodes
that run `hueman sync` skip it without noise.

## Details that cost us

- **Mime:** `account.updateTheme` rejects documents with a guessed mime
  (`ThemeMimeInvalidError`). The upload has to use
  `application/x-tgtheme-android`, which is why the script uses
  `SendMediaRequest` + `InputMediaUploadedDocument` and not `send_file`.
- **The upload goes through Saved Messages:** a message is needed to get an
  `InputDocument`; the script deletes it afterwards.
- **Session path:** Telethon already appends `.session`; `SESSION` is the full
  path of `telegram.session`.
- **Users only:** bots cannot call `account.updateTheme`.
- **ToS:** Telegram's API terms (core.telegram.org/api/terms) cover third-party
  apps and forbid acting without the user's consent or interfering with core
  features. Automating your own theme, with your own `api_id` and one call per
  palette change, falls outside what they forbid. They do not document ban
  thresholds for user accounts; use it at your own risk.

## Known limits

- The `.attheme` keys are a hand-picked subset (~140); anything not defined
  falls back to Telegram's default light values.
- Some roles map only approximately: in palettes where `background_alt` and
  `kitty.inactive_border_color` are equal, the selected incoming bubble is
  barely distinguishable from a normal one.
- iOS and Telegram Desktop use other formats (`.tgios-theme`,
  `.tdesktop-theme`); this flow is Android only.
- Importing on a device has not been tested from this repo.

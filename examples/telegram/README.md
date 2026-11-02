# Ejemplo: sincronizar el tema de Telegram (Android)

Script de ejemplo para usar hueman con Telegram. Es un punto de partida para
adaptar, no parte del producto: no se incluye en el paquete pip y hueman no
depende de Telethon. No se probó en un dispositivo desde este repo; revisa el
script antes de ejecutarlo.

`hueman set <paleta>` regenera un tema `.attheme` de Telegram Android desde la
paleta activa y lo sube a un **tema en la nube**. Los dispositivos que ya
aplicaron ese tema lo reciben solos; después de la primera vez no hay que
importar nada a mano.

```
hueman set <paleta>
  └─ target telegram_theme
       ├─ telegram.attheme.j2 (empaquetado)  →  current.attheme
       └─ reload: telegram-theme-sync current.attheme  (segundo plano, 60 s)
                    └─ Telethon (sesion de usuario MTProto) → account.updateTheme
```

Por qué un tema en la nube: Android no puede aplicar un tema desde otra app (no
hay intent ni API), y un `.attheme` enviado a un chat pide tocar "Aplicar" cada
vez. Un tema en la nube (`t.me/addtheme/<slug>`) lo sincroniza Telegram, así
que editarlo en el servidor actualiza todos los dispositivos que lo aplicaron.

## Archivos

| Ruta | Para qué |
|------|----------|
| `telegram-theme-sync` | Script Telethon de esta carpeta: sube el archivo y actualiza el tema en la nube. |
| `hueman/templates/telegram.attheme.j2` | Template empaquetado: paleta → claves `.attheme` (enteros ARGB con signo, convertidos en Jinja). |
| `hueman.config.example.yaml` → `telegram_theme` | Target comentado: renderiza el template y dispara la subida. |
| `~/.config/hueman/telegram.env` | `TG_API_ID`, `TG_API_HASH` y opcional `TG_THEME_SLUG` (modo 600, fuera de git). |
| `~/.config/hueman/telegram.session` | Sesión de Telethon (modo 600, fuera de git). |

El directorio de config se puede cambiar con `HUEMAN_TELEGRAM_DIR`. Si
`~/.config/hueman` es un symlink a un repo de dotfiles, `telegram.env` y
`telegram.session` quedan dentro del árbol del repo: agrégalos a `.gitignore`.

## Mapeo de paleta

El target usa `palette_key: polybar` más `extra_vars` de `kitty`, así que
funciona con las 25 paletas empaquetadas:

| Variable del template | Origen |
|-----------------------|--------|
| `background`, `background_alt`, `foreground` | `polybar.*` |
| `primary`, `secondary`, `success`, `alert` | `polybar.*` (acentos, contadores, checks, errores) |
| `muted` | `polybar.muted` (texto secundario y `dim`) |
| `bg0h`, `bg2` | `kitty.color0`, `kitty.inactive_border_color` |
| `blu`, `pur`, `aqu` | `kitty.color12`, `color13`, `color14` |

El texto secundario (`fg2`) usa `foreground` y los grises (`dim`) usan `muted`.
El template no lee la sección `pi`, que pertenece a otra herramienta.

## Instalación única

1. **Crea el tema en la nube** en la app: Ajustes → Ajustes del chat → Tema →
   Crear tema nuevo. Anota su enlace `t.me/addtheme/<slug>`. La cuenta que corre
   el script debe ser la creadora.
2. **Obtén credenciales de API** en https://my.telegram.org → API development
   tools → crea una aplicación (plataforma "Other", sin "Telegram" en el
   nombre). No pegues el `api_hash` en ningún lugar compartido.
3. **Guárdalas** en `~/.config/hueman/telegram.env` y ponle `chmod 600` (edítalo
   con un editor, no con `echo`, para no dejarlo en el historial del shell):
   ```
   TG_API_ID=<tu api_id>
   TG_API_HASH=<tu api_hash>
   TG_THEME_SLUG=<slug del tema>
   ```
4. **Instala Telethon** en su propio venv (no en el entorno de hueman):
   ```bash
   python3 -m venv ~/.local/share/hueman-telegram
   ~/.local/share/hueman-telegram/bin/pip install telethon
   ```
5. **Copia el script** a una ruta tuya y apunta su primera línea (`#!`) al
   python de ese venv, por ejemplo `~/.local/bin/telegram-theme-sync`.
6. **Inicia sesión una vez** (interactivo: teléfono con código de país, el
   código que Telegram manda a la app y la contraseña 2FA si la tienes):
   ```bash
   ~/.local/bin/telegram-theme-sync --login
   ```
7. **Activa el target** `telegram_theme` del config de ejemplo (descoméntalo y
   ajusta `outputs` y la ruta del script en `reload`).
8. **Aplica el tema en el teléfono** abriendo su enlace `t.me/addtheme/<slug>`.

## Uso

```bash
hueman set dracula                         # aplica todo, incluida la subida a Telegram
hueman set --only telegram_theme <paleta>  # prueba solo este target
telegram-theme-sync algo.attheme           # sube un archivo cualquiera
```

El reload del ejemplo solo corre si existe `telegram.session`, así que otros
nodos que ejecuten `hueman sync` lo omiten sin ruido.

## Detalles que costaron

- **Mime:** `account.updateTheme` rechaza documentos con mime adivinado
  (`ThemeMimeInvalidError`). Hay que subir como `application/x-tgtheme-android`,
  por eso el script usa `SendMediaRequest` + `InputMediaUploadedDocument` y no
  `send_file`.
- **La subida pasa por Saved Messages:** se necesita un mensaje para obtener un
  `InputDocument`; el script lo borra después.
- **Ruta de sesión:** Telethon ya agrega `.session`; `SESSION` es la ruta
  completa de `telegram.session`.
- **Solo usuarios:** `account.updateTheme` no lo pueden llamar los bots.
- **ToS:** los términos de la API de Telegram (core.telegram.org/api/terms)
  cubren apps de terceros y prohíben actuar sin consentimiento del usuario o
  interferir con funciones centrales. Automatizar tu propio tema, con tu propio
  `api_id` y una llamada por cambio de paleta, queda fuera de lo que prohíben.
  No documentan umbrales de baneo para cuentas de usuario; úsalo bajo tu riesgo.

## Límites conocidos

- Las claves `.attheme` son un subconjunto elegido a mano (~140); lo que no se
  define cae a los valores claros por defecto de Telegram.
- Algunos roles se mapean de forma aproximada: en paletas donde
  `background_alt` y `kitty.inactive_border_color` son iguales, la burbuja
  entrante seleccionada casi no se distingue de la normal.
- iOS y Telegram Desktop usan otros formatos (`.tgios-theme`,
  `.tdesktop-theme`); este flujo es solo Android.
- Sin probar importación en dispositivo desde este repo.

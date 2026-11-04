"""Template empaquetado telegram.attheme.j2: renderiza con todas las paletas
sin depender de la seccion `pi` (no es un contrato estable)."""
import logging
import re
from pathlib import Path

import pytest
import yaml

from hueman.engine.render import make_jinja_env, render_target
from hueman.engine.targets import Target

ROOT = Path(__file__).resolve().parent.parent
PALETTE_DIR = ROOT / "hueman" / "palettes"
TEMPLATE = ROOT / "hueman" / "templates" / "telegram.attheme.j2"
PALETTES = sorted(p.stem for p in PALETTE_DIR.glob("*.yaml"))
LINE_RE = re.compile(r"^[A-Za-z0-9_]+=-?\d+$")
logger = logging.getLogger("hueman-tests")


def _target(out):
    return Target.from_dict("telegram_theme", {
        "template": "telegram.attheme.j2",
        "palette_key": "polybar",
        "mode": "overwrite",
        "extra_vars": {
            "bg0h": "kitty.color0",
            "bg2": "kitty.inactive_border_color",
            "blu": "kitty.color12",
            "pur": "kitty.color13",
            "aqu": "kitty.color14",
        },
        "outputs": [str(out)],
    })


def _render(tmp_path, name, strip_pi=False):
    palette = yaml.safe_load((PALETTE_DIR / f"{name}.yaml").read_text())
    if strip_pi:
        palette.pop("pi", None)
    out = tmp_path / "current.attheme"
    env = make_jinja_env([], ROOT / "hueman" / "templates")
    assert render_target(env, _target(out), name, palette, False, logger) is True
    return out.read_text()


def test_template_does_not_reference_pi_vars():
    src = TEMPLATE.read_text()

    assert "pi.vars" not in src and "textMuted" not in src and "dimGray" not in src


@pytest.mark.parametrize("name", PALETTES)
def test_renders_on_every_palette_without_pi_section(name, tmp_path):
    text = _render(tmp_path, name, strip_pi=True)
    lines = [ln for ln in text.splitlines() if ln.strip()]

    assert len(lines) > 100
    assert all(LINE_RE.match(ln) for ln in lines), [ln for ln in lines if not LINE_RE.match(ln)][:3]
    assert "windowBackgroundWhite=" in text and "chat_inBubble=" in text


def test_argb_conversion_is_signed_32_bit(tmp_path):
    palette = yaml.safe_load((PALETTE_DIR / "dracula.yaml").read_text())
    text = _render(tmp_path, "dracula")
    bg = palette["polybar"]["background"].lstrip("#")  # #282a36
    expected = int("ff" + bg, 16) - 2**32
    values = dict(ln.split("=") for ln in text.splitlines() if ln)

    assert int(values["windowBackgroundWhite"]) == expected
    assert all(-2**31 <= int(v) < 2**31 for v in values.values())


def test_render_is_deterministic(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()

    assert _render(tmp_path / "a", "nord") == _render(tmp_path / "b", "nord")

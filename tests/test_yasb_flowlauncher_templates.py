"""Templates empaquetados de YASB (patch del bloque :root) y Flow Launcher
(tema XAML). Todo en tmp_path: nunca se toca el home real."""
import logging
import re
import xml.dom.minidom
from pathlib import Path

import pytest
import yaml

from hueman.engine.colors import is_dark
from hueman.engine.render import make_jinja_env, render_target, render_template
from hueman.engine.targets import Target

ROOT = Path(__file__).resolve().parent.parent
PALETTE_DIR = ROOT / "hueman" / "palettes"
PALETTES = sorted(p.stem for p in PALETTE_DIR.glob("*.yaml"))
ROOT_RE = re.compile(r":root\s*\{.*?\}", re.DOTALL)
logger = logging.getLogger("hueman-tests")


def _palette(name):
    return yaml.safe_load((PALETTE_DIR / f"{name}.yaml").read_text())


def _env():
    return make_jinja_env([], ROOT / "hueman" / "templates")


def _yasb_target(out):
    return Target.from_dict("yasb_theme", {
        "template": "yasb_root.css.j2",
        "palette_key": "polybar",
        "extra_vars": {
            "border_active": "kitty.active_border_color",
            "border_inactive": "kitty.inactive_border_color",
        },
        "mode": "patch",
        "outputs": [str(out)],
        "skip_unless_path_exists": str(out),
        "patch": {"strategy": "regex_splice", "marker_regex": r":root\s*\{.*?\}"},
    })


def _flow_target(out):
    return Target.from_dict("flowlauncher_theme", {
        "template": "flowlauncher_theme.xaml.j2",
        "palette_key": "polybar",
        "extra_vars": {"border_active": "kitty.active_border_color"},
        "mode": "overwrite",
        "outputs": [str(out)],
    })


def _rendered(target, name):
    return render_template(_env(), target, name, _palette(name))


@pytest.mark.parametrize("name", PALETTES)
def test_yasb_block_is_a_single_root_without_inner_brace(name, tmp_path):
    text = _rendered(_yasb_target(tmp_path / "styles.css"), name)

    assert ROOT_RE.fullmatch(text.strip())
    assert "}" not in text.strip()[:-1]
    assert "{{" not in text and "{%" not in text
    assert "--yasb-accent:" in text and "--hueman-border-active:" in text


def test_yasb_uses_rgba_not_eight_digit_hex(tmp_path):
    text = _rendered(_yasb_target(tmp_path / "styles.css"), "tokyonight")

    assert "rgba(" in text
    assert not re.search(r"#[0-9a-fA-F]{8}\b", text)


def test_yasb_patch_is_idempotent_and_keeps_surrounding_rules(tmp_path):
    css = tmp_path / "styles.css"
    before = ".yasb-bar { border: 1px solid red; }\n\n"
    after = "\n.systray { margin: 0 6px; }\n"
    css.write_text(before + ":root {\n    --old: 1;\n}\n" + after)
    target = _yasb_target(css)
    palette = _palette("synthwave")

    assert render_target(_env(), target, "synthwave", palette, False, logger) is True
    first = css.read_text()
    assert render_target(_env(), target, "synthwave", palette, False, logger) is True
    second = css.read_text()

    assert first == second
    assert len(ROOT_RE.findall(second)) == 1
    assert second.startswith(before) and second.endswith(after)
    assert "--old" not in second
    assert palette["polybar"]["primary"] in second


def test_yasb_patch_on_missing_styles_creates_nothing(tmp_path):
    css = tmp_path / ".config" / "yasb" / "styles.css"
    target = _yasb_target(css)

    assert render_target(_env(), target, "dracula", _palette("dracula"), False, logger) is False
    assert not css.exists() and not css.parent.exists()


@pytest.mark.parametrize("name", PALETTES)
def test_flow_xaml_is_valid_xml_with_coherent_is_dark(name, tmp_path):
    text = _rendered(_flow_target(tmp_path / "Hueman.xaml"), name)

    dom = xml.dom.minidom.parseString(text.encode("utf-8"))
    assert dom.documentElement.tagName == "ResourceDictionary"
    expected = "True" if is_dark(_palette(name)["polybar"]["background"]) else "False"
    assert f"IsDark: {expected}" in text
    assert "{{" not in text and "{%" not in text


def test_flow_overwrite_writes_theme_file(tmp_path):
    out = tmp_path / "Themes" / "Hueman.xaml"
    target = _flow_target(out)

    assert render_target(_env(), target, "nord", _palette("nord"), False, logger) is True
    assert _palette("nord")["kitty"]["active_border_color"] in out.read_text()

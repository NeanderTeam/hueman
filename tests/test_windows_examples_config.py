"""Targets de ejemplo (YASB, Flow Launcher, Telegram) y ejemplo de Telegram:
sin rutas reales ni secretos, fuera del paquete y sin dependencias nuevas."""
import ast
import logging
import re
from pathlib import Path

import yaml

from hueman.engine.render import make_jinja_env, render_target
from hueman.engine.targets import Target

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CFG = ROOT / "hueman" / "data" / "hueman.config.example.yaml"
TG_DIR = ROOT / "examples" / "telegram"
NAMES = ["yasb_theme", "flowlauncher_theme", "telegram_theme"]
logger = logging.getLogger("hueman-tests")


def _commented_targets(win_home):
    text = EXAMPLE_CFG.read_text()
    start = text.index("  # yasb_theme:")
    end = text.index("\n\n# Comandos que corren una sola vez")
    # Solo se descomenta lo que es YAML de target: el nombre (`  # nombre:`) y
    # su cuerpo (`  #   clave: ...`); la prosa comentada (`  # texto`) se descarta.
    names = "|".join(NAMES)
    lines = []
    for ln in text[start:end].splitlines():
        if re.match(rf"^  # ({names}):$", ln) or ln.startswith("  #   "):
            lines.append(re.sub(r"^  # ?", "  ", ln))
        elif ln.strip() == "#" or not ln.strip().startswith("#"):
            lines.append("" if ln.strip() == "#" else ln)
    block = "\n".join(lines)
    return yaml.safe_load("targets:\n" + block.replace("${win_home}", str(win_home)))["targets"], block


def test_example_config_has_the_three_commented_targets_that_parse(tmp_path):
    targets, _ = _commented_targets(tmp_path)

    assert all(n in targets for n in NAMES)
    parsed = {n: Target.from_dict(n, targets[n]) for n in NAMES}
    assert parsed["yasb_theme"].mode == "patch"
    assert parsed["flowlauncher_theme"].template == "flowlauncher_theme.xaml.j2"
    assert parsed["telegram_theme"].reload
    for n in ("yasb_theme", "flowlauncher_theme"):
        assert parsed[n].skip_unless_path_exists


def test_commented_targets_are_skipped_when_tools_are_absent(tmp_path):
    targets, _ = _commented_targets(tmp_path)
    env = make_jinja_env([], ROOT / "hueman" / "templates")
    palette = yaml.safe_load((ROOT / "hueman" / "palettes" / "nord.yaml").read_text())

    for n in ("yasb_theme", "flowlauncher_theme"):
        t = Target.from_dict(n, targets[n])
        assert render_target(env, t, "nord", palette, False, logger) is False
    assert not any(tmp_path.iterdir())


def test_example_targets_and_telegram_example_use_no_real_paths_or_secrets():
    _, block = _commented_targets(Path("/x"))
    files = [TG_DIR / "README.md", TG_DIR / "telegram-theme-sync"]
    assert all(f.is_file() for f in files)
    haystack = block + "".join(f.read_text() for f in files)

    for needle in ("neandertech", "MyDotFiles", "atku5XLHRIw8SV3z", "/home/"):
        assert needle not in haystack
    assert not re.search(r"TG_API_HASH\s*=\s*[0-9a-f]{32}", haystack)
    assert not re.search(r"TG_API_ID\s*=\s*\d{5,}", haystack)


def test_telegram_script_is_valid_python_and_stays_out_of_the_package():
    ast.parse((TG_DIR / "telegram-theme-sync").read_text())
    manifest = (ROOT / "MANIFEST.in").read_text()
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert "prune examples" in manifest
    assert "examples" not in pyproject
    for f in ("pyproject.toml", "requirements.txt"):
        assert "telethon" not in (ROOT / f).read_text().lower()

import logging
import sys

import pytest

import hueman.cli as cli
from hueman.cli import Hueman
from hueman.engine.config import HuemanConfig


def _app(tmp_path, *, post_apply=None):
    (tmp_path / "theme.j2").write_text("theme={{ theme_name }}\n")
    (tmp_path / "galaxy.yaml").write_text("kitty: {}\n")
    post_apply = post_apply or []
    commands = "".join(f"  - {command!r}\n" for command in post_apply)
    (tmp_path / "hueman.yaml").write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        f"template_dirs: [{tmp_path}]\n"
        "targets:\n"
        "  written:\n"
        "    template: theme.j2\n"
        "    palette_key: kitty\n"
        f"    outputs: ['{tmp_path / 'written.conf'}']\n"
        "  first_skip:\n"
        "    template: theme.j2\n"
        "    palette_key: kitty\n"
        "    skip_if_missing_parent: true\n"
        f"    outputs: ['{tmp_path / 'missing-one' / 'theme.conf'}']\n"
        "  second_skip:\n"
        "    template: theme.j2\n"
        "    palette_key: kitty\n"
        "    skip_if_missing_parent: true\n"
        f"    outputs: ['{tmp_path / 'missing-two' / 'theme.conf'}']\n"
        f"post_apply:\n{commands}"
    )
    return Hueman(HuemanConfig(tmp_path / "hueman.yaml"))


def test_default_set_output_is_concise_english_and_quiet(tmp_path, caplog, capsys):
    app = _app(tmp_path)

    with caplog.at_level(logging.INFO, logger="hueman"):
        assert app.set_theme("galaxy") == []

    assert capsys.readouterr().out == "Applied: galaxy (written: 1, skipped: 2, failed: 0)\n"
    assert "Generated:" not in caplog.text
    assert "does not exist; skipped" not in caplog.text


def test_dry_run_verbose_retains_paths_and_hook_details(tmp_path, capsys):
    app = _app(tmp_path, post_apply=["echo refresh"])

    assert app.set_theme("galaxy", dry_run=True, verbose=True) == []

    output = capsys.readouterr().out
    assert f"[DRY RUN] would write {tmp_path / 'written.conf'}" in output
    assert "[DRY RUN] post_apply: echo refresh" in output
    assert "Dry run: galaxy (written: 1, skipped: 2, failed: 0)" in output


def test_cli_help_uses_english_set_output_labels(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["hueman", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Apply a palette" in output
    assert "Aplicar un tema" not in output


def test_cli_help_shows_scannable_examples(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["hueman", "--help"])
    with pytest.raises(SystemExit):
        cli.main()
    root = capsys.readouterr().out
    assert "commands:" in root
    assert "hueman set gruvbox --dry-run" in root
    assert "hueman sync --quiet" in root

    monkeypatch.setattr(sys, "argv", ["hueman", "set", "--help"])
    with pytest.raises(SystemExit):
        cli.main()
    set_help = capsys.readouterr().out
    assert "hueman set gruvbox --only kitty,starship" in set_help
    assert "hueman set gruvbox --verbose" in set_help

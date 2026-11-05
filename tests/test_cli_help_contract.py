import re
import sys

import pytest

import hueman.cli as cli


def help_text(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["hueman", *argv])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    return capsys.readouterr().out


def test_root_help_lists_commands_and_global_options(monkeypatch, capsys):
    out = help_text(monkeypatch, capsys, "--help")

    for command in ("set", "sync", "init", "list", "status"):
        assert re.search(rf"(?m)^\s+{command}\s+", out)
    for option in ("--config", "--var", "--version", "-h, --help"):
        assert option in out
    assert "HUEMAN_CONFIG" in out
    assert "commands:" in out
    assert "examples:" in out
    assert "Aplicar" not in out and "Configuracion" not in out


def test_set_help_covers_palette_and_key_flags(monkeypatch, capsys):
    out = help_text(monkeypatch, capsys, "set", "--help")

    assert "PALETTE" in out
    for flag in ("--dry-run", "-v, --verbose", "--only"):
        assert flag in out
    assert "hueman set gruvbox --dry-run" in out
    assert "hueman set gruvbox --only kitty,starship" in out
    assert "hueman set gruvbox --verbose" in out


def test_sync_init_list_status_help_cover_flags_and_examples(monkeypatch, capsys):
    sync = help_text(monkeypatch, capsys, "sync", "--help")
    assert "-q, --quiet" in sync
    assert "hueman sync --quiet" in sync

    init = help_text(monkeypatch, capsys, "init", "--help")
    assert "--force" in init
    assert "hueman init --force" in init

    listing = help_text(monkeypatch, capsys, "list", "--help")
    assert "List packaged and configured custom palettes" in listing
    assert "hueman list" in listing

    status = help_text(monkeypatch, capsys, "status", "--help")
    assert "active palette" in status
    assert "hueman status" in status

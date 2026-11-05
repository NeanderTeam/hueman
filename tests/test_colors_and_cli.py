import logging

from hueman.engine.colors import contrast_text, is_dark
from hueman.cli import Hueman, _SetProgress
from hueman.engine.config import HuemanConfig


def test_progress_bar_reports_current_target():
    progress = _SetProgress("galaxy", total=50, enabled=True)
    progress.update(12, "Rendering qutebrowser")

    assert progress._line() == (
        "Applying galaxy [██████░░░░░░░░░░░░░░░░░░] 12/50 · Rendering qutebrowser"
    )


def test_color_filters_classify_light_and_dark_values():
    assert contrast_text("#000000") == "#f5f5f5"
    assert contrast_text("#ffffff") == "#1a1a1a"
    assert is_dark("#000000") is True
    assert is_dark("#ffffff") is False


def test_set_theme_persists_state_and_runs_post_apply_after_targets(tmp_path, monkeypatch):
    palette_file = tmp_path / "palette.yaml"
    palette_file.write_text("name: demo\n")
    config_file = tmp_path / "hueman.yaml"
    config_file.write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        "targets: {}\n"
        "post_apply: ['echo done']\n"
    )
    config = HuemanConfig(config_file)
    app = Hueman(config)
    calls = []
    monkeypatch.setattr("hueman.cli.run_post_apply", lambda commands, logger: calls.append(commands))

    app.set_theme("palette")

    assert config.state_file.read_text() == "palette\n"
    assert calls == [["echo done"]]


def test_set_theme_dry_run_does_not_persist_state(tmp_path):
    palette_file = tmp_path / "palette.yaml"
    palette_file.write_text("name: demo\n")
    config_file = tmp_path / "hueman.yaml"
    config_file.write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        "targets: {}\n"
    )

    app = Hueman(HuemanConfig(config_file))
    app.set_theme("palette", dry_run=True)

    assert not (tmp_path / "state").exists()


def _only_app(tmp_path, monkeypatch):
    (tmp_path / "t.j2").write_text("x={{ name }}\n")
    (tmp_path / "palette.yaml").write_text("name: demo\nkitty: {}\n")
    targets = "".join(
        f"  {n}:\n    template: t.j2\n    palette_key: kitty\n"
        f"    outputs: ['{tmp_path / n}.out']\n    reload: 'reload-{n}'\n"
        for n in ("alpha_one", "alpha_two", "beta")
    )
    (tmp_path / "hueman.yaml").write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        f"template_dirs: [{tmp_path}]\n"
        f"targets:\n{targets}"
        "post_apply: ['echo done']\n"
    )
    reloads, post = [], []
    monkeypatch.setattr("hueman.cli.run_reload", lambda cmd, logger: reloads.append(cmd))
    monkeypatch.setattr("hueman.cli.run_post_apply", lambda c, logger: post.append(c))
    return Hueman(HuemanConfig(tmp_path / "hueman.yaml")), reloads, post


def test_set_theme_only_renders_matched_targets_skips_state_and_post_apply(tmp_path, monkeypatch):
    app, reloads, post = _only_app(tmp_path, monkeypatch)

    app.set_theme("palette", only=["alpha_*", "beta"])

    assert (tmp_path / "alpha_one.out").exists()
    assert (tmp_path / "alpha_two.out").exists()
    assert (tmp_path / "beta.out").exists()
    assert sorted(reloads) == ["reload-alpha_one", "reload-alpha_two", "reload-beta"]
    assert post == []
    assert not (tmp_path / "state").exists()


def test_set_theme_only_exact_name_limits_render_and_reload(tmp_path, monkeypatch):
    app, reloads, post = _only_app(tmp_path, monkeypatch)

    app.set_theme("palette", only=["beta"])

    assert not (tmp_path / "alpha_one.out").exists()
    assert (tmp_path / "beta.out").exists()
    assert reloads == ["reload-beta"]


def test_set_theme_only_unknown_pattern_raises_listing_valid_targets(tmp_path, monkeypatch):
    import pytest
    from hueman.cli import UnknownTargetError

    app, reloads, post = _only_app(tmp_path, monkeypatch)

    with pytest.raises(UnknownTargetError) as exc:
        app.set_theme("palette", only=["beta", "nope_*"])

    assert "nope_*" in str(exc.value)
    assert "alpha_one, alpha_two, beta" in str(exc.value)
    assert reloads == [] and not (tmp_path / "beta.out").exists()


def test_cli_only_flag_is_repeatable_and_comma_separated(tmp_path, monkeypatch):
    import hueman.cli as hueman

    seen = {}
    monkeypatch.setattr(
        hueman.Hueman, "set_theme",
        lambda self, name, dry_run=False, only=None, verbose=False: seen.update(only=only, verbose=verbose),
    )
    (tmp_path / "c.yaml").write_text(f"state_file: {tmp_path / 's'}\ntargets: {{}}\n")
    monkeypatch.setattr(
        "sys.argv",
        ["hueman", "--config", str(tmp_path / "c.yaml"), "set", "p", "--only", "a,b", "--only", "c_*"],
    )

    hueman.main()

    assert seen["only"] == ["a", "b", "c_*"]
    assert seen["verbose"] is False


def test_cli_only_unknown_exits_nonzero(tmp_path, monkeypatch, capsys):
    import pytest
    import hueman.cli as hueman

    (tmp_path / "p.yaml").write_text("name: demo\n")
    (tmp_path / "c.yaml").write_text(
        f"state_file: {tmp_path / 's'}\npalette_dirs: [{tmp_path}]\ntargets: {{}}\n"
    )
    monkeypatch.setattr(
        "sys.argv", ["hueman", "--config", str(tmp_path / "c.yaml"), "set", "p", "--only", "zzz"]
    )

    with pytest.raises(SystemExit) as exc:
        hueman.main()

    assert exc.value.code != 0
    assert "zzz" in capsys.readouterr().err


def test_set_reports_concise_written_skipped_and_failed_counts(tmp_path, capsys):
    (tmp_path / "t.j2").write_text("x\n")
    (tmp_path / "palette.yaml").write_text("kitty: {}\n")
    (tmp_path / "hueman.yaml").write_text(
        f"state_file: {tmp_path / 'state'}\npalette_dirs: [{tmp_path}]\n"
        f"template_dirs: [{tmp_path}]\ntargets:\n"
        f"  written:\n    template: t.j2\n    palette_key: kitty\n"
        f"    outputs: ['{tmp_path / 'written.out'}']\n"
        f"  skipped:\n    template: t.j2\n    palette_key: kitty\n"
        f"    skip_if_missing_parent: true\n    outputs: ['{tmp_path / 'missing' / 'skipped.out'}']\n"
    )

    Hueman(HuemanConfig(tmp_path / "hueman.yaml")).set_theme("palette")

    assert capsys.readouterr().out == "Applied: palette (written: 1, skipped: 1, failed: 0)\n"


def test_dry_run_shows_paths_only_with_verbose(tmp_path, monkeypatch, capsys):
    app, _, _ = _only_app(tmp_path, monkeypatch)

    app.set_theme("palette", dry_run=True)
    clean = capsys.readouterr().out
    app.set_theme("palette", dry_run=True, verbose=True)
    verbose = capsys.readouterr().out

    assert "would write" not in clean
    assert clean == "Dry run: palette (written: 3, skipped: 0, failed: 0)\n"
    assert verbose.count("[DRY RUN] would write") == 3
    assert "Dry run: palette (written: 3, skipped: 0, failed: 0)" in verbose

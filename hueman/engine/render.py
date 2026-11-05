"""Motor de render genérico: dos modos (overwrite, patch) compartidos por
TODOS los targets — nada de código Python específico por herramienta."""

import json
import re
from pathlib import Path

import jinja2
import jinja2.sandbox

from .colors import contrast_text, is_dark
from .fsutil import atomic_write_text


class TargetRenderError(Exception):
    """A target could not be rendered (e.g. the palette lacks a required key)."""


def _dig(data: dict, dotted_path: str):
    cur = data
    for part in dotted_path.split("."):
        cur = cur[part]
    return cur


def make_jinja_env(template_dirs: list, packaged_dir: Path, delimiters=None) -> jinja2.sandbox.SandboxedEnvironment:
    """Entorno Jinja en sandbox: una plantilla ajena no alcanza internals de
    Python (`__class__`, `__globals__`...).

    ChoiceLoader: los template_dirs custom del usuario se resuelven ANTES
    que los empaquetados — así un target idiosincrático puede referenciar un
    template por nombre igual que uno genérico."""
    loader = jinja2.ChoiceLoader([
        jinja2.FileSystemLoader([str(d) for d in template_dirs]),
        jinja2.FileSystemLoader(str(packaged_dir)),
    ])
    kwargs = {"loader": loader, "keep_trailing_newline": True}
    if delimiters:
        kwargs["variable_start_string"], kwargs["variable_end_string"] = delimiters
    env = jinja2.sandbox.SandboxedEnvironment(**kwargs)
    env.filters["contrast"] = contrast_text
    env.filters["is_dark"] = is_dark
    return env


def build_context(target, name: str, palette: dict) -> dict:
    context = {"theme_name": name}
    if target.palette_key and target.palette_key in palette:
        context.update(palette[target.palette_key])
    for key, dotted_path in target.extra_vars.items():
        try:
            context[key] = _dig(palette, dotted_path)
        except (KeyError, TypeError):
            raise KeyError(dotted_path) from None
    return context


def render_template(env: jinja2.Environment, target, name: str, palette: dict) -> str:
    context = build_context(target, name, palette)
    return env.get_template(target.template).render(**context)


def _record(stats, outcome: str) -> None:
    if stats is not None:
        stats[outcome] += 1


def _write(path: Path, content: str, dry_run: bool, logger, stats=None, verbose: bool = False,
           make_executable: bool = False):
    if dry_run:
        if verbose:
            print(f"[DRY RUN] would write {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, content, make_executable)
        if verbose:
            logger.info(f"Generated: {path}")
    _record(stats, "written")


def _missing_palette_section(target, palette, logger, stats=None) -> bool:
    if target.palette_key and target.palette_key not in palette:
        logger.warning(f"{target.name}: palette has no '{target.palette_key}' section; skipped")
        _record(stats, "skipped")
        return True
    return False


def render_overwrite(env, target, name, palette, dry_run, logger, stats=None, verbose: bool = False) -> bool:
    if _missing_palette_section(target, palette, logger, stats):
        return False
    content = render_template(env, target, name, palette)
    wrote = False
    for out in target.outputs:
        if target.skip_if_missing_parent and not out.parent.exists():
            if verbose:
                logger.info(f"{target.name}: {out.parent} does not exist; skipped")
            _record(stats, "skipped")
            continue
        _write(out, content, dry_run, logger, stats, verbose, target.make_executable)
        wrote = True
    return wrote


def _apply_regex_splice(original: str, rendered: str, patch, logger) -> str:
    if patch.marker_regex:
        # Bloque delimitado por un único regex (ej. una sección TOML entera).
        block = rendered
        pattern = re.compile(patch.marker_regex, re.DOTALL)
        inserted = not pattern.search(original)
        if not inserted:
            content = pattern.sub(lambda m: block, original, count=1)
        elif patch.insert_after_section_regex:
            section = re.search(patch.insert_after_section_regex, original, re.DOTALL)
            if section:
                insert_at = section.end()
                content = original[:insert_at] + "\n" + block + original[insert_at:]
            else:
                content = original.rstrip("\n") + "\n\n" + block
        else:
            content = original.rstrip("\n") + "\n\n" + block
        # Si el regex no reconoce el bloque recién insertado, se duplicará.
        if inserted and not pattern.search(content):
            logger.warning(
                "marker_regex does not match the inserted block; "
                "it will be inserted again on the next run"
            )
    else:
        # Marcadores begin/end literales envolviendo el contenido renderizado.
        marker_begin = patch.marker_begin
        marker_end = patch.marker_end
        if patch.marker_end_regex:
            end_pattern = patch.marker_end_regex
        else:
            # Consume the newline after END: full_block re-adds it.
            end_pattern = re.escape(marker_end) + r"\n?"
        pattern = re.compile(re.escape(marker_begin) + r".*?" + end_pattern, re.DOTALL)
        if marker_end and not patch.marker_end_regex:
            full_block = f"{marker_begin}\n{rendered}{marker_end}\n"
        else:
            full_block = f"{marker_begin}\n{rendered}"
        if pattern.search(original):
            content = pattern.sub(lambda m: full_block, original, count=1)
        else:
            content = original.rstrip("\n") + "\n\n" + full_block

    for old, new in patch.replacements:
        content = content.replace(old, new)
    for rule in patch.ensure_after:
        if not re.search(rule["if_missing_regex"], content):
            content = content.replace(rule["anchor"], rule["anchor"] + rule["insert"], 1)
    return content


def _apply_json_scheme_upsert(original: str, kitty: dict, scheme_name: str) -> str:
    data = json.loads(original)
    scheme = {
        "name": scheme_name,
        "background": kitty["background"],
        "foreground": kitty["foreground"],
        "black": kitty["color0"],
        "red": kitty["color1"],
        "green": kitty["color2"],
        "yellow": kitty["color3"],
        "blue": kitty["color4"],
        "purple": kitty["color5"],
        "cyan": kitty["color6"],
        "white": kitty["color7"],
        "brightBlack": kitty["color8"],
        "brightRed": kitty["color9"],
        "brightGreen": kitty["color10"],
        "brightYellow": kitty["color11"],
        "brightBlue": kitty["color12"],
        "brightPurple": kitty["color13"],
        "brightCyan": kitty["color14"],
        "brightWhite": kitty["color15"],
        "cursorColor": kitty["cursor"],
        "selectionBackground": kitty["selection_background"],
    }
    schemes = data.setdefault("schemes", [])
    for i, s in enumerate(schemes):
        if s.get("name") == scheme_name:
            schemes[i] = scheme
            break
    else:
        schemes.append(scheme)
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n"


def render_patch(env, target, name, palette, dry_run, logger, stats=None, verbose: bool = False) -> bool:
    patch = target.patch
    if _missing_palette_section(target, palette, logger, stats):
        return False

    if patch.strategy == "json_scheme_upsert":
        section = palette[patch.palette_section]
        scheme_name = patch.scheme_name or "Dotfiles"
        wrote = False
        for out in target.outputs:
            if not out.exists():
                if verbose:
                    logger.info(f"{target.name}: {out} not found; skipped")
                _record(stats, "skipped")
                continue
            original = out.read_text(encoding="utf-8")
            try:
                content = _apply_json_scheme_upsert(original, section, scheme_name)
            except json.JSONDecodeError as exc:
                raise TargetRenderError(f"{target.name}: {out} is not valid JSON ({exc})") from exc
            wrote = True
            if dry_run:
                if verbose:
                    print(f"[DRY RUN] would write {out} (scheme '{scheme_name}')")
            else:
                atomic_write_text(out, content)
                if verbose:
                    logger.info(f"{target.name}: scheme '{scheme_name}' updated in {out}")
            _record(stats, "written")
        return wrote

    # regex_splice
    rendered = render_template(env, target, name, palette) if target.template else ""
    wrote = False
    for out in target.outputs:
        if target.skip_if_missing_parent and not out.parent.exists():
            if verbose:
                logger.info(f"{target.name}: {out.parent} does not exist; skipped")
            _record(stats, "skipped")
            continue
        if not out.exists():
            if verbose:
                logger.info(f"{target.name}: {out} not found; skipped")
            _record(stats, "skipped")
            continue
        original = out.read_text()
        content = _apply_regex_splice(original, rendered, patch, logger)
        _write(out, content, dry_run, logger, stats, verbose, target.make_executable)
        wrote = True
    return wrote


def render_target(env, target, name, palette, dry_run, logger, stats=None, verbose: bool = False) -> bool:
    missing = [p for p in target.skip_unless_path_exists if not p.exists()]
    if missing:
        if verbose:
            logger.info(f"{target.name}: {missing[0]} does not exist; target skipped")
        _record(stats, "skipped")
        return False
    try:
        if target.mode == "overwrite":
            return render_overwrite(env, target, name, palette, dry_run, logger, stats, verbose)
        return render_patch(env, target, name, palette, dry_run, logger, stats, verbose)
    except jinja2.TemplateNotFound as exc:
        raise TargetRenderError(f"{target.name}: template {exc.name!r} not found") from exc
    except jinja2.exceptions.SecurityError as exc:
        raise TargetRenderError(
            f"{target.name}: template attempted a disallowed sandbox operation ({exc})"
        ) from exc
    except OSError as exc:
        raise TargetRenderError(f"{target.name}: I/O error ({exc})") from exc
    except (KeyError, TypeError) as exc:
        key = exc.args[0] if exc.args else exc
        raise TargetRenderError(
            f"{target.name}: palette '{name}' lacks required key {key!r}"
        ) from exc

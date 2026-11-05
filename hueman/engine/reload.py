"""Ejecuta comandos de recarga: uno por target (best-effort, tras escribir
con éxito) y los `post_apply` globales (una sola vez al final de `set`)."""

import re
import shlex
import subprocess

from .render import _dig

# `{name}`, `{palette}` o `{seccion.clave}`; el lookbehind deja intactos
# `${VAR}` del shell. Llaves simples sin punto (ej. `find -exec {} +`) no
# matchean salvo `name`/`palette`.
_PLACEHOLDER = re.compile(r"(?<!\$)\{([A-Za-z_]\w*(?:\.\w+)*)\}")


class PlaceholderError(ValueError):
    """Un `{seccion.clave}` de reload/post_apply no existe en la paleta."""


def expand_command(cmd: str, name: str, palette: dict) -> str:
    """Sustituye `{name}`/`{palette}` y `{a.b}` (lookup en la paleta activa)
    por su valor con shlex.quote. Un `{a.b}` que no resuelve es un error."""
    def repl(m):
        key = m.group(1)
        if key in ("name", "palette"):
            return shlex.quote(name)
        if "." not in key:
            return m.group(0)
        try:
            value = _dig(palette, key)
        except (KeyError, TypeError):
            raise PlaceholderError(f"unknown placeholder {{{key}}} in command: {cmd}")
        return shlex.quote(str(value))

    return _PLACEHOLDER.sub(repl, cmd)


def _run(label: str, cmd: str, logger, verbose: bool = False) -> int:
    """Run `cmd`, hiding successful command output unless verbose is requested."""
    result = subprocess.run(
        ["sh", "-c", cmd],
        capture_output=not verbose,
        text=True,
    )
    if verbose:
        logger.info(f"{label}: {cmd} (exit {result.returncode})")
    elif result.returncode:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        if output:
            logger.warning(f"{label} failed output: {output}")
    return result.returncode


def run_reload(cmd: str, logger, verbose: bool = False) -> int:
    """Run a target reload command; return its exit code (0 if no command)."""
    if not cmd:
        return 0
    return _run("reload", cmd, logger, verbose)


def run_post_apply(commands: list, logger, verbose: bool = False) -> list:
    """Run every command (a failure does not stop the rest); return the
    `(command, exit_code)` pairs of those that exited non-zero."""
    failed = []
    for cmd in commands:
        rc = _run("post_apply", cmd, logger, verbose)
        if rc:
            failed.append((cmd, rc))
    return failed

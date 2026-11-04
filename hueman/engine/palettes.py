"""Carga de paletas YAML: empaquetadas dentro del tool + directorios custom
del usuario, con precedencia de los custom sobre los empaquetados."""

import re
from pathlib import Path

import yaml

PALETTE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def is_valid_palette_name(name) -> bool:
    """Nombre seguro: sin separadores de ruta, sin '..', sin espacios ni saltos
    de linea. El nombre llega a rutas, logs y comandos (y con `sync` lo controla
    el remoto), asi que se valida antes de tocar el disco."""
    return (isinstance(name, str) and PALETTE_NAME_RE.fullmatch(name) is not None
            and ".." not in name)


class PaletteLoader:
    def __init__(self, packaged_dir: Path, custom_dirs: list, logger):
        self.packaged_dir = packaged_dir
        self.custom_dirs = custom_dirs
        self.logger = logger

    def _search_dirs(self):
        # los custom_dirs (en orden declarado) tienen precedencia sobre lo empaquetado
        return list(self.custom_dirs) + [self.packaged_dir]

    def list_palettes(self) -> list:
        found = {}
        for d in self._search_dirs():
            if not d.exists():
                continue
            for p in d.glob("*.yaml"):
                if p.stem in found and found[p.stem] != p:
                    self.logger.warning(
                        f"Palette '{p.stem}' is defined in more than one directory; "
                        f"using the higher-precedence definition: {found[p.stem]}"
                    )
                    continue
                found.setdefault(p.stem, p)
        return sorted(found)

    def load(self, name: str) -> dict:
        if not is_valid_palette_name(name):
            self.logger.error(
                f"Invalid palette name: {name!r} "
                "(use letters, digits, '.', '_', or '-'; must start with a letter or digit)"
            )
            raise SystemExit(1)
        for d in self._search_dirs():
            path = d / f"{name}.yaml"
            if path.exists():
                try:
                    data = yaml.safe_load(path.read_text())
                except yaml.YAMLError as exc:
                    self.logger.error(f"Invalid palette {path}: {exc}")
                    raise SystemExit(1)
                if not isinstance(data, dict):
                    self.logger.error(f"Invalid palette {path}: expected a YAML mapping")
                    raise SystemExit(1)
                return data
        available = ", ".join(self.list_palettes())
        self.logger.error(f"Palette not found: {name}. Available: {available}")
        raise SystemExit(1)

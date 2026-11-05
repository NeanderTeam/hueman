# Contributing

## Setup

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Workflow

- Branch from `dev` (`feat/...`, `fix/...`, `docs/...`) and open the PR against `dev`.
- `main` only carries releases; do not target it.
- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, `test:`).
- `CHANGELOG.md` is generated from commit messages. Do not edit it by hand.

## Tests

Behavior changes need tests. Writing the failing test first is welcome.
Run `python -m pytest -q` before opening the PR.

## Documentation

The docs live in `website/content/latest` (English, public product language).

- Add a tool or target: [add-a-tool](website/content/latest/guides/add-a-tool.md)
- Add a palette: [add-a-palette](website/content/latest/guides/add-a-palette.md)

Targets stay declarative: tool-specific logic belongs in YAML and Jinja
templates, not in Python.

### Freezing docs for a release

The site is static (`website/`, no build step). `content/latest` is the editable
tip. Page ids in `content/*/nav.json` are used as URLs (`?p=<id>`), so do not
rename them.

Docs freezes are **automatic** on release. When `release.yml` cuts a version it
runs `scripts/freeze-docs.sh vX.Y.Z` before tagging, in the same
`chore(release): vX.Y.Z` commit as the changelog. That script:

1. Copies `website/content/latest/` → `website/content/vX.Y.Z/`
2. Copies `website/skills/latest/` → `website/skills/vX.Y.Z/` when present
3. Inserts the release entry in `website/data/versions.json` and marks the
   previous release snapshot as `supported`

Do **not** open a follow-up PR just to freeze docs. To dry-run locally:

```bash
./scripts/freeze-docs.sh vX.Y.Z
# inspect, then discard the generated paths if you are not cutting a release
```

## Security

Report vulnerabilities privately; see [SECURITY.md](SECURITY.md).

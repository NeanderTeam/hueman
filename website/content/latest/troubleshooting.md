# Troubleshooting

| Problem | What to check |
|---------|----------------|
| `Config not found: <path>` | Exit 1. Create one with `hueman init`, or use `--config` / `HUEMAN_CONFIG`. Order: `--config` / `HUEMAN_CONFIG` / `~/.config/hueman/config.yaml` (cwd is not searched) |
| `Palette not found: <name>. Available: ...` | Name matches no YAML in `palette_dirs` or packaged palettes; see `hueman list` |
| `Invalid palette <path>: ...` | Palette YAML does not parse or its root is not a mapping |
| `Invalid palette name: '...'` | Only letters, digits, `.`, `_`, `-`; must start with a letter or digit |
| `Invalid config: <path>: invalid YAML: ...` / `expected a YAML mapping at the root` | Config does not parse or root is not a mapping |
| `Invalid config: ... variable '${name}' is undefined` / `vars.<name> ...` | Undefined `${...}` in `vars`, invalid name, non-string value, or nested `${...}` |
| `Invalid config: ... reload_failure must be 'warn' or 'error'` | Value outside the two allowed policies |
| `<target>: template '<name>' not found` | Template missing from `template_dirs` and packaged set; target counts as failed |
| `Failed targets: a, b` | Final summary (exit 1) of failed targets; detail is in earlier logs |
| `Already exists: <path> (use --force to overwrite)` | `hueman init` will not overwrite an existing config |
| Palette not listed | File name, `palette_dirs`, valid YAML |
| Template not found | Exact name, `template_dirs`, packaged vs custom |
| File does not change | `--dry-run`, `--only`, skip guards, `palette_key` that is not a palette section (WARNING `palette has no '<key>' section; skipped`, exit 0), patch with no match |
| Empty values in the output | Missing context variable: Jinja renders an empty string, no error. Check `palette_key` and key names |
| Literal `{{ … }}` | Only with `jinja_delimiters` other than `{{ }}`: the template uses different delimiters |
| `Invalid config: ... logging.level` / `logging.file` / `mode` / `patch` / `post_apply` / `outputs` | Invalid config value: unknown `level`, missing/unwritable `file` directory, `mode` not `overwrite`/`patch`, `mode: patch` without a `patch` section, `post_apply` or `outputs` that is not a list of strings. Exit 1, one-line message, no traceback |
| `Invalid config: unknown placeholder` | Unknown `{section.key}` in `reload` or `post_apply`: `set` (and `sync`, without advancing revision) exits clean (exit 1) before writing |
| Duplicated block in a patch | `marker_regex` with no match and no `insert_after_section_regex`: appends the block on every run; hueman warns if your `marker_regex` does not recognize the block it inserted |
| Exit 1 with theme applied | Targets skipped on error, or `reload_failure: error` |
| Sync does not apply | `status` drift; remote unreachable; local revision ≥ remote; remote palette missing on this node (notice, exit 0) |

More context when extending tools: [Add support for a tool](guides/add-a-tool.md).

## If you come from a host/environment detection engine

1. **`outputs` is a static list, not "discovered" each run.** If you list a path
   that does not exist yet, an `overwrite` target creates it (`mkdir -p` +
   write). If your old engine silently skipped an environment without that
   folder, this one creates it; use `skip_if_missing_parent` to skip.
2. **A target's `reload` only runs if that target wrote something.** There is
   no global reload step that runs regardless of what rendered.
3. **No hostname/environment detection in the engine.** If your reload depends
   on "which machine am I", resolve that in your own wrapper script and pass it
   as `reload:`; the engine only runs the command you give it.

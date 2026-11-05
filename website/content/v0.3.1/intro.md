# What is hueman

**One palette. Every tool.**

hueman keeps your terminal, editor, prompt, and the rest of your setup on the
same theme. You say which file each app uses, and one command paints them all.

Core ideas:

- One palette, many targets.
- Packaged templates and palettes are defaults; your custom dirs win.
- Overwrite for full generated files; patch for blocks inside hand-edited configs.
- Reload and post_apply are best-effort, with a `warn` / `error` policy.
- Optional sync of the active palette across machines (`state_sync`).

To add a tool, write a template and a target. The engine doesn't change.
Guide: [Add support for a tool](guides/add-a-tool.md).

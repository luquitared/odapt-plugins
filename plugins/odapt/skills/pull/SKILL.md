---
description: Pull an Odapt app's source (views/partials as HTML files) into a local folder for editing with Claude Code. Use when the user wants to download, pull, clone, or locally edit an Odapt app.
argument-hint: "[app_id] [directory]"
---

# Pull an Odapt app locally

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py pull <app_id> --dir <directory>
```

- Resolve the app id via `apps` (list + ask) if not given.
- Default directory: a new folder named after the app (kebab-case) in the
  current working directory — never overwrite a non-empty directory without
  asking.
- The pull writes each view as `<name>.html`, partials under `partials/`,
  and an `odapt.json` manifest (app_id + build_id) that /odapt:publish uses
  for round-tripping.

After pulling, orient the user: views are plain HTML pages; navigation
between them is real links/`location.href` (relative URLs — `spec.html`, not
`/spec`); the odapt runtime APIs available in-page are `callTool`,
`requestGPT`, `navigateTo`, `getQueryParams`, `appdb_*` via callTool. Edit
files, then `/odapt:publish` to ship.

Note: running the app fully locally (serving files + live gateway calls)
isn't wired yet — edits are verified by publishing to a private app or using
the hosted editor preview.

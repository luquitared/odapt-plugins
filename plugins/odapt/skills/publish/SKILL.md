---
description: Publish an Odapt app — push local app files (if any) and make the current build live, applying visibility settings. Use when the user says publish, deploy, ship, or "put my app online" in an Odapt context.
argument-hint: "[app_id] [--public true|false] [--requires-login true|false]"
---

# Publish an Odapt app

The CLI is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py` (JSON on
stdout; errors on stderr). If any call fails with a missing/invalid key, run
`/odapt:setup` first.

## Resolve the app

- If the working directory has an `odapt.json` manifest, use its `app_id`
  (and `build_id`).
- Else if the user gave an app id or name, use `apps` to list and match.
- Else run `apps` and ask which one (AskUserQuestion) — or offer to `create
  --name <name>` for a brand-new app when the directory clearly contains an
  app (html views) but no manifest.

## Steps

1. **Publishing a local folder — use the one atomic verb:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py deploy [app_id] --dir . [--name N] [--public ...] [--requires-login ...]
   ```
   `deploy` reads/writes the `odapt.json` manifest (identity + settings;
   flags update it), uploads every deployable file (html at root = pages,
   `partials/`, plus css/js/svg/json assets), creates the app on first run,
   snapshots a new build, and prints the live URL. The manifest never
   contains a build_id — builds are server state returned by the deploy.
2. **Publishing an editor-built app (no local files):**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py publish <app_id> [--public true|false] [--requires-login true|false]
   ```
3. **Report**: the command prints the live URL (`https://odapt.ai/app?app_id=N`)
   plus the resulting visibility. State plainly: who can access it now
   (e.g. "public, no login required" / "private — only you"). If the app is
   shared with specific emails, list them (`shares <app_id>`).

Never flip an app from private to public unless the user asked for that or
their configured default says so — say what you're about to apply first if
it differs from the app's current state.

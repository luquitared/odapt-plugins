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

1. **Push local changes** only if the directory contains the app source
   (`odapt.json` present, or user asked to publish "this folder"):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py push <app_id> --dir .
   ```
   Skip pushing when the user is publishing an app they built in the hosted
   editor (no local files) — publishing works on the server-side build as-is.
2. **Publish** (points the deployment at the build and applies access flags;
   omitted flags fall back to `~/.odapt/config.json` defaults):
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

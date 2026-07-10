# Odapt Claude Code plugin

Build, publish, and manage [Odapt](https://odapt.ai) apps from Claude Code.

## Install (two commands)

```
/plugin marketplace add luquitared/odapt-plugins
/plugin install odapt@odapt-plugins
```

Then run `/odapt:setup` once to link your account (API key from
https://odapt.ai/developers) and pick publish defaults.

## Commands

| Command | What it does |
|---|---|
| `/odapt:setup` | Link account, validate key, set publish defaults (`~/.odapt/config.json`) |
| `/odapt:publish` | Push local app files (if any) and make the build live with your visibility settings |
| `/odapt:configure` | View/change name, visibility, login requirement; share with specific emails |
| `/odapt:pull` | Download an app's views/partials as HTML files + `odapt.json` manifest for local editing |

## Repo layout

This repo is both the **marketplace** (`.claude-plugin/marketplace.json`) and
the **plugin** (`plugins/odapt/`). Skills call `plugins/odapt/scripts/odapt_api.py`
(Python 3 stdlib, no dependencies) against the Odapt REST API using
`ODAPT_API_KEY` or `~/.odapt/config.json`.

Currently developed inside the odapt monorepo at `claude-plugin/`; published
as a standalone public repo so `/plugin marketplace add` works for users.
Versioning: none — every commit is a release (SHA-based plugin versioning).

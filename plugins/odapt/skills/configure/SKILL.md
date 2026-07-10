---
description: View or change an Odapt app's settings — name, description, visibility (public/private), login requirement, and sharing with specific email addresses. Use when the user wants to configure, rename, make public/private, or share an Odapt app.
argument-hint: "[app_id] [setting...]"
---

# Configure an Odapt app

CLI: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py`. Resolve the app
the same way as /odapt:publish (odapt.json manifest → given id/name → list
and ask).

## Read current settings

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py configure <app_id>   # GET when no flags
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py shares <app_id>
```

Summarize as: name, description, access mode (private / public+login /
public web), live URL, shared emails.

## Change settings

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py configure <app_id> \
  [--name "New Name"] [--description "..."] \
  [--public true|false] [--requires-login true|false]
```

Access modes map as: **private** = public:false; **public on odapt (login
required)** = public:true, requires-login:true; **public web (anonymous)** =
public:true, requires-login:false.

## Sharing with specific people

Sharing gives named people access to a **private** app (they log in to odapt
with that email and open the app URL):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py share <app_id> person@example.com
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py unshare <app_id> person@example.com
```

After sharing, tell the user: the app stays private; shared people access it
at the app URL after logging in with that email — no odapt account needed in
advance (they can sign up with it). If the app is currently public, note
that shares only matter once it's private.

Confirm before changes that widen access (private → public).

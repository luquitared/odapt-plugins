---
description: Connect Claude Code to your Odapt account and set publish defaults. Use when the user wants to set up, configure, or log in to Odapt, or when another odapt skill fails with a missing/invalid API key.
argument-hint: "[api-key]"
---

# Odapt setup

Link this machine to an Odapt account and record publish defaults in
`~/.odapt/config.json`.

## Steps

1. **Get an API key.** If the user passed one as an argument, use it. If
   `ODAPT_API_KEY` is set in the environment, prefer that. Otherwise tell the
   user: create a key at **https://odapt.ai/developers** (API keys section)
   and paste it here — then wait for them to provide it. Keys start with
   `sk-`.
2. **Validate it** before saving:
   ```bash
   ODAPT_API_KEY=<key> python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py whoami
   ```
   This prints the account (id, email) on success. On 401, the key is wrong —
   ask again; do not save.
3. **Ask for publish defaults** (one AskUserQuestion, two questions):
   - Default visibility for newly published apps: private (only you) /
     public on the web (anonymous allowed) / public but login required.
   - (Skip billing — not configurable yet.)
   Map to `defaults`: private → `{"public": false, "requires_login": true}`;
   public web → `{"public": true, "requires_login": false}`;
   public + login → `{"public": true, "requires_login": true}`.
4. **Write `~/.odapt/config.json`** (create `~/.odapt/` if needed), merging
   with any existing file:
   ```json
   {
     "api_key": "sk-…",
     "base_url": "https://odapt.ai",
     "auth_url": "https://auth.odapt.ai",
     "defaults": { "public": false, "requires_login": true }
   }
   ```
   Set file mode 600. If the user prefers env-var-only, omit `api_key` and
   tell them to export `ODAPT_API_KEY` in their shell profile instead.
5. Confirm: print the account email and the chosen defaults, and mention the
   main commands: `/odapt:publish`, `/odapt:configure`, `/odapt:pull`.

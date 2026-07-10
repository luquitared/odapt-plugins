#!/usr/bin/env python3
"""Odapt CLI — thin wrapper over the Odapt REST API for the Claude Code plugin.

Auth: ODAPT_API_KEY env var, else "api_key" in ~/.odapt/config.json.
Stdlib only. Every command prints JSON to stdout (errors to stderr, exit 1).

Commands:
  whoami                                   validate key, print user
  apps                                     list your apps
  app <app_id>                             app details (+ builds)
  create --name N [--description D]        create app (+ first build)
  pull <app_id> [--dir DIR] [--build B]    write views/partials to files
  push <app_id> [--dir DIR] [--build B]    read files, merge into build app_spec
  publish <app_id> [--build B] [--public true|false] [--requires-login true|false]
                                           point deployment at build + set access
  configure <app_id> [--name N] [--description D] [--public ...] [--requires-login ...]
  shares <app_id>                          list shared emails
  share <app_id> <email>                   share app with an email
  unshare <app_id> <email>                 remove a share
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".odapt" / "config.json"


def load_config():
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    cfg.setdefault("base_url", "https://odapt.ai")
    cfg.setdefault("auth_url", "https://auth.odapt.ai")
    cfg.setdefault("defaults", {})
    return cfg


CFG = load_config()
API_KEY = os.environ.get("ODAPT_API_KEY") or CFG.get("api_key")


def die(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def req(method, url, body=None, auth=True):
    headers = {"Content-Type": "application/json"}
    if auth:
        if not API_KEY:
            die("No API key. Set ODAPT_API_KEY or run /odapt:setup (writes ~/.odapt/config.json).")
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        die(f"{method} {url} -> HTTP {e.code}: {detail}")
    except Exception as e:
        die(f"{method} {url} failed: {e}")


def api(method, path, body=None):
    return req(method, CFG["base_url"] + path, body)


def whoami():
    return req("GET", CFG["auth_url"] + "/api/user")


def get_default_build_id(app_id):
    app = api("GET", f"/apps/{app_id}")["app"]
    return app.get("build_id"), app


# --- file <-> app_spec mapping -------------------------------------------
# Views live as <name>.html in the app dir; partials as partials/<name>.html.
# app_spec views may be {"template_content": str} or bare strings; preserve
# whichever shape the build already uses when pushing back.

def spec_to_files(spec, out):
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, view in (spec.get("views") or {}).items():
        content = view.get("template_content") if isinstance(view, dict) else view
        if not isinstance(content, str):
            continue
        p = out / f"{name}.html"
        p.write_text(content)
        written.append(str(p))
    partials = spec.get("partials") or {}
    if partials:
        (out / "partials").mkdir(exist_ok=True)
        for name, content in partials.items():
            if isinstance(content, str):
                p = out / "partials" / f"{name}.html"
                p.write_text(content)
                written.append(str(p))
    return written


def files_to_spec(src, existing_spec):
    spec = existing_spec or {}
    views = dict(spec.get("views") or {})
    partials = dict(spec.get("partials") or {})
    found = False
    for p in sorted(src.glob("*.html")):
        found = True
        name = p.stem
        old = views.get(name)
        if isinstance(old, dict):
            views[name] = {**old, "template_content": p.read_text()}
        else:
            views[name] = {"template_content": p.read_text()}
    pdir = src / "partials"
    if pdir.is_dir():
        for p in sorted(pdir.glob("*.html")):
            found = True
            partials[p.stem] = p.read_text()
    if not found:
        die(f"No .html files found in {src}")
    spec["views"] = views
    spec["partials"] = partials
    return spec


# --- commands --------------------------------------------------------------

def parse_flags(args):
    flags, rest, i = {}, [], 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = "true"
                i += 1
        else:
            rest.append(a)
            i += 1
    return flags, rest


def as_bool(v):
    if str(v).lower() in ("true", "1", "yes"): return True
    if str(v).lower() in ("false", "0", "no"): return False
    die(f"Expected true/false, got {v!r}")


def main():
    if len(sys.argv) < 2:
        die("No command. See --help in the file docstring.")
    cmd, argv = sys.argv[1], sys.argv[2:]
    flags, args = parse_flags(argv)

    if cmd == "whoami":
        out = whoami()

    elif cmd == "apps":
        me = whoami()
        out = api("GET", f"/users/{me['id']}/apps?page=1&page_size=100")

    elif cmd == "app":
        app = api("GET", f"/apps/{args[0]}")
        builds = api("GET", f"/apps/{args[0]}/builds")
        out = {**app, "builds": builds.get("builds", builds)}

    elif cmd == "create":
        name = flags.get("name") or die("--name required")
        out = api("POST", "/apps", {"app_name": name, "description": flags.get("description", "")})

    elif cmd == "pull":
        app_id = args[0]
        build_id = flags.get("build")
        if not build_id:
            build_id, _ = get_default_build_id(app_id)
        build = api("GET", f"/apps/{app_id}/builds/{build_id}")
        b = build.get("builds") or build.get("build") or build
        if isinstance(b, list):
            b = b[0]
        spec = b.get("app_spec")
        if isinstance(spec, str):
            spec = json.loads(spec)
        outdir = Path(flags.get("dir", "."))
        written = spec_to_files(spec or {}, outdir)
        manifest = {"app_id": int(app_id), "build_id": int(build_id), "base_url": CFG["base_url"]}
        (outdir / "odapt.json").write_text(json.dumps(manifest, indent=2))
        out = {"pulled": written, "manifest": str(outdir / "odapt.json")}

    elif cmd == "push":
        app_id = args[0]
        src = Path(flags.get("dir", "."))
        manifest = {}
        mf = src / "odapt.json"
        if mf.exists():
            manifest = json.loads(mf.read_text())
        build_id = flags.get("build") or manifest.get("build_id")
        if not build_id:
            build_id, _ = get_default_build_id(app_id)
        cur = api("GET", f"/apps/{app_id}/builds/{build_id}")
        b = cur.get("builds") or cur.get("build") or cur
        if isinstance(b, list):
            b = b[0]
        spec = b.get("app_spec")
        if isinstance(spec, str):
            spec = json.loads(spec)
        new_spec = files_to_spec(src, spec)
        out = api("PATCH", f"/apps/{app_id}/builds/{build_id}", {"app_spec": new_spec})
        out = {"pushed": sorted((new_spec.get("views") or {}).keys()), "build_id": int(build_id),
               "message": out.get("message")}

    elif cmd == "publish":
        app_id = args[0]
        build_id = flags.get("build")
        if not build_id:
            build_id, _ = get_default_build_id(app_id)
        updates = {"deployment_build_id": int(build_id)}
        defaults = CFG.get("defaults", {})
        public = flags.get("public", defaults.get("public"))
        req_login = flags.get("requires_login", defaults.get("requires_login"))
        if public is not None:
            updates["public"] = as_bool(public)
        if req_login is not None:
            updates["requires_login"] = as_bool(req_login)
        res = api("PATCH", f"/apps/{app_id}", updates)
        app = res.get("app", {})
        url = f"{CFG['base_url']}/app?app_id={app_id}"
        out = {"published": True, "app_id": int(app_id), "deployment_build_id": int(build_id),
               "public": app.get("public"), "requires_login": app.get("requires_login"), "url": url}

    elif cmd == "configure":
        app_id = args[0]
        updates = {}
        if "name" in flags: updates["app_name"] = flags["name"]
        if "description" in flags: updates["description"] = flags["description"]
        if "public" in flags: updates["public"] = as_bool(flags["public"])
        if "requires_login" in flags: updates["requires_login"] = as_bool(flags["requires_login"])
        if not updates:
            out = api("GET", f"/apps/{app_id}")
        else:
            out = api("PATCH", f"/apps/{app_id}", updates)

    elif cmd == "shares":
        out = api("GET", f"/apps/{args[0]}/shares")

    elif cmd == "share":
        out = api("POST", f"/apps/{args[0]}/shares", {"email": args[1]})

    elif cmd == "unshare":
        out = api("DELETE", f"/apps/{args[0]}/shares/{args[1]}")

    else:
        die(f"Unknown command: {cmd}")

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Odapt CLI — thin wrapper over the Odapt REST API for the Claude Code plugin.

Auth: ODAPT_API_KEY env var, else "api_key" in ~/.odapt/config.json.
Stdlib only. Every command prints JSON to stdout (errors to stderr, exit 1).

Commands:
  whoami                                   validate key, print user
  apps                                     list your apps
  app <app_id>                             app details (+ builds)
  create --name N [--description D] [--public true|false]
                                           create app + first build + link
  deploy [app_id] [--dir DIR] [--name N] [--public ...] [--requires-login ...]
                                           create-if-needed + push + publish (one verb)
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


def create_app_with_build(name, description="", public=False):
    """POST /apps alone leaves an app with no build; do the full dance the
    dashboard does: create app -> create empty build -> point app at it."""
    res = api("POST", "/apps", {"app_name": name, "description": description, "public": bool(public)})
    app = res["app"]
    app_id = app.get("id") or app.get("app_id")
    build = api("POST", "/builds", {
        "app_id": int(app_id), "instructions": "", "enabled_tools": [],
        "disabled_action_names": [], "app_spec": {"views": {}, "partials": {}},
    }).get("build") or {}
    build_id = build.get("id") or build.get("build_id")
    if build_id:
        api("PATCH", f"/apps/{app_id}", {"build_id": int(build_id)})
    return {"app_id": int(app_id), "build_id": build_id and int(build_id), "app_name": name}


def ensure_build(app_id):
    """Return the app's editing build id, creating + linking one if missing."""
    app = api("GET", f"/apps/{app_id}")["app"]
    if app.get("build_id"):
        return app["build_id"]
    build = api("POST", "/builds", {
        "app_id": int(app_id), "instructions": "", "enabled_tools": [],
        "disabled_action_names": [], "app_spec": {"views": {}, "partials": {}},
    }).get("build") or {}
    build_id = build.get("id") or build.get("build_id")
    if not build_id:
        die(f"App {app_id} has no build and creating one failed.")
    api("PATCH", f"/apps/{app_id}", {"build_id": int(build_id)})
    return int(build_id)


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

    if cmd == "login":
        # Device-link flow: open browser, approve, key lands in ~/.odapt/config.json.
        import time
        start = req("POST", CFG["auth_url"] + "/cli-auth/start", {}, auth=False)
        print(json.dumps({"open_this_url": start["verification_url"],
                          "code": start["user_code"],
                          "expires_in": start["expires_in"]}), file=sys.stderr)
        deadline = time.time() + start.get("expires_in", 600)
        key = None
        while time.time() < deadline:
            time.sleep(start.get("interval", 3))
            res = req("POST", CFG["auth_url"] + "/cli-auth/poll",
                      {"poll_token": start["poll_token"]}, auth=False)
            if res.get("status") == "approved":
                key = res["api_key"]
                break
        if not key:
            die("Login timed out — code expired before approval.")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        cfg = dict(CFG)
        cfg["api_key"] = key
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        os.chmod(CONFIG_PATH, 0o600)
        global API_KEY
        API_KEY = key
        me = whoami()
        out = {"logged_in": True, "email": me.get("email"), "config": str(CONFIG_PATH)}

    elif cmd == "whoami":
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
        out = create_app_with_build(name, flags.get("description", ""),
                                    as_bool(flags.get("public", CFG.get("defaults", {}).get("public", False))))

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
            build_id = ensure_build(app_id)
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

    elif cmd == "deploy":
        # One idempotent verb: create app if needed, push the directory, publish.
        src = Path(flags.get("dir", "."))
        mf = src / "odapt.json"
        manifest = json.loads(mf.read_text()) if mf.exists() else {}
        app_id = (args[0] if args else None) or flags.get("app") or manifest.get("app_id")
        if not app_id:
            name = flags.get("name") or src.resolve().name
            created = create_app_with_build(name, flags.get("description", ""),
                                            as_bool(flags.get("public", CFG.get("defaults", {}).get("public", False))))
            app_id = created["app_id"]
        build_id = manifest.get("build_id") or ensure_build(app_id)
        cur = api("GET", f"/apps/{app_id}/builds/{build_id}")
        b = cur.get("builds") or cur.get("build") or cur
        if isinstance(b, list):
            b = b[0]
        spec = b.get("app_spec")
        if isinstance(spec, str):
            spec = json.loads(spec)
        new_spec = files_to_spec(src, spec)
        api("PATCH", f"/apps/{app_id}/builds/{build_id}", {"app_spec": new_spec})
        updates = {"deployment_build_id": int(build_id)}
        defaults = CFG.get("defaults", {})
        for flag_key, col in (("public", "public"), ("requires_login", "requires_login")):
            val = flags.get(flag_key, defaults.get(col))
            if val is not None:
                updates[col] = as_bool(val)
        api("PATCH", f"/apps/{app_id}", updates)
        mf.write_text(json.dumps({"app_id": int(app_id), "build_id": int(build_id),
                                  "base_url": CFG["base_url"]}, indent=2))
        out = {"deployed": True, "app_id": int(app_id), "build_id": int(build_id),
               "views": sorted((new_spec.get("views") or {}).keys()),
               "url": f"{CFG['base_url']}/app?app_id={app_id}"}

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

    elif cmd == "presigners":
        out = api("GET", "/presigners")

    elif cmd == "presigner-create":
        body = {
            "name": flags.get("name") or die("--name required"),
            "bucket": flags.get("bucket") or die("--bucket required"),
            "provider": flags.get("provider", "s3"),
            "region": flags.get("region", "us-east-1"),
            "key_prefix": flags.get("prefix", ""),
            "max_expires_seconds": int(flags.get("max_expires", "3600")),
            "access_key_id": flags.get("access_key_id") or os.environ.get("PRESIGN_ACCESS_KEY_ID") or die("--access-key-id or PRESIGN_ACCESS_KEY_ID required"),
            "secret_access_key": flags.get("secret_access_key") or os.environ.get("PRESIGN_SECRET_ACCESS_KEY") or die("--secret-access-key or PRESIGN_SECRET_ACCESS_KEY required"),
        }
        if flags.get("endpoint"):
            body["endpoint"] = flags["endpoint"]
        if flags.get("methods"):
            body["allowed_methods"] = [m.strip().upper() for m in flags["methods"].split(",")]
        out = api("POST", "/presigners", body)

    elif cmd == "presigner-delete":
        out = api("DELETE", f"/presigners/{args[0]}")

    elif cmd == "presign":
        body = {"key": flags.get("key") or (args[1] if len(args) > 1 else None) or die("--key required"),
                "method": flags.get("method", "PUT")}
        if flags.get("expires"):
            body["expires_in"] = int(flags["expires"])
        if flags.get("content_type"):
            body["content_type"] = flags["content_type"]
        out = api("POST", f"/presigners/{args[0]}/presign", body)

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

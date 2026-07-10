---
description: Generate S3/R2 pre-signed upload/download URLs through Odapt — no server needed. Use when the user needs presigned URLs, direct-to-bucket uploads from a static site, or mentions S3/R2 signing without wanting to run a backend.
argument-hint: "[presigner_id --key path/file.png]"
---

# Odapt presigner

Odapt holds your S3/R2 credentials (encrypted) and signs URLs on demand, so
static sites and serverless apps can upload/download directly to a bucket.
CLI: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py`.

## One-time: create a presigner

Ask the user for provider (S3 or R2), bucket, region (S3) or account endpoint
(R2, `https://<account_id>.r2.cloudflarestorage.com`), an optional key prefix
to confine access, and the access key pair. **Never echo the secret back;
prefer passing keys via env vars:**

```bash
PRESIGN_ACCESS_KEY_ID=... PRESIGN_SECRET_ACCESS_KEY=... \
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py presigner-create \
  --name my-uploads --provider r2 --endpoint https://<account>.r2.cloudflarestorage.com \
  --bucket my-bucket --prefix uploads/ --methods GET,PUT --max-expires 3600
```

`presigners` lists existing ones (secrets are never returned).

## Generate a URL

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odapt_api.py presign <presigner_id> \
  --key uploads/avatar.png --method PUT --expires 900 --content-type image/png
```

Returns `{url, method, headers, expiresAt}`. For PUT with `--content-type`,
the client MUST send exactly that Content-Type header (it's signed). Example
client usage to hand to the user:

```js
const { url, headers } = await fetch(presignEndpoint).then(r => r.json());
await fetch(url, { method: 'PUT', headers, body: file });
```

Policy is enforced server-side: keys must stay under the configured prefix,
methods and expiry are capped by the presigner. The signing key never leaves
Odapt — only short-lived signed URLs do.

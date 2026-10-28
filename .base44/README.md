# Base44 development environment

This repository is not a web app: it is an Android TV launcher (`launcher/`) plus a set of Python
ADB tools (`tools/`) and data (`examples/`, `themes/`, `addons/`). Base44's sandbox needs something
on host port 3000, so this compose file runs two services:

| Service | What it runs | Why |
|---|---|---|
| `preview` | `.base44/preview/server.py`, stdlib Python, on `0.0.0.0:3000` | Renders a read-only page from the repository's own Markdown tables and screenshots (themes, add-ons, tested TVs, tools). It is a sandbox preview surface, not product code. |
| `tools` | `tools/venv` with `tools/requirements.txt` installed, kept alive | Where the project's real work runs: `python -m unittest discover -s tests`, and the `tools/*.py` commands. |

```bash
docker compose -f docker-compose.base44.yml up -d --build
docker compose -f docker-compose.base44.yml ps
docker compose -f docker-compose.base44.yml exec -T tools tools/venv/bin/python -m unittest discover -s tests
```

## What does not run here

- **The launcher.** `launcher/` is an Android app (JDK 17, Android SDK platform 34, build-tools
  34.0.0). It builds with Gradle and is seen on a TV or an emulator, neither of which exists in this
  sandbox. `launcher/build-and-install.sh` needs a real TV.
- **The tools against a TV.** Every tool in `tools/` talks to network ADB on a TV in your own LAN
  (`TV_HOST`). A sandbox cannot reach it, so the tests run them against fake TVs only.
- **Nothing in this sandbox needs a credential.** There is no external service to sign into; the only
  value the tools read is `TV_HOST`, the TV's address on your own network, which is not a secret and
  cannot be used from here.

## Editing the preview page

`preview` has no file watcher: `server.py` re-reads the Markdown tables on every request, so table,
theme or data edits show up on a reload, but a change to `server.py` itself needs
`docker compose -f docker-compose.base44.yml restart preview`. No `BASE44_*` value is baked into any
file; nothing here depends on the sandbox's hostname or origin.

#!/usr/bin/env python3
"""Base44 development preview surface for this repository.

This repository is an Android TV launcher (`launcher/`) plus a set of Python ADB tools (`tools/`);
it has no web frontend of its own, and the launcher can only be seen on a real TV or an emulator.
This page exists only so the sandbox preview has something to show: it is generated from the
repository's own Markdown tables and screenshots, and it changes nothing about the product.
See `.base44/README.md`.
"""
import html
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ.get("CLEANYOURTV_ROOT", Path(__file__).resolve().parents[2])).resolve()
PORT = int(os.environ.get("PORT", "3000"))
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------- reading the repo

def table_rows(path):
    """Every Markdown table row in a file, as lists of stripped cells."""
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if len(line) > 2 and line.startswith("|") and line.endswith("|"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def clean(text):
    """A Markdown cell as plain text: no HTML, links, code ticks or emphasis."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").replace("**", "")
    return re.sub(r"\s+", " ", text).strip()


def image_in(cell):
    match = re.search(r'src="([^"]+)"', cell or "")
    return match.group(1) if match else None


def themes():
    found = []
    for cells in table_rows(ROOT / "themes" / "README.md"):
        if len(cells) < 3:
            continue
        name = re.match(r"`([^`]+)/`", cells[0])
        if not name:
            continue
        shot = image_in(cells[2])
        found.append({
            "name": name.group(1),
            "desc": clean(cells[1]),
            "img": f"themes/{shot}" if shot else None,
        })
    return found


def addons():
    found = []
    for cells in table_rows(ROOT / "addons" / "README.md"):
        if len(cells) < 2:
            continue
        link = re.match(r"\[[^\]]+\]\(([^)]+)\)", cells[0])
        if not link or not link.group(1).endswith("/"):
            continue
        shot = image_in(cells[-1]) or image_in(" ".join(cells))
        found.append({
            "name": clean(cells[0]),
            "desc": clean(cells[1]),
            "author": clean(cells[2]) if len(cells) > 2 else "",
            "tested": clean(cells[3]) if len(cells) > 3 else "",
            "img": f"addons/{shot}" if shot else None,
        })
    return found


def tools():
    found = []
    for cells in table_rows(ROOT / "README.md"):
        if len(cells) < 2 or not cells[0].startswith("[`tools/"):
            continue
        found.append({"name": clean(cells[0]), "desc": clean(cells[1])})
    return found


def tvs():
    found = []
    for path in sorted((ROOT / "examples").glob("*/tv.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        found.append({
            "tv": clean(str(data.get("tv", path.parent.name))),
            "os": clean(str(data.get("os", ""))),
            "brand": clean(str(data.get("brand", ""))),
        })
    found.sort(key=lambda tv: (tv["brand"].lower(), tv["tv"].lower()))
    return found


# ---------------------------------------------------------------- the page

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: #0a0d16; color: #e7ecf6;
  font: 16px/1.55 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
a { color: #7de2d1; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 40px 24px 72px; }
header.hero h1 { margin: 0 0 6px; font-size: 34px; letter-spacing: -0.02em; }
header.hero p.lede { margin: 0; max-width: 760px; color: #a9b4c9; font-size: 17px; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0 0; padding: 0; list-style: none; }
.chips li { background: #131a2a; border: 1px solid #23304a; border-radius: 999px;
  padding: 7px 15px; font-size: 14px; color: #c7d2e5; }
.chips b { color: #7de2d1; font-weight: 600; }
.beforeafter { margin: 32px 0 8px; border-radius: 16px; overflow: hidden; border: 1px solid #23304a; }
.beforeafter img { display: block; width: 100%; height: auto; }
.caption { margin: 10px 0 0; color: #7d879b; font-size: 13.5px; }
section { margin-top: 56px; }
section > h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.13em;
  color: #7de2d1; margin: 0 0 4px; }
section > p.sub { margin: 0 0 24px; color: #98a3b8; max-width: 780px; }
.grid { display: grid; gap: 22px; grid-template-columns: repeat(auto-fill, minmax(268px, 1fr)); }
.card { background: #101625; border: 1px solid #1f2a40; border-radius: 14px; overflow: hidden;
  display: flex; flex-direction: column; }
.card .shot { aspect-ratio: 16 / 9; background: #070a12; overflow: hidden; }
.card .shot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.card .body { padding: 15px 16px 18px; }
.card h3 { margin: 0 0 6px; font-size: 16.5px; }
.card h3 code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 15px;
  color: #b9c6dc; font-weight: 400; }
.card p { margin: 0; color: #9aa6bc; font-size: 14px; }
.card .meta { margin-top: 10px; color: #6f7b91; font-size: 12.5px; }
table { width: 100%; border-collapse: collapse; font-size: 14.5px; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #1b2437; vertical-align: top; }
th { color: #8b97ac; font-weight: 600; font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.07em; }
td.name { white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #cbd6e8; }
input[type="search"] { width: 100%; max-width: 380px; margin: 0 0 16px; padding: 10px 14px;
  background: #101625; border: 1px solid #23304a; border-radius: 10px; color: #e7ecf6; font-size: 15px; }
.scroller { max-height: 460px; overflow: auto; border: 1px solid #1f2a40; border-radius: 14px; }
pre { margin: 0; padding: 18px 20px; background: #0d1420; border: 1px solid #1f2a40; border-radius: 14px;
  overflow-x: auto; font: 13.5px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace; color: #c9d6e8; }
footer { margin-top: 64px; padding-top: 22px; border-top: 1px solid #1b2437; color: #6f7b91; font-size: 13px; }
@media (max-width: 640px) { .wrap { padding: 26px 16px 56px; } header.hero h1 { font-size: 26px; } }
"""

SEARCH_JS = """
document.querySelectorAll('input[type=search]').forEach(function (box) {
  box.addEventListener('input', function () {
    var q = box.value.trim().toLowerCase();
    document.querySelectorAll('[data-filter]').forEach(function (row) {
      row.hidden = q !== '' && row.textContent.toLowerCase().indexOf(q) === -1;
    });
  });
});
"""


def media_url(path):
    return "/media/" + path if path else ""


def cards(items, monospace_name=False):
    out = []
    for item in items:
        shot = ""
        if item["img"]:
            shot = ('<div class="shot"><img loading="lazy" src="%s" alt="%s">'
                    % (html.escape(media_url(item["img"])), html.escape(item["name"] + " screenshot")))
            shot += "</div>"
        name = ("<code>%s/</code>" % html.escape(item["name"])) if monospace_name else html.escape(item["name"])
        meta = item.get("meta")
        meta_html = '<div class="meta">%s</div>' % html.escape(meta) if meta else ""
        out.append(
            '<article class="card">%s<div class="body"><h3>%s</h3><p>%s</p>%s</div></article>'
            % (shot, name, html.escape(item["desc"]), meta_html)
        )
    return '<div class="grid">%s</div>' % "".join(out)


def build_page():
    theme_list = themes()
    addon_list = addons()
    tool_list = tools()
    tv_list = tvs()
    brands = {tv["brand"] for tv in tv_list if tv["brand"]}

    for addon in addon_list:
        bits = [b for b in (addon["author"], addon["tested"]) if b]
        addon["meta"] = " · ".join(bits)

    chips = "".join([
        "<li><b>%d</b> tested TVs</li>" % len(tv_list),
        "<li><b>%d</b> brands</li>" % len(brands),
        "<li><b>%d</b> themes</li>" % len(theme_list),
        "<li><b>%d</b> add-ons</li>" % len(addon_list),
        "<li><b>%d</b> tools</li>" % len(tool_list),
    ])

    theme_cards = cards(theme_list, monospace_name=True)
    addon_cards = cards(addon_list)

    tv_rows = "".join(
        '<tr data-filter><td class="name">%s</td><td>%s</td><td>%s</td></tr>'
        % (html.escape(tv["brand"]), html.escape(tv["tv"]), html.escape(tv["os"]))
        for tv in tv_list
    )

    tool_rows = "".join(
        '<tr data-filter><td class="name">%s</td><td>%s</td></tr>'
        % (html.escape(tool["name"]), html.escape(tool["desc"]))
        for tool in tool_list
    )

    hero = os.path.join("docs", "stock-vs-new.jpg")
    hero_html = ""
    if (ROOT / hero).is_file():
        hero_html = (
            '<div class="beforeafter"><img src="%s" alt="Stock Google TV home with a sponsored ad, '
            'and the same TV with the CleanYourTV launcher"></div>'
            '<p class="caption">Before and after, on a real TV.</p>' % html.escape(media_url(hero))
        )

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CleanYourTV — repository preview</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>CleanYourTV</h1>
    <p class="lede">Your TV, minus the ads: debloat any Android TV or Google TV over Wi-Fi and replace the
      ad-filled home screen with a clean launcher. No root, no cable, nothing uninstalled, and a one-line
      restore. Everything below is read from this checkout: the README tables, the themes, the add-ons and
      the tested-TV lists.</p>
    <ul class="chips">%s</ul>
  </header>

  %s

  <section>
    <h2>Themes</h2>
    <p class="sub">A theme is a folder with a <code>config.json</code>; pushing one changes the launcher's
      dock, layout and look on the TV without rebuilding the APK. Each picture below is Home with that
      theme on a real TV.</p>
    %s
  </section>

  <section>
    <h2>Add-ons</h2>
    <p class="sub">Small optional apps that plug in as a module card. The launcher never depends on them.</p>
    %s
  </section>

  <section>
    <h2>Tested TVs</h2>
    <p class="sub">%d models, each with its own debloat list in <code>examples/</code>.</p>
    <input type="search" placeholder="Filter by brand, model or Android version" aria-label="Filter TVs">
    <div class="scroller"><table>
      <thead><tr><th>Brand</th><th>Model</th><th>OS</th></tr></thead>
      <tbody>%s</tbody>
    </table></div>
  </section>

  <section>
    <h2>Tools</h2>
    <p class="sub">The Python tools that talk to the TV over network ADB. They need a TV on your own
      network (<code>TV_HOST</code>), which a sandbox cannot reach.</p>
    <div class="scroller"><table>
      <thead><tr><th>Tool</th><th>What it does</th></tr></thead>
      <tbody>%s</tbody>
    </table></div>
  </section>

  <section>
    <h2>Quick start</h2>
    <p class="sub">From the repository README.</p>
    <pre>python3 -m venv tools/venv &amp;&amp; tools/venv/bin/pip install -r tools/requirements.txt
export TV_HOST=192.168.1.50

tools/venv/bin/python -I tools/tv.py --probe                 # model, Android version, firmware
tools/disable.sh examples/xiaomi-mi-tv-4a/debloat.txt        # apply a debloat list
tools/theme.sh themes/aurora                                 # push a theme
TV_HOST=$TV_HOST launcher/build-and-install.sh               # build the launcher, make it Home
tools/restore.sh examples/xiaomi-mi-tv-4a/debloat.txt        # undo it all</pre>
  </section>

  <footer>
    Base44 development preview surface. This repository has no web frontend of its own: the product is the
    Android launcher in <code>launcher/</code> and the ADB tools in <code>tools/</code>, so this page is
    generated from the repository's own Markdown tables and screenshots. The Python tooling in the
    <code>tools</code> service is set up and running beside it.
  </footer>
</div>
<script>%s</script>
</body>
</html>
""" % (
        CSS,
        chips,
        hero_html,
        theme_cards,
        addon_cards,
        len(tv_list),
        tv_rows,
        tool_rows,
        SEARCH_JS,
    )


# ---------------------------------------------------------------- serving it

class Handler(BaseHTTPRequestHandler):
    server_version = "CleanYourTVPreview/1.0"

    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])

        if path in ("/", "/index.html"):
            try:
                page = build_page()
            except Exception as exc:  # a broken table must not take the preview down
                self.send_body(500, ("preview error: %s" % exc).encode("utf-8"),
                               "text/plain; charset=utf-8")
                return
            self.send_body(200, page.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path.startswith("/media/"):
            try:
                target = (ROOT / path[len("/media/"):]).resolve()
            except OSError:
                target = None
            if target and target.is_file() and target.suffix.lower() in MEDIA_EXT and ROOT in target.parents:
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                self.send_body(200, target.read_bytes(), content_type)
                return

        self.send_body(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("preview of %s on http://0.0.0.0:%d" % (ROOT, PORT), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

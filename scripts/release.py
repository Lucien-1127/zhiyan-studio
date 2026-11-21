"""Build the public assets and verify the exact release served by GitHub Pages."""

import argparse
from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
INDEX = ROOT / "index.html"
START = "  <!-- release-assets:start -->"
END = "  <!-- release-assets:end -->"


def asset_bundle():
    styles = b"\n".join((SOURCE / name).read_bytes() for name in ("base.css", "style.css"))
    files = {}
    for extension, body in [("css", styles), ("js", (SOURCE / "app.js").read_bytes())]:
        name = f"assets/site-{sha256(body).hexdigest()[:16]}.{extension}"
        files[name] = body
    return files


def with_asset_links(html, files):
    if html.count(START) != 1 or html.count(END) != 1:
        raise ValueError("index.html must have one release-assets block")
    prefix, rest = html.split(START)
    _, suffix = rest.split(END)
    css, js = files
    block = f'  <link rel="stylesheet" href="./{css}">\n  <script src="./{js}" defer></script>'
    return f"{prefix}{START}\n{block}\n{END}{suffix}"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()
        self.targets = set()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids[attrs["id"]] += 1
        for name in ("aria-controls", "aria-labelledby", "aria-describedby", "for"):
            self.targets.update((attrs.get(name) or "").split())
        for name in ("href", "src"):
            url = urlsplit(attrs.get(name) or "")
            if url.scheme or url.netloc:
                continue
            if url.path:
                self.paths.add(url.path.removeprefix("./").lstrip("/"))
            elif url.fragment:
                self.targets.add(url.fragment)
        if attrs.get("property") == "og:image":
            url = urlsplit(attrs["content"])
            if url.hostname == "lucien126.com":
                self.paths.add(url.path.lstrip("/"))


def check_page(html):
    refs = References()
    refs.feed(html)
    duplicates = [key for key, count in refs.ids.items() if count > 1]
    missing = sorted(refs.targets.difference(refs.ids))
    if duplicates or missing:
        raise ValueError(f"duplicate IDs: {duplicates}, missing targets: {missing}")
    for path in sorted(refs.paths):
        if not (ROOT / path).is_file():
            raise ValueError(f"missing local resource: {path}")
    return refs.paths


def verify_live(base, paths):
    for path in ["index.html", *sorted(paths)]:
        url = urljoin(base.rstrip("/") + "/", "" if path == "index.html" else path)
        request = Request(url, headers={"User-Agent": "Zhiyan-release-check/1.0", "Accept-Encoding": "identity"})
        with urlopen(request, timeout=35) as response:
            body = response.read()
            if response.status != 200 or body != (ROOT / path).read_bytes():
                raise ValueError(f"{url} does not match this release")
            print(f"{response.status}  {len(body):6} B  {sha256(body).hexdigest()[:16]}  "
                  f"{response.headers.get('Cache-Control', 'no Cache-Control')}  {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "check", "verify-live"))
    parser.add_argument("--url", default="https://lucien126.com/")
    args = parser.parse_args()
    html = INDEX.read_text(encoding="utf-8")
    files = asset_bundle()
    updated = with_asset_links(html, files)
    if args.action == "build":
        for name, body in files.items():
            (ROOT / name).write_bytes(body)
        INDEX.write_text(updated, encoding="utf-8")
    elif updated != html or any(not (ROOT / name).is_file() or
                                (ROOT / name).read_bytes() != body for name, body in files.items()):
        raise ValueError("stale assets or index.html; run python3 scripts/release.py build")
    paths = check_page(updated)
    if args.action == "verify-live":
        verify_live(args.url, paths)
    else:
        print("Verified HTML targets and local resources:", ", ".join(sorted(paths)))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error

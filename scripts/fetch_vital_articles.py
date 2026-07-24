#!/usr/bin/env python3
"""Fetches Wikipedia's "Vital Articles" Level 1, 2 and 3 lists and writes a
deduplicated, alphabetized JSON array of article titles suitable for
wikiman's curated title pool. Standard library only.

Usage: python scripts/fetch_vital_articles.py [output-path]
Default output: scripts/vital-articles.json
"""

import json
import re
import sys
import urllib.parse
import urllib.request

PAGES = [
    "Wikipedia:Vital articles/Level 1",
    "Wikipedia:Vital articles/Level 2",
    "Wikipedia:Vital articles/Level 3",
]

NAMESPACE_PATTERN = re.compile(
    r"^(File|Image|Category|Wikipedia|WP|User|Template|Help|Portal|Module"
    r"|MediaWiki|Draft|TimedText|Special|Media)( talk)?:|^Talk:",
    re.IGNORECASE,
)

LINK_PATTERN = re.compile(r"\[\[([^\]]*)\]\]")

API_URL = "https://en.wikipedia.org/w/api.php"


def fetch_wikitext(title):
    query = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
    }
    url = API_URL + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": "wikiman-vital-articles-script"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = json.load(res)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise RuntimeError(f'No page found for "{title}"')
    revisions = pages[0].get("revisions")
    if not revisions:
        raise RuntimeError(f'No wikitext found for "{title}"')
    return revisions[0]["slots"]["main"]["content"]


def extract_article_titles(wikitext):
    titles = []
    for match in LINK_PATTERN.finditer(wikitext):
        target = match.group(1).split("|")[0].split("#")[0].strip()
        if target.startswith(":"):
            target = target[1:]
        if not target:
            continue
        if NAMESPACE_PATTERN.match(target):
            continue
        if not re.search(r"[A-Za-z]", target):
            continue  # drop titles with no letters (e.g. "0")
        titles.append(target)
    return titles


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/vital-articles.json"

    seen = set()
    for page in PAGES:
        print(f"Fetching {page}...", file=sys.stderr)
        wikitext = fetch_wikitext(page)
        seen.update(extract_article_titles(wikitext))

    titles = sorted(seen)
    print(f"Collected {len(titles)} unique article titles.", file=sys.stderr)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(titles, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

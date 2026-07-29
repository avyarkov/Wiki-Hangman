#!/usr/bin/env python3
"""Fetches Google Books Ngram frequency (mentions per million words, averaged over
2015-2019) for each title, as a tiebreak signal for borderline-obscure topics.

Parenthetical disambiguators are stripped, since "Mass (music)" is never written
that way in print. Phrases longer than five words are skipped -- the Ngram corpus
only indexes up to 5-grams -- and recorded as null rather than zero.

Usage: python scripts/fetch_ngrams.py <titles.json> <out.json>
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

URL = "https://books.google.com/ngrams/json"
THROTTLE = 1.2
USER_AGENT = "Mozilla/5.0 (compatible; wikiguesser-ngrams/1.0)"


def phrase(title):
    p = re.sub(r"\s*\(.*?\)", "", title).strip()
    return p if 1 <= len(p.split()) <= 5 else None


def fetch(p):
    q = {
        "content": p,
        "year_start": 2015,
        "year_end": 2019,
        "corpus": "en-2019",
        "smoothing": 3,
    }
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.load(res)
            time.sleep(THROTTLE)
            if not data:
                return 0.0
            ts = data[0].get("timeseries") or []
            return (sum(ts) / len(ts) * 1e6) if ts else 0.0
        except Exception as exc:  # noqa: BLE001
            if attempt == 4:
                print(f"  give up on {p!r}: {exc}", file=sys.stderr)
                return None
            time.sleep(5 * (attempt + 1))
    return None


def main():
    titles = json.load(open(sys.argv[1], encoding="utf-8"))
    out_path = sys.argv[2]
    try:
        out = json.load(open(out_path, encoding="utf-8"))
    except (OSError, ValueError):
        out = {}

    todo = [t for t in titles if t not in out]
    print(f"{len(todo)} of {len(titles)} still need ngrams", file=sys.stderr)
    for i, t in enumerate(todo, 1):
        p = phrase(t)
        out[t] = None if p is None else fetch(p)
        if i % 25 == 0 or i == len(todo):
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
            print(f"  {i}/{len(todo)}", file=sys.stderr)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()

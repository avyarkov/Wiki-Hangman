#!/usr/bin/env python3
"""Marks which titles are biographies, by asking Wikidata whether the linked
entity is an instance of human (P31 -> Q5).

Name-shaped heuristics cannot tell "Marie Curie" from "Milky Way", so the
person list is confirmed against structured data rather than guessed.

Usage: python scripts/fetch_is_human.py <titles.json> <out.json>
"""

import json
import sys
import time
import urllib.parse
import urllib.request

API_URL = "https://www.wikidata.org/w/api.php"
BATCH = 25  # full claim payloads are heavy; keep batches small
THROTTLE = 1.0
USER_AGENT = "wikiguesser-ishuman/1.0 (title pool curation for a word game)"


def api_get(params):
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                out = json.load(res)
            time.sleep(THROTTLE)
            return out
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 5:
                raise
            wait = int(exc.headers.get("Retry-After") or 0) or 15 * (attempt + 1)
            print(f"  rate limited, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001
            if attempt == 5:
                raise
            print(f"  retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def main():
    titles = json.load(open(sys.argv[1], encoding="utf-8"))
    out_path = sys.argv[2]
    try:
        flags = json.load(open(out_path, encoding="utf-8"))
    except (OSError, ValueError):
        flags = {}

    todo = [t for t in titles if t not in flags]
    print(f"{len(todo)} of {len(titles)} still unchecked", file=sys.stderr)

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        data = api_get(
            {
                "action": "wbgetentities",
                "sites": "enwiki",
                "titles": "|".join(batch),
                "props": "claims|sitelinks",
                "sitefilter": "enwiki",
                "format": "json",
            }
        )
        for ent in (data.get("entities") or {}).values():
            title = ((ent.get("sitelinks") or {}).get("enwiki") or {}).get("title")
            if not title:
                continue
            p31 = (ent.get("claims") or {}).get("P31") or []
            ids = {
                (c.get("mainsnak", {}).get("datavalue", {}).get("value") or {}).get("id")
                for c in p31
            }
            flags[title] = "Q5" in ids
        for t in batch:
            flags.setdefault(t, False)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(flags, f, ensure_ascii=False)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}", file=sys.stderr)

    print(f"done. {sum(1 for x in flags.values() if x)} humans", file=sys.stderr)


if __name__ == "__main__":
    main()

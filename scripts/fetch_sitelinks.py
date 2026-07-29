#!/usr/bin/env python3
"""Fetches the number of Wikimedia language editions that carry each article
(Wikidata sitelink count) and writes {title: count} as JSON.

Sitelinks complement pageviews: views measure current interest, sitelinks measure
global reach. A word like "Paintbrush" gets few views but exists in ~57 languages,
which is the signal that it is common knowledge rather than obscure.

Usage: python scripts/fetch_sitelinks.py <titles.json> <out.json>
"""

import json
import sys
import time
import urllib.parse
import urllib.request

API_URL = "https://www.wikidata.org/w/api.php"
BATCH = 50
THROTTLE = 1.0
USER_AGENT = "wikiguesser-sitelinks/1.0 (title pool curation for a word game)"


def api_get(params):
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=40) as res:
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
        counts = json.load(open(out_path, encoding="utf-8"))
    except (OSError, ValueError):
        counts = {}

    todo = [t for t in titles if t not in counts]
    print(f"{len(todo)} of {len(titles)} titles still need sitelinks", file=sys.stderr)

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        data = api_get(
            {
                "action": "wbgetentities",
                "sites": "enwiki",
                "titles": "|".join(batch),
                "props": "sitelinks",
                "format": "json",
            }
        )
        for ent in (data.get("entities") or {}).values():
            sl = ent.get("sitelinks") or {}
            en = sl.get("enwiki", {}).get("title")
            if en:
                # count only language Wikipedias, not commons/wikiquote/etc.
                counts[en] = len([k for k in sl if k.endswith("wiki") and k != "commonswiki"])
        # anything the API could not resolve gets 0 so it is not retried forever
        for t in batch:
            counts.setdefault(t, 0)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(counts, f, ensure_ascii=False)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}", file=sys.stderr)

    print(f"done. {len(counts)} scored", file=sys.stderr)


if __name__ == "__main__":
    main()

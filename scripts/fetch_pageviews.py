#!/usr/bin/env python3
"""Fetches 60-day English Wikipedia pageview totals for every title in a JSON
title list and writes {title: views} as JSON.

Pageviews are the best cheap proxy for "would an average person know this?" --
they measure how often real people actually look a subject up.

Usage: python scripts/fetch_pageviews.py <titles.json> <out.json>
"""

import json
import sys
import time
import urllib.parse
import urllib.request

API_URL = "https://en.wikipedia.org/w/api.php"
BATCH = 50
THROTTLE = 1.0
USER_AGENT = "wikiguesser-popularity/1.0 (title pool curation for a word game)"


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
        views = json.load(open(out_path, encoding="utf-8"))
    except (OSError, ValueError):
        views = {}

    todo = [t for t in titles if t not in views]
    print(f"{len(todo)} of {len(titles)} titles still need pageviews", file=sys.stderr)

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        data = api_get(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "pageviews",
                "pvipdays": "60",
                "titles": "|".join(batch),
            }
        )
        query = data.get("query", {})
        # requested title -> returned title, so normalisation does not lose entries
        back = {n["to"]: n["from"] for n in query.get("normalized", [])}
        for page in query.get("pages", []):
            # The API intermittently omits "pageviews" entirely for a batch. Recording
            # those as 0 would silently mark famous articles as obscure, so leave them
            # missing and let the next run retry them.
            if "pageviews" not in page:
                continue
            pv = page.get("pageviews") or {}
            total = sum(v for v in pv.values() if v)
            title = page.get("title", "")
            views[back.get(title, title)] = total
            if title in back:
                views[title] = total
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(views, f, ensure_ascii=False)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}", file=sys.stderr)

    missing = [t for t in titles if t not in views]
    print(f"done. {len(views)} scored, {len(missing)} missing", file=sys.stderr)


if __name__ == "__main__":
    main()

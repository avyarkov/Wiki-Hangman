#!/usr/bin/env python3
"""Renders the curation audit table: one row per candidate title, sorted by
pageviews descending, with the signals used to keep or cut it.

Columns are fixed-width and space-padded rather than tab-separated, so the file
reads as a table in any editor. Parse it by column offset, not by splitting on
runs of spaces -- an empty metric cell collapses the separators.

  views   60-day English Wikipedia pageview total
  langs   Wikidata sitelink count (how many language editions carry the article)
  letters distinct a-z letters in the title, i.e. how many of the game's 26 keys
          the puzzle can actually use
  status  kept / the reason it was dropped

Usage: python scripts/make_metrics_table.py <all-titles.json> <views.json>
                                            <sitelinks.json> <kept.json> <out.txt>
                                            [--reasons <reasons.json>]
"""

import json
import re
import sys


def distinct_letters(title):
    # a-z only, case-insensitive: exactly what the game's A-Z keyboard can guess.
    # Accented characters are not guessable and reveal for free, so they do not count.
    return len(set(re.findall(r"[a-z]", title.lower())))


def main():
    args = sys.argv[1:]
    reasons = {}
    if "--reasons" in args:
        i = args.index("--reasons")
        reasons = json.load(open(args[i + 1], encoding="utf-8"))
        args = args[:i] + args[i + 2 :]

    all_titles, views_path, links_path, kept_path, out_path = args
    titles = json.load(open(all_titles, encoding="utf-8"))
    views = json.load(open(views_path, encoding="utf-8"))
    links = json.load(open(links_path, encoding="utf-8"))
    kept = set(json.load(open(kept_path, encoding="utf-8")))

    rows = []
    for t in titles:
        rows.append(
            (
                views.get(t, 0),
                links.get(t, 0),
                distinct_letters(t),
                "kept" if t in kept else reasons.get(t, "cut"),
                t,
            )
        )
    rows.sort(key=lambda r: (-r[0], r[4].lower()))

    width = max(len(r[3]) for r in rows)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"{len(rows)} candidates, {len(kept)} kept\n\n")
        f.write(f"{'views/60d':>10}  {'langs':>5}  {'letters':>7}  {'status':<{width}}  title\n")
        f.write(f"{'-' * 10}  {'-' * 5}  {'-' * 7}  {'-' * width}  {'-' * 40}\n")
        for v, l, n, status, t in rows:
            f.write(f"{v:>10}  {l:>5}  {n:>7}  {status:<{width}}  {t}\n")
    print(f"wrote {out_path}: {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()

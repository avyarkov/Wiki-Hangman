#!/usr/bin/env python3
"""Validates candidate article titles against the live English Wikipedia API and
writes a deduplicated, alphabetized JSON array of canonical titles.

Drops titles that are missing, disambiguation pages, or lack a usable intro
extract (the game needs an extract to mask). Redirects are resolved to their
canonical target so the puzzle word is the real article title.

Usage: python scripts/validate_titles.py <input.txt> [<input.txt> ...] -o out.json
Input files are plain text, one candidate title per line; blank lines and lines
starting with # are ignored.
"""

import json
import sys
import time
import urllib.parse
import urllib.request

API_URL = "https://en.wikipedia.org/w/api.php"
BATCH = 20  # exlimit cap for non-bot clients
MIN_EXTRACT_CHARS = 60
THROTTLE = 1.0  # seconds between requests; the API 429s on bursts
USER_AGENT = "wikiguesser-title-validator/1.0 (educational hangman game title check)"


def api_get(params):
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                out = json.load(res)
            time.sleep(THROTTLE)
            return out
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 5:
                raise
            wait = int(exc.headers.get("Retry-After") or 0) or 15 * (attempt + 1)
            print(f"  rate limited, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001 - retry on any transport hiccup
            if attempt == 5:
                raise
            print(f"  retry {attempt + 1} after {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def check_batch(titles):
    """Returns (accepted_canonical_titles, rejects) for one batch."""
    data = api_get(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": "|".join(titles),
            "redirects": "1",
            "prop": "pageprops|extracts",
            "ppprop": "disambiguation",
            "exintro": "1",
            "explaintext": "1",
            "exlimit": str(BATCH),
        }
    )
    query = data.get("query", {})

    # map canonical title -> the original candidate(s) that led there
    origin = {}
    for norm in query.get("normalized", []):
        origin[norm["to"]] = norm["from"]
    for red in query.get("redirects", []):
        origin[red["to"]] = origin.get(red["from"], red["from"])

    accepted, rejects = [], []
    for page in query.get("pages", []):
        title = page.get("title", "")
        src = origin.get(title, title)
        if page.get("missing"):
            rejects.append((src, "missing"))
            continue
        if page.get("ns") != 0:
            rejects.append((src, "not an article"))
            continue
        if (page.get("pageprops") or {}).get("disambiguation") is not None:
            rejects.append((src, "disambiguation"))
            continue
        extract = (page.get("extract") or "").strip()
        if len(extract) < MIN_EXTRACT_CHARS:
            rejects.append((src, "no usable extract"))
            continue
        accepted.append((title, src))
    return accepted, rejects


def main():
    args = sys.argv[1:]
    if "-o" not in args:
        print(__doc__, file=sys.stderr)
        return 1
    split = args.index("-o")
    inputs, out_path = args[:split], args[split + 1]

    candidates = []
    seen_input = set()
    for path in inputs:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # MediaWiki ignores the case of the first character only, so
                # normalise just that when deduplicating. Folding the whole
                # title would collide an acronym with an ordinary word and
                # silently drop one of two genuinely different articles --
                # ACID vs Acid, ALGOL vs Algol, Stack overflow vs Stack Overflow.
                key = line[0].upper() + line[1:]
                if key in seen_input:
                    continue
                seen_input.add(key)
                candidates.append(line)
    print(f"{len(candidates)} unique candidates from {len(inputs)} file(s)", file=sys.stderr)

    # Resume support: batches already checked are cached on disk, so a rate-limit
    # abort halfway through does not throw away an hour of API calls.
    cache_path = out_path.rsplit(".", 1)[0] + "-cache.json"
    try:
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}

    accepted, rejects, redirected = {}, [], []
    for i in range(0, len(candidates), BATCH):
        batch = candidates[i : i + BATCH]
        key = "\n".join(batch)
        if key in cache:
            ok, bad = [tuple(x) for x in cache[key][0]], [tuple(x) for x in cache[key][1]]
        else:
            ok, bad = check_batch(batch)
            cache[key] = [ok, bad]
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        for title, src in ok:
            if title in accepted:
                redirected.append((src, title, "duplicate of " + accepted[title]))
                continue
            accepted[title] = src
            if title != src:
                redirected.append((src, title, "redirect"))
        rejects.extend(bad)
        done = min(i + BATCH, len(candidates))
        print(f"  {done}/{len(candidates)} checked, {len(accepted)} kept", file=sys.stderr)

    titles = sorted(accepted, key=lambda s: s.lower())
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(titles, f, ensure_ascii=False, indent=4)
        f.write("\n")

    report = out_path.rsplit(".", 1)[0] + "-report.txt"
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"kept: {len(titles)}\nrejected: {len(rejects)}\n\n== REJECTED ==\n")
        for src, why in sorted(rejects):
            f.write(f"{src}\t{why}\n")
        f.write("\n== RESOLVED / MERGED ==\n")
        for src, title, why in sorted(redirected):
            f.write(f"{src}\t->\t{title}\t({why})\n")

    print(f"\nWrote {out_path}: {len(titles)} titles ({len(rejects)} rejected)", file=sys.stderr)
    print(f"Report: {report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

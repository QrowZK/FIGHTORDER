#!/usr/bin/env python3
"""
Export pages (with full history) from the Spring RTS wiki as MediaWiki XML
dumps, ready for importDump.php on Fightorder.

Enumerates pages via the API (paginated), then downloads full-history XML in
batches via Special:Export's GET form (the POST/token path is disabled on the
source, but `?pages=A%0AB&history=1&action=submit` works and returns valid
<mediawiki> import XML).

The source's own "Main Page" and the entire MediaWiki namespace are never
exported, so Fightorder's themed Main Page and MediaWiki:Common.css are safe.

Usage:
  export_spring.py --out dump [--namespaces 0,4,10,12,14] [--batch 25]
                   [--limit N] [--delay 1.5]
"""
import argparse, os, sys, time, urllib.parse, urllib.request, json

API = "https://springrts.com/mediawiki/api.php"
EXPORT = "https://springrts.com/wiki/Special:Export"
UA = "FightorderWikiPort/1.0 (one-time migration; contact admin@fightorder.net)"

# Titles we must never pull in (would collide with Fightorder's own pages).
EXCLUDE_TITLES = {"Main Page"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def enumerate_titles(namespaces):
    titles = []
    for ns in namespaces:
        apcontinue = None
        while True:
            q = {
                "action": "query", "list": "allpages", "apnamespace": str(ns),
                "aplimit": "500", "format": "json",
            }
            if apcontinue:
                q["apcontinue"] = apcontinue
            data = json.loads(get(API + "?" + urllib.parse.urlencode(q)))
            for p in data["query"]["allpages"]:
                t = p["title"]
                if t not in EXCLUDE_TITLES:
                    titles.append(t)
            cont = data.get("continue", {}).get("apcontinue")
            if not cont:
                break
            apcontinue = cont
            time.sleep(0.3)
        print(f"  ns {ns}: cumulative {len(titles)} titles", file=sys.stderr)
    return titles


def export_batches(titles, out_dir, batch, delay):
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        pages = "%0A".join(urllib.parse.quote(t, safe="") for t in chunk)
        # No templates=1: the Template namespace is exported wholesale, so
        # pulling each page's templates here would just duplicate them.
        url = f"{EXPORT}?pages={pages}&history=1&action=submit"
        xml = get(url)
        if not xml.lstrip().startswith("<mediawiki"):
            raise SystemExit(f"batch {n}: unexpected response (not export XML)")
        n += 1
        path = os.path.join(out_dir, f"spring_{n:04d}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"  wrote {path}  ({xml.count('<page>')} pages, "
              f"{xml.count('<revision>')} revisions)", file=sys.stderr)
        time.sleep(delay)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dump")
    ap.add_argument("--namespaces", default="0,4,10,12,14")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--limit", type=int, default=0, help="cap titles (testing)")
    ap.add_argument("--delay", type=float, default=1.5)
    a = ap.parse_args()

    namespaces = [int(x) for x in a.namespaces.split(",") if x != ""]
    print("Enumerating titles...", file=sys.stderr)
    titles = enumerate_titles(namespaces)
    # de-dupe preserving order
    seen, uniq = set(), []
    for t in titles:
        if t not in seen:
            seen.add(t); uniq.append(t)
    titles = uniq
    if a.limit:
        titles = titles[:a.limit]
    print(f"Total titles to export: {len(titles)}", file=sys.stderr)
    with open(os.path.join(".", "spring_titles.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(titles) + "\n")
    count = export_batches(titles, a.out, a.batch, a.delay)
    print(f"Done: {count} XML batch file(s) in {a.out}/", file=sys.stderr)


if __name__ == "__main__":
    main()

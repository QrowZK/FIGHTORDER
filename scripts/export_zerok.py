#!/usr/bin/env python3
"""
Export pages (with full history) from the Zero-K wiki (zero-k.info/mediawiki,
MediaWiki 1.34.1, CC BY-SA) as MediaWiki XML dumps, ready for importDump.php
on Fightorder.

Same mechanism as scripts/export_spring.py: enumerate via the API, download
full-history XML in batches via Special:Export's GET form (?pages=A%0AB&
history=1&action=submit).

Ten titles collide with existing Fightorder (Spring-sourced) pages —
generic RTS-wiki terms both communities independently use (Commander, FAQ,
Glossary, Units, ...). Those are disambiguated to "Title (Zero-K)" on
import, and internal wikilinks referencing them (within the exported
content itself) are rewritten to match, so nothing silently resolves to
Spring's unrelated same-named page. None of the ten are also template
names (checked separately), so only [[wikilink]] syntax needs rewriting,
not {{template}} invocations.

The source wiki's own "Main Page" is excluded — Fightorder ships its own
themed Zero-K portal in its place, same treatment as the Spring/Recoil
imports.

Usage:
  export_zerok.py --out dump [--namespaces 0,4,10,12,14,828] [--batch 20]
                  [--limit N] [--delay 1.5]
"""
import argparse, os, re, sys, time, urllib.parse, urllib.request, json

API = "https://zero-k.info/mediawiki/api.php"
EXPORT = "https://zero-k.info/mediawiki/Special:Export"
UA = "FightorderWikiPort/1.0 (one-time migration; contact admin@fightorder.net)"

EXCLUDE_TITLES = {"Main Page"}

# Collides with an existing Fightorder (Spring-sourced) page; disambiguate.
COLLIDE = ["Changelog", "Commander", "Elmo", "FAQ", "Glossary", "HLT", "LLT",
           "Lua Beginners FAQ", "Media", "Units"]
DISAMBIG_SUFFIX = " (Zero-K)"


def get(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"request failed after retries: {last} ({url})")


def enumerate_titles(namespaces):
    titles = []
    for ns in namespaces:
        apcontinue = None
        while True:
            q = {"action": "query", "list": "allpages", "apnamespace": str(ns),
                 "aplimit": "500", "format": "json"}
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


def build_link_rewrite_patterns():
    """One compiled regex per colliding title, matching [[Title ...,
    case-insensitive on the first letter only (MediaWiki link normalisation),
    exact thereafter, up to the link's |, #, or closing ]]."""
    pats = []
    for title in COLLIDE:
        first, rest = title[0], re.escape(title[1:])
        charclass = f"[{re.escape(first.lower())}{re.escape(first.upper())}]"
        pat = re.compile(rf"\[\[({charclass}{rest})(\||#|\]\])")
        pats.append((pat, title))
    return pats

LINK_PATTERNS = build_link_rewrite_patterns()


def rewrite_internal_links(xml_text):
    def sub(m):
        return f"[[{m.group(1)}{DISAMBIG_SUFFIX}{m.group(2)}"
    for pat, _title in LINK_PATTERNS:
        xml_text = pat.sub(sub, xml_text)
    return xml_text


def rewrite_titles(xml_text):
    """Disambiguate <title>Title</title> for the ten colliding pages."""
    for title in COLLIDE:
        xml_text = xml_text.replace(
            f"<title>{title}</title>",
            f"<title>{title}{DISAMBIG_SUFFIX}</title>",
        )
    return xml_text


def export_batches(titles, out_dir, batch, delay):
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        pages = "%0A".join(urllib.parse.quote(t, safe="") for t in chunk)
        url = f"{EXPORT}?pages={pages}&history=1&action=submit"
        xml = get(url)
        if not xml.lstrip().startswith("<mediawiki"):
            raise SystemExit(f"batch {n}: unexpected response (not export XML)")
        xml = rewrite_internal_links(xml)
        xml = rewrite_titles(xml)
        n += 1
        path = os.path.join(out_dir, f"zerok_{n:04d}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"  wrote {path}  ({xml.count('<page>')} pages, "
              f"{xml.count('<revision>')} revisions)", file=sys.stderr)
        time.sleep(delay)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dump")
    ap.add_argument("--namespaces", default="0,4,10,12,14,828")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    a = ap.parse_args()

    namespaces = [int(x) for x in a.namespaces.split(",") if x != ""]
    print("Enumerating titles...", file=sys.stderr)
    titles = enumerate_titles(namespaces)
    seen, uniq = set(), []
    for t in titles:
        if t not in seen:
            seen.add(t); uniq.append(t)
    titles = uniq
    if a.limit:
        titles = titles[:a.limit]
    print(f"Total titles to export: {len(titles)}", file=sys.stderr)
    with open("zerok_titles.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(titles) + "\n")
    count = export_batches(titles, a.out, a.batch, a.delay)
    print(f"Done: {count} XML batch file(s) in {a.out}/", file=sys.stderr)


if __name__ == "__main__":
    main()

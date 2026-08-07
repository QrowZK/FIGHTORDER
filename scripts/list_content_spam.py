#!/usr/bin/env python3
"""
Enumerate spam mainspace (ns 0) articles created by bot accounts on
Fightorder and write:
  out/content_spam_pages.txt  — page titles to delete
  out/content_spam_users.txt  — usernames to block

Unlike User-namespace sign-up spam, these are actual SEO/adult/gambling
articles the bots posted as content. Detection: walk recentchanges (type=new,
ns=0) and flag every creator not in ALLOWLIST — the wiki has a small, known
set of real human/deploy editors, so anyone else creating a mainspace page
is a bot.

Usage: list_content_spam.py [--out out] [--api URL]
"""
import argparse, os, sys, urllib.parse, urllib.request, json, time

UA = "FightorderSpamCleanup/1.0 (admin@fightorder.net)"
# Real editors / deploy accounts to never touch.
ALLOWLIST = {"FightorderAdmin", "Qrow", "KelseySowden", "MediaWiki default"}


def get(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"request failed after retries: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--api", default="https://fightorder.net/api.php")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    entries, rccontinue = [], None
    while True:
        q = {"action": "query", "list": "recentchanges", "format": "json",
             "rcprop": "title|user|timestamp", "rclimit": "500",
             "rctype": "new", "rcnamespace": "0"}
        if rccontinue:
            q["rccontinue"] = rccontinue
        d = get(a.api + "?" + urllib.parse.urlencode(q))
        entries += d["query"]["recentchanges"]
        rccontinue = d.get("continue", {}).get("rccontinue")
        if not rccontinue:
            break

    spam = [e for e in entries if e["user"] not in ALLOWLIST]
    pages = [e["title"] for e in spam]
    users = sorted({e["user"] for e in spam})

    with open(os.path.join(a.out, "content_spam_pages.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(pages) + ("\n" if pages else ""))
    with open(os.path.join(a.out, "content_spam_users.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(users) + ("\n" if users else ""))

    print(f"mainspace pages scanned : {len(entries)}", file=sys.stderr)
    print(f"  spam pages            : {len(pages)}", file=sys.stderr)
    print(f"  distinct spam users   : {len(users)}", file=sys.stderr)
    print("  sample spam           :", pages[:8], file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Enumerate spam User-namespace pages (bot sign-ups) on Fightorder and write:
  out/spam_pages.txt  — page titles to delete   (User:Foo)
  out/spam_users.txt  — usernames to block      (Foo)

The User namespace was never imported (the Spring migration only brought in
namespaces 0/4/10/12/14), so every User page is a post-launch bot sign-up.
Anything in ALLOWLIST is preserved.

Usage: list_user_spam.py [--out out] [--api URL]
"""
import argparse, os, sys, time, urllib.parse, urllib.request, json

UA = "FightorderSpamCleanup/1.0 (admin@fightorder.net)"
# Real accounts to never touch (page title form).
ALLOWLIST = {"User:FightorderAdmin"}


def get(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # transient TLS/connection resets
            last = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"request failed after retries: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--api", default="https://fightorder.net/api.php")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    titles, apcontinue = [], None
    while True:
        q = {"action": "query", "list": "allpages", "apnamespace": "2",
             "aplimit": "500", "format": "json"}
        if apcontinue:
            q["apcontinue"] = apcontinue
        d = get(a.api + "?" + urllib.parse.urlencode(q))
        titles += [p["title"] for p in d["query"]["allpages"]]
        apcontinue = d.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break

    spam = [t for t in titles if t not in ALLOWLIST]
    kept = [t for t in titles if t in ALLOWLIST]
    # username = title without the "User:" prefix (base user page only; skip
    # subpages so we don't try to block "Foo/subpage" as a username)
    users = sorted({t.split(":", 1)[1] for t in spam if "/" not in t.split(":", 1)[1]})

    with open(os.path.join(a.out, "spam_pages.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(spam) + ("\n" if spam else ""))
    with open(os.path.join(a.out, "spam_users.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(users) + ("\n" if users else ""))

    print(f"User pages total : {len(titles)}", file=sys.stderr)
    print(f"  preserved      : {len(kept)} {sorted(kept)}", file=sys.stderr)
    print(f"  spam pages      : {len(spam)}", file=sys.stderr)
    print(f"  distinct users  : {len(users)}", file=sys.stderr)
    print("  sample spam     :", spam[:8], file=sys.stderr)


if __name__ == "__main__":
    main()

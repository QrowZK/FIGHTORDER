#!/usr/bin/env python3
"""
Convert the RecoilEngine GitHub wiki (a git repo of GitHub-flavored Markdown
pages) into MediaWiki wikitext for import into Fightorder, verbatim.

Runs on the GitHub Actions runner (needs `pandoc` and network access to
clone the wiki repo — this sandbox can't reach github.com wiki clones
directly in some environments, the Action runner always can).

Titles and category groupings are hand-mapped (only 23 pages) rather than
guessed from filenames, since several titles contain punctuation that would
be ambiguous to reverse-engineer (parens, colons, commas).

Home.md is intentionally skipped — Fightorder ships its own themed
"Recoil Engine" portal page in its place (content/Recoil_Engine.wikitext),
the same treatment given to the Spring wiki's Main Page during that import.

Usage: import_recoil.py --wiki-repo <path to cloned .wiki.git> --out <dir>
"""
import argparse, os, subprocess, sys

SOURCE_REPO = "https://github.com/beyond-all-reason/RecoilEngine"
SOURCE_WIKI = f"{SOURCE_REPO}/wiki"

# filename -> (Fightorder page title, [categories])
PAGES = {
    "Building-and-developing-engine-without-docker.md":
        ("Recoil:Building the engine without Docker", ["Recoil Building"]),
    "Building-on-MSVC.md":
        ("Recoil:Building on MSVC", ["Recoil Building"]),
    "SpringRTS-Build-Environment-(Docker).md":
        ("Recoil:Build Environment (Docker)", ["Recoil Building"]),
    "MINGW64-Setup-(Windows-x64).md":
        ("Recoil:MINGW64 Setup (Windows x64)", ["Recoil Building"]),
    "Windows-build-environment:-step‐by‐step-instructions.md":
        ("Recoil:Windows build environment, step by step", ["Recoil Building"]),

    "Lua-VBO-and-VAO.md": ("Recoil:Lua VBO and VAO", ["Recoil Lua"]),
    "Lua-annotations-convention.md": ("Recoil:Lua annotations convention", ["Recoil Lua"]),
    "Lua_Handle.md": ("Recoil:Lua Handle", ["Recoil Lua"]),
    "Lua_SyncedControl.md": ("Recoil:Lua SyncedControl", ["Recoil Lua"]),
    "Lua_UnsyncedCtrl.md": ("Recoil:Lua UnsyncedCtrl", ["Recoil Lua"]),
    "Lua_UnsyncedRead.md": ("Recoil:Lua UnsyncedRead", ["Recoil Lua"]),

    "Engine-Configuration-Overview.md":
        ("Recoil:Engine Configuration Overview", ["Recoil Configuration"]),
    "Engine-Settings-Config-File.md":
        ("Recoil:Engine Settings Config File", ["Recoil Configuration"]),
    "Mod-Rules.md": ("Recoil:Mod Rules", ["Recoil Configuration"]),
    "Move-Definitions.md": ("Recoil:Move Definitions", ["Recoil Configuration"]),

    "ClientGameState-ServerGameState-state-dumps.md":
        # not "ClientGameState / ServerGameState ..." — "/" triggers MediaWiki
        # subpage nesting, which isn't wanted here.
        ("Recoil:ClientGameState and ServerGameState state dumps", ["Recoil Engine Internals"]),
    "Determinism-In-Engine.md":
        ("Recoil:Determinism in Engine", ["Recoil Engine Internals"]),

    "Console-Commands.md": ("Recoil:Console Commands", ["Recoil Reference"]),
    "Known-games.md": ("Recoil:Known games", ["Recoil Reference"]),

    "Pre-release-testing-Checklist,-and-release-engine-checklist.md":
        ("Recoil:Pre-release testing and release checklist", ["Recoil Development"]),

    "Profiling-Linux-Builds-with-Perf.md":
        ("Recoil:Profiling Linux Builds with Perf", ["Recoil Profiling"]),
    "Tracy-Profiling.md": ("Recoil:Tracy Profiling", ["Recoil Profiling"]),
}
SKIP = {"Home.md"}


def convert(md_path):
    r = subprocess.run(["pandoc", "-f", "gfm", "-t", "mediawiki", md_path],
                        capture_output=True, text=True, check=True)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki-repo", required=True)
    ap.add_argument("--out", default="recoil_pages")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    seen = set()
    manifest = []
    for fname in sorted(os.listdir(a.wiki_repo)):
        if not fname.endswith(".md"):
            continue
        if fname in SKIP:
            continue
        if fname not in PAGES:
            print(f"WARNING: unmapped wiki page {fname!r} — skipping "
                  f"(add it to PAGES in scripts/import_recoil.py)", file=sys.stderr)
            continue
        title, cats = PAGES[fname]
        seen.add(fname)
        body = convert(os.path.join(a.wiki_repo, fname))
        cat_lines = "\n".join(f"[[Category:{c}]]" for c in cats)
        footer = (
            f"\n\n----\n''Imported verbatim from the "
            f"[{SOURCE_WIKI} RecoilEngine wiki] on GitHub "
            f"([{SOURCE_REPO} beyond-all-reason/RecoilEngine]). "
            f"See the source repository for full page history and authorship.''"
            f"\n{cat_lines}\n"
        )
        safe = title.replace("/", "-")
        out_path = os.path.join(a.out, safe + ".wiki")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(body + footer)
        manifest.append((title, out_path))
        print(f"converted: {fname} -> {title!r}", file=sys.stderr)

    missing = set(PAGES) - seen
    if missing:
        print(f"WARNING: mapped pages not found in wiki repo: {sorted(missing)}",
              file=sys.stderr)

    with open(os.path.join(a.out, "MANIFEST.tsv"), "w", encoding="utf-8") as f:
        for title, path in manifest:
            f.write(f"{title}\t{os.path.basename(path)}\n")

    print(f"Done: {len(manifest)} pages converted.", file=sys.stderr)


if __name__ == "__main__":
    main()

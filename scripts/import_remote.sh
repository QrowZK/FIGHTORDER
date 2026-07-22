#!/usr/bin/env bash
# Runs ON the DreamHost server. Imports every staged Spring XML dump, then
# rebuilds link/category tables and site statistics. Re-runnable: importDump
# skips revisions that already exist.
#
# $1 = MediaWiki install path (docroot). Dumps live in ~/spring-import/.
set -euo pipefail

DP="$1"
cd "$DP"

shopt -s nullglob
files=( "${HOME}"/spring-import/*.xml )
if [ ${#files[@]} -eq 0 ]; then
  echo "No dump files found in ~/spring-import/ — nothing to import." >&2
  exit 1
fi

for f in "${files[@]}"; do
  echo ">>> importing $(basename "$f")"
  php maintenance/run.php importDump --no-updates "$f"
done

echo ">>> refreshing links / categories"
php maintenance/run.php refreshLinks --quiet || true

echo ">>> updating site statistics"
php maintenance/run.php initSiteStats --update || true

echo ">>> cleaning up staged dumps"
rm -rf "${HOME}/spring-import"

echo ">>> done"

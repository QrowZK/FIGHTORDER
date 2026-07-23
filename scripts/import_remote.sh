#!/usr/bin/env bash
# Runs ON the DreamHost server. Imports every staged XML dump from a given
# staging directory under $HOME, then rebuilds link/category tables and
# site statistics. Re-runnable: importDump skips revisions that already
# exist. Shared by the Spring and Zero-K (and any future) wiki imports.
#
# $1 = MediaWiki install path (docroot).
# $2 = staging directory name under $HOME (default: spring-import, for
#      backwards compatibility with the existing Spring import workflow).
set -euo pipefail

DP="$1"
STAGE_DIR="${2:-spring-import}"
cd "$DP"

shopt -s nullglob
files=( "${HOME}/${STAGE_DIR}"/*.xml )
if [ ${#files[@]} -eq 0 ]; then
  echo "No dump files found in ~/${STAGE_DIR}/ — nothing to import." >&2
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
rm -rf "${HOME}/${STAGE_DIR}"

echo ">>> done"

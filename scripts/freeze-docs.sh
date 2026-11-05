#!/usr/bin/env bash
# Freeze website/content/latest (and skills/latest) for a release tag.
# Usage: scripts/freeze-docs.sh vX.Y.Z
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 vX.Y.Z" >&2
  exit 2
fi

TAG="$1"
if [[ ! "$TAG" =~ ^v[0-9]+(\.[0-9]+)*$ ]]; then
  echo "invalid version tag: $TAG (expected vX.Y.Z)" >&2
  exit 2
fi
SEMVER="${TAG#v}"
TODAY="$(date -u +%F)"

CONTENT_SRC="website/content/latest"
CONTENT_DST="website/content/$TAG"
SKILLS_SRC="website/skills/latest"
SKILLS_DST="website/skills/$TAG"
VERSIONS="website/data/versions.json"

if [[ ! -d "$CONTENT_SRC" ]]; then
  echo "missing $CONTENT_SRC" >&2
  exit 1
fi
if [[ ! -f "$VERSIONS" ]]; then
  echo "missing $VERSIONS" >&2
  exit 1
fi
if [[ -e "$CONTENT_DST" ]]; then
  echo "refusing to overwrite existing freeze: $CONTENT_DST" >&2
  exit 1
fi

cp -a "$CONTENT_SRC" "$CONTENT_DST"
if [[ -d "$SKILLS_SRC" ]]; then
  if [[ -e "$SKILLS_DST" ]]; then
    echo "refusing to overwrite existing skills freeze: $SKILLS_DST" >&2
    exit 1
  fi
  cp -a "$SKILLS_SRC" "$SKILLS_DST"
fi

python3 - "$VERSIONS" "$TAG" "$SEMVER" "$TODAY" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
tag, semver, today = sys.argv[2], sys.argv[3], sys.argv[4]
data = json.loads(path.read_text(encoding="utf-8"))
versions = data.setdefault("versions", [])

if any(v.get("id") == tag for v in versions):
    raise SystemExit(f"versions.json already has entry {tag}")

for entry in versions:
    if entry.get("channel") == "latest":
        entry["updated"] = today
    elif entry.get("channel") == "release" and entry.get("status") == "current":
        entry["status"] = "supported"

# Insert the new release right after the latest tip entry.
insert_at = 0
for i, entry in enumerate(versions):
    if entry.get("channel") == "latest":
        insert_at = i + 1
        break
versions.insert(
    insert_at,
    {
        "id": tag,
        "label": tag,
        "semver": semver,
        "channel": "release",
        "status": "current",
        "updated": today,
        "contentDir": f"content/{tag}",
        "changelogSource": "CHANGELOG.md",
        "notes": f"Frozen snapshot matching the {tag} release tag.",
    },
)

path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"froze docs for {tag}")
PY

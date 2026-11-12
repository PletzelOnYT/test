#!/usr/bin/env bash
# Publish ONLY a successfully compiled and fully accepted no-voice game.
# This script runs in GitHub Actions with contents:write and actions:read.
set -Eeuo pipefail

: "${GH_TOKEN:?GitHub Actions authentication required}"
: "${GITHUB_REPOSITORY:?Missing repository}"
: "${GITHUB_REF_NAME:?Missing branch}"
: "${BUILD_RUN_ID:?Missing exact source run}"
: "${BUILD_SOURCE_SHA:?Missing exact source commit}"
: "${ACCEPTANCE_RUN_ID:?Missing exact acceptance run}"

REPO="$GITHUB_REPOSITORY"
BRANCH="pletzel-v4-easyplace-mapart-red-20261112"
FILE="Pletzel-V4-Optimized-Litematica-EasyPlace-EasyPick-MapArt-NoVoice.html"
EXPECTED_ARTIFACT="pletzel-v4-easyplace-easypick-mapart-red-optimized-no-voice-complete-html"
ORIGINAL_NAME="Pletzel-V4-Optimized-Litematica-EasyPlace-EasyPick-MapArt-NoVoice.html"
RELEASE_TAG="pletzel-v4-easyplace-mapart-no-voice"

test "$REPO" = "PletzelOnYT/test"
test "$GITHUB_REF_NAME" = "$BRANCH"
git merge-base --is-ancestor "$BUILD_SOURCE_SHA" HEAD

# Never publish from a testing-only job or a failed/unaccepted build.
build_json="$(gh api "repos/$REPO/actions/runs/$BUILD_RUN_ID")"
echo "$build_json" | jq -e --arg sha "$BUILD_SOURCE_SHA" --arg branch "$BRANCH" \
  '.status=="completed" and .conclusion=="success" and .head_sha==$sha and .head_branch==$branch and .name=="Pletzel V4 Easy Place Map Art red highlight no-voice full compilation"' >/dev/null
accept_json="$(gh api "repos/$REPO/actions/runs/$ACCEPTANCE_RUN_ID")"
# When called from the accepted browser workflow itself, its publishing job
# is still running, so the PARENT run cannot already be "completed".
# All seven Chrome jobs must nevertheless be completed and successful below.
if [[ "${ACCEPTANCE_RUNNING_PARENT:-false}" == "true" || "${GITHUB_RUN_ID:-}" == "$ACCEPTANCE_RUN_ID" ]]; then
  echo "$accept_json" | jq -e --arg branch "$BRANCH" \
    '(.status=="in_progress" or .status=="completed") and (.conclusion==null or .conclusion=="success") and .head_branch==$branch and .name=="Pletzel V4 Easy Place Map Art real Chrome seven-suite acceptance"' >/dev/null
else
  echo "$accept_json" | jq -e --arg branch "$BRANCH" \
    '.status=="completed" and .conclusion=="success" and .head_branch==$branch and .name=="Pletzel V4 Easy Place Map Art real Chrome seven-suite acceptance"' >/dev/null
fi
accept_sha="$(echo "$accept_json" | jq -r .head_sha)"
git merge-base --is-ancestor "$accept_sha" HEAD

# Verify the seven independently completed Chromium suites, not just a
# top-level acceptance status or one successful matrix job.
jobs_json="$(gh api "repos/$REPO/actions/runs/$ACCEPTANCE_RUN_ID/jobs?per_page=100")"
for suite in easyplace mapart red-highlight fourformat freecam hologram world-save; do
  echo "$jobs_json" | jq -e --arg n "chrome ($suite)" \
    '[.jobs[] | select(.name==$n and .status=="completed" and .conclusion=="success")] | length == 1' >/dev/null
done
echo "$jobs_json" | jq -e '[.jobs[] | select(.name | startswith("chrome ("))] | length == 7' >/dev/null

# The accepted source must explicitly pin THIS source compilation.
accepted_workflow="$(git show "$accept_sha:.github/workflows/pletzel-v4-easyplace-chrome-acceptance.yml")"
grep -Fqx "          run=$BUILD_RUN_ID" <<< "$accepted_workflow"
grep -Fqx "          sha=$BUILD_SOURCE_SHA" <<< "$accepted_workflow"
grep -Fqx "          artifact=$EXPECTED_ARTIFACT" <<< "$accepted_workflow"
grep -Fqx '          gh run download "$run" -R "$GITHUB_REPOSITORY" -n "$artifact" -D candidate' <<< "$accepted_workflow"

mkdir -p publish-from-action
gh run download "$BUILD_RUN_ID" -R "$REPO" -n "$EXPECTED_ARTIFACT" -D publish-from-action
mapfile -d '' -t files < <(find publish-from-action -type f -name "$ORIGINAL_NAME" -print0)
test "${#files[@]}" -eq 1
src="${files[0]}"
bytes="$(stat -c %s "$src")"
sha="$(sha256sum "$src" | cut -d' ' -f1)"

# GitHub blocks normal Git blobs above 100 MiB. The verified current
# artifact is 89,741,508 bytes; never commit an LFS pointer as a game.
if (( bytes < 80000000 || bytes > 104857600 )); then
  echo "REFUSING publication: unexpected HTML size $bytes; Git LFS would be required above 100 MiB."
  exit 8
fi
# Cross-check against the full compiled HTML hash recorded by the
# original compilation job, not just the artifact ZIP metadata.
mkdir -p original-compile-logs
gh run download "$BUILD_RUN_ID" -R "$REPO" -n pletzel-v4-corrected-shulker-gui-compile-logs -D original-compile-logs
recorded="$(find original-compile-logs -name artifact-sha256.txt -exec awk -v name="$ORIGINAL_NAME" '$2 ~ name {print $1}' {} \; | head -1)"
if [[ -z "$recorded" || "$recorded" != "$sha" ]]; then
  echo "ABORT: real HTML differs from compiler-recorded original SHA-256"
  exit 6
fi
if [[ -n "${EXPECTED_HTML_SHA256:-}" ]]; then
  test "$sha" = "$EXPECTED_HTML_SHA256"
fi

python3 - "$src" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1])
payload=source.read_bytes()
assert payload.startswith(b'<!DOCTYPE html>'), "Not a complete compiled document"
assert b'</html>' in payload[-100000:], "HTML closing tag missing"
for marker in (b'WebAssembly',b'__pletzelNativeXHR',b'sounds.epk',b'<script'):
    assert marker in payload, ("Missing embedded standalone resource",marker)
assert len(payload)>80000000,"Unexpectedly small file (possibly a redirect or pointer)"
print("STANDALONE_HTML_VERIFIED", source.name, len(payload))
PY

# Idempotence: unchanged accepted game bytes must never be recommitted.
already_published=false
if [[ -f "$FILE" ]] && [[ "$(stat -c %s "$FILE")" == "$bytes" ]] && \
   [[ "$(sha256sum "$FILE" | cut -d' ' -f1)" == "$sha" ]]; then
  already_published=true
  echo "Identical game already tracked in Git; preserving existing README and commit."
else
  cp "$src" "$FILE"
fi
test "$(sha256sum "$FILE" | cut -d' ' -f1)" = "$sha"
build_date="$(echo "$build_json" | jq -r .updated_at | cut -c1-10)"
repo_file="https://github.com/$REPO/blob/$BRANCH/$FILE"
release_file="https://github.com/$REPO/releases/download/$RELEASE_TAG/$FILE"
if [[ "$already_published" != "true" ]] || [[ ! -s README.md ]]; then
cat > README.md <<EOF
# Pletzel V4 Minecraft 26.2 — Latest No-Voice Release

**Version:** Pletzel V4 Easy Place + Easy Pick + durable Map Art + red highlights, no voice chat  
**Build date (UTC):** $build_date  
**Verified source run:** [GitHub Actions #$BUILD_RUN_ID](https://github.com/$REPO/actions/runs/$BUILD_RUN_ID)  
**Successful seven-suite browser acceptance:** [Run #$ACCEPTANCE_RUN_ID](https://github.com/$REPO/actions/runs/$ACCEPTANCE_RUN_ID)  
**Source commit:** \`$BUILD_SOURCE_SHA\`  
**Published filename:** \`$FILE\` ($bytes bytes)  
**SHA-256:** \`$sha\`

## Download

- **[Download complete standalone HTML directly from the GitHub Release]($release_file)** — no build tools or Git LFS needed.
- **[View the actual fully compiled HTML file in this branch's Code tab]($repo_file)** — committed normally as a full Git blob, not an LFS pointer.
- [Download the original compilation's Actions artifact](https://github.com/$REPO/actions/runs/$BUILD_RUN_ID).

## Features

- Four-format Litematica/Schematica imports: \`.litematic\`, \`.schematic\`, \`.schem\`, \`.nbt\`.
- Lazy, section-based schematic holograms with render-distance culling and bounded render caches.
- **Easy Place (OFF default)**: vanilla support-face right-click in Hold or opt-in Hover mode, with real reach and server validation.
- **Easy Pick (OFF default)**: selects only existing hotbar slots 1–9 through normal inventory selection.
- **Map Art memory (ON default)**: preserves original 128x128 map pixels by world/server+dimension+map ID in browser storage, with explicit art classification, explorer exclusion and clear controls.
- **Wrong-block overlays**: red on all expected-model faces, independent of connected ghost culling.
- Freecam, original Shulker Box Tooltip UI, real Map Tooltip artwork, and singleplayer engine improvements.
- **No experimental voice chat** in this build.

## Verification and limitations

The $ACCEPTANCE_RUN_ID Chrome acceptance run passed seven suites: Easy Place, persistent Map Art, red highlighting, all four schematic formats, Freecam, in-world holograms, and world save/reload. Compiled HTML bytes match the original source artifact using SHA-256.

**Not claimed as verified:** multiplayer server compatibility, every special block orientation, or stable FPS on a physical Mac. The separate [same-runner FPS comparison #43259063632](https://github.com/$REPO/actions/runs/43259063632) failed; it is not evidence of a speedup. A past render-distance acceptance workflow also failed while automating Video Settings, so complete 2/4/8/16 performance acceptance is not established.

## Release automation

\`.github/workflows/pletzel-v4-publish-easyplace-no-voice.yml\` publishes only after validating an actual successful game-compilation run and all seven successful Chromium acceptance jobs pinned to that compiled artifact. Repeated publication of identical binary/metadata does not create another Git commit. The acceptance workflow invokes this publisher automatically after its entire browser matrix passes.
EOF
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -- "$FILE" README.md
if git diff --cached --quiet; then
  echo "No file changes: identical binary and README are already committed."
else
  git commit -m "Publish accepted Pletzel V4 no-voice game from Actions #$BUILD_RUN_ID"
  git push origin "HEAD:$BRANCH"
fi

# Independent verification of the full Git blob as fetched from origin.
git fetch origin "$BRANCH"
git show "origin/$BRANCH:$FILE" > committed-file-check.html
test "$(stat -c %s committed-file-check.html)" = "$bytes"
test "$(sha256sum committed-file-check.html | cut -d' ' -f1)" = "$sha"

notes="Compiled game: $FILE
Build run: https://github.com/$REPO/actions/runs/$BUILD_RUN_ID
Accepted Chrome run: https://github.com/$REPO/actions/runs/$ACCEPTANCE_RUN_ID
Source commit: $BUILD_SOURCE_SHA
Size: $bytes bytes
SHA-256: $sha
Note: no voice chat. The independent FPS comparison workflow failed; no performance improvement is claimed."

if gh release view "$RELEASE_TAG" -R "$REPO" >/dev/null 2>&1; then
  gh release edit "$RELEASE_TAG" -R "$REPO" --title "Pletzel V4 — Easy Place, Map Art, and Red Highlight No-Voice HTML" --notes "$notes" --latest
else
  gh release create "$RELEASE_TAG" -R "$REPO" --target "$(git rev-parse HEAD)" \
    --title "Pletzel V4 — Easy Place, Map Art, and Red Highlight No-Voice HTML" --notes "$notes" --latest
fi

# Do not needlessly reupload an unchanged large release asset.
asset_info="$(gh api "repos/$REPO/releases/tags/$RELEASE_TAG" --jq '.assets[] | select(.name=="Pletzel-V4-Optimized-Litematica-EasyPlace-EasyPick-MapArt-NoVoice.html")' || true)"
asset_digest="$(echo "$asset_info" | jq -r '.digest // empty' 2>/dev/null || true)"
asset_bytes="$(echo "$asset_info" | jq -r '.size // empty' 2>/dev/null || true)"
if [[ "$asset_digest" == "sha256:$sha" && "$asset_bytes" == "$bytes" ]]; then
  echo "Identical GitHub Release asset already published; skipping reupload."
else
  gh release upload "$RELEASE_TAG" "$FILE" -R "$REPO" --clobber
fi

# Actually download the public Release asset again, and compare bytes.
mkdir -p verified-release-download
gh release download "$RELEASE_TAG" -R "$REPO" --pattern "$FILE" \
  --dir verified-release-download --clobber
test "$(stat -c %s "verified-release-download/$FILE")" = "$bytes"
test "$(sha256sum "verified-release-download/$FILE" | cut -d' ' -f1)" = "$sha"

# Check Code-tab API metadata and real README targets, not an invented URL.
remote_metadata="$(gh api "repos/$REPO/contents/$FILE?ref=$BRANCH")"
test "$(echo "$remote_metadata" | jq -r .size)" = "$bytes"
gh api "repos/$REPO/contents/README.md?ref=$BRANCH" --jq .sha >/dev/null
release_json="$(gh api "repos/$REPO/releases/tags/$RELEASE_TAG")"
echo "$release_json" | jq -e --arg file "$FILE" --arg bytes "$bytes" \
  '.assets | any(.name==$file and (.size|tostring)==$bytes)' >/dev/null

{
  echo "## Verified No-Voice Publication"
  echo "- Source build: $BUILD_RUN_ID ($BUILD_SOURCE_SHA)"
  echo "- Accepted browser run: $ACCEPTANCE_RUN_ID"
  echo "- Repository commit: $(git rev-parse HEAD)"
  echo "- Real full-blob bytes: $bytes"
  echo "- SHA-256: $sha"
  echo "- Code tab: $repo_file"
  echo "- Release asset: $release_file"
  echo "- Normal Git object; not LFS; verified downloaded Release bytes are identical"
} | tee publication-verification.txt
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat publication-verification.txt >> "$GITHUB_STEP_SUMMARY"
fi

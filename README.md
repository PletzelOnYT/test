# Pletzel V4 Minecraft 26.2 — Latest No-Voice Release

> **EMERGENCY SAFETY WARNING — 2026-11-13:** A newer Easy Place source implementation was reported to cause kicks/bans and client-only ghost blocks. Easy Place and hover automation have been placed under a source-level safety lockout. **The previously published HTML file below does not contain this safety patch.** Do not enable Easy Place or hover automation on public servers. No new safe compiled HTML or controlled multiplayer acceptance has been verified. Easy Pick is independent.

**Version:** Pletzel V4 Easy Pick + Map Tooltips + optimized Litematica, no voice chat  
**Build date (UTC):** 2026-11-12  
**Verified source run:** [GitHub Actions #43258316571](https://github.com/PletzelOnYT/test/actions/runs/43258316571)  
**Successful six-suite browser acceptance:** [Run #43262166530](https://github.com/PletzelOnYT/test/actions/runs/43262166530)  
**Source commit:** `c6e7c330414700db3a075940b376f8f4888480ea`  
**Published filename:** `Pletzel-V4-Latest-No-Voice.html` (89741508 bytes)  
**SHA-256:** `97716eeaf71045ecefaaa8e6463f8aeb7856142b32b1dab14aa0df78260df37a`

## Download

- **[Download complete standalone HTML directly from the GitHub Release](https://github.com/PletzelOnYT/test/releases/download/pletzel-v4-latest-no-voice/Pletzel-V4-Latest-No-Voice.html)** — no build tools or Git LFS needed.
- **[View the actual 85.6 MiB HTML file in this branch's Code tab](https://github.com/PletzelOnYT/test/blob/pletzel-v4-easypick-chunk-map-20261112/Pletzel-V4-Latest-No-Voice.html)** — committed normally as a full Git blob, not an LFS pointer.
- [Download the original compilation's Actions artifact](https://github.com/PletzelOnYT/test/actions/runs/43258316571).

## Features

- Four-format Litematica/Schematica imports: `.litematic`, `.schematic`, `.schem`, `.nbt`.
- Lazy, section-based schematic holograms with render-distance culling and bounded render caches.
- Optional persistent **Easy Pick**: hold the configured Use/Place Block key to select a suitable block from the existing nine hotbar slots using vanilla item selection.
- Freecam, original Shulker Box Tooltip UI, real Map Tooltip artwork, and singleplayer engine improvements.
- **No experimental voice chat** in this build.

## Verification and limitations

The 43262166530 Chrome acceptance run passed six suites: Easy Pick, map-hover, all four schematic formats, Freecam, in-world holograms, and world save/reload. Compiled HTML bytes match the original source artifact using SHA-256.

**Not claimed as verified:** multiplayer server compatibility, every special block orientation, or stable FPS on a physical Mac. The separate [same-runner FPS comparison #43259063632](https://github.com/PletzelOnYT/test/actions/runs/43259063632) failed; it is not evidence of a speedup. A past render-distance acceptance workflow also failed while automating Video Settings, so complete 2/4/8/16 performance acceptance is not established.

## Release automation

`.github/workflows/pletzel-v4-publish-no-voice.yml` publishes only after validating an actual successful game-compilation run and all six successful Chromium acceptance jobs pinned to that compiled artifact. Repeated publication of identical binary/metadata does not create another Git commit. The acceptance workflow invokes this publisher automatically after its entire browser matrix passes.

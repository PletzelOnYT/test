# Pletzel V4 — four-mod unified candidate

**Purpose:** assemble one Minecraft 26.2/TeaVM Wasm-GC client. This is not a gameplay acceptance report.

## Pinned sources

| Feature | Provenance |
|---|---|
| Schematica, engine and other V4 patches | Existing Pletzel V4 build pipeline (pinned upstream `dicestack88/Eaglercraft-26.2-source` commit `f73bff91f0f0840bc958c09ab536dbba1e146b2e`) |
| Map Tooltip and persisted Controls settings | `pletzel-v4-map-shulker-tooltips-native` commit `70fa22d0f00bc56cb7cd1dcb2ce54fed27a13149` |
| Original Shulker Box Tooltip v5.4.3+26.2 | `pletzel-v4-shulker-original-gui-geometry-fix` commit `17eb41fb4e88b65b2db27f212a28a017638eb298`; original MIT mod `MisterPeModder/ShulkerBoxTooltip` tag `v5.4.3+26.2` |
| Native official EaglerXServer V5 voice client | `pletzel-v4-eaglerx-v5-voice-native` commit `4342c328ed5fab6b7e9b3be0704d5e98f9eab12b` |
| Existing original shulker GUI candidate | GitHub Actions `42764573833` |
| Existing official voice candidate | GitHub Actions `42756876274` |

This branch is **based on the newest original Shulker geometry/CTRL-lock branch**, rather than an older voice or map implementation. Six missing voice-source files were imported without overwriting the corrected shulker patch or native Options settings.

## Order of patches in the one native build

1. Existing V4 Schematica, loading, safe-spawn, player skin, networking, rendering and engine patches.
2. Native Minecraft Singleplayer warning and touch/mouse Controls.
3. VendoAU native Map Tooltip using actual MapId + vanilla MapRenderer.
4. Native original Shulker v5.4.3 GUI (real 27-slot CONTAINER contents, mod sprite, dye tint, hover, CTRL-locked preview).
5. Native official EaglerXServer V5 voice packet support and TeaVM browser WebRTC, using existing Eagler v5 transport.
6. Compile Java exactly once, link Wasm-GC exactly once, package one standalone HTML.

## Unresolved validation obligations

- Previous WebRTC browser audio test reported zero received audio despite WebRTC connection. **Not PASS.**
- Earlier Shulker screenshot tests sometimes failed to create actual shulker items. **Item preview parity is not yet PASS.**
- Separate working component builds do not prove that features coexist in this combined HTML.
- Singleplayer Mac TPS stalls, saving, live multiplayer/server voice compatibility, Schematica hologram, and long-session stability require meaningful gameplay acceptance.

Final artifact must be SHA-256 hashed and tested as-is; any capability that cannot be exercised must remain BLOCKED or UNTESTED.

# Pletzel V4 — Litematica Easy Pick

Easy Pick is an **optional, client-only hotbar selector** for the Pletzel V4 Minecraft 26.2 no-voice build.

## Use

1. Load a supported schematic: `.litematic`, `.schematic`, `.schem`, or `.nbt`.
2. Put the blocks you need in **hotbar slots 1–9**. Blocks anywhere else in the inventory are not used.
3. Open **Options → Litematica/Schematica → Easy Pick: OFF** and click to enable **ON**. The setting is OFF by default and saved through Minecraft's existing options.
4. Aim at a real support block face adjacent to the intended missing schematic block, within normal vanilla reach, then **hold your configured Place Block control** (right mouse button by default).
5. When a hotbar block matches both the schematic block type and the exact state vanilla placement would create at that face, Easy Pick selects its hotbar slot. Minecraft performs normal, server-authoritative item selection and placement. The feature never adds placement inputs.

## Constraints and safety

- Freecam disables use/placement; Easy Pick never runs while Freecam is active.
- No forged packets, automatic placement, camera movement, item duplication, creative inventory insertion or main-inventory item transfers.
- Only a valid block under the vanilla crosshair and its legitimate placement destination are considered; ghost blocks outside reach are not selected.
- Already-correct schematic positions are skipped. If the required state cannot be placed using the current aim and available hotbar slots, Easy Pick refuses to select a substitute or place a wrong item there.
- Vanilla orientation matters: rotate your view or aim at a different face for stairs, logs and slabs, rather than expecting Easy Pick to rotate blocks for you.
- The renderer's progressive 16x16x16 schematic index supplies O(1) local block lookups. A recently imported distant section may need several frames to be indexed.
- Easy Pick requires Minecraft's **Hold to Use** mode; it intentionally does not perform continuous selection in Toggle Use mode.
- Tested outcomes are recorded separately in GitHub Actions. Multiplayer behavior should not be considered verified without testing on a real server.

No separate service or server plugin is required for the selection mechanism.

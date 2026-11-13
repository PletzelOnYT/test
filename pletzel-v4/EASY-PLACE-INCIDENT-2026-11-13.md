# Pletzel V4 Easy Place — incident and release gate (2026-11-13)

## Severity and current status

**Critical, OPEN. Easy Place is intentionally DISABLED in source.**
A user reported kicks/bans, client-only ghost blocks and repeated failed placement. These reports require controlled reproduction; they cannot be independently established from a Java compile or successful packet transmission.

The emergency source lockout is implemented in `EasyPlace26.java`:
- `beforeVanillaUse` returns to **unmodified vanilla right-click**;
- `shouldHoverPlace` always returns false;
- `afterVanillaKeybinds` resets persisted Easy Place/Hover settings OFF;
- both available settings screens refuse attempts to enable Easy Place/Hover;
- independent Easy Pick remains functional and OFF by default;
- no custom hit substitution, packet send, local block placement, pending-completion inference or automated retry remains executable.

**Existing released HTML files do NOT automatically inherit this source change. Do not enable Easy Place/Hover in older binaries on public servers.** A safety-only source build is not a functional Easy Place release.

## Source-backed defects in the previous implementation

1. **Client prediction was treated as completion.** `afterVanillaKeybinds()` previously cleared `awaitingTarget` when `mc.level.getBlockState(awaitingTarget).equals(awaitingState)`. `ClientLevel` may reflect client-side prediction, so this was not proof of server acceptance. The log itself used `CLIENT_WORLD_MATCHED`, not a server packet receipt.
2. **No single-outstanding-placement invariant for Hold mode.** `beforeVanillaUse()` could continue to invoke normal item use while a previous target was still awaiting confirmation; `awaitingTarget` was not a global stop condition.
3. **Automatic retry signature could change from local prediction/correction.** `shouldHoverPlace()` used `world.hashCode()` and selected slot in its signature; such transitions could re-arm an attempt without explicit server acceptance.
4. **Crosshair hit substitution needs independent validation.** The old implementation overwrote `mc.hitResult` with another `ClientLevel.clip()` hit before vanilla use. Even a real collision raycast is not guaranteed equivalent to the user's current vanilla crosshair target or a server-accepted action.
5. **Selection synchronization was not proven.** The old planner considered any matching hotbar slot when Easy Pick was enabled, while selection actually occurred later in the use path. No controlled-server validation established that every placement used a synchronized slot.
6. **Existing Chrome tests did not establish public/multiplayer acceptance.** They exercised real integrated singleplayer scenarios, but explicitly reported multiplayer unverified. A test observing client-world state alone does not prove that a remote server accepted the block.

These are confirmed weaknesses in the *source logic*. They are not proof of which exact server anticheat check caused the reported bans, and they do not prove that the schematic renderer itself inserted real ghost blocks.

## Required functional reimplementation (not completed)

- Separate non-solid schematic hologram, pending attempt, and server-verified world state.
- Use only a genuinely reachable vanilla support hit and standard client interaction manager; no arbitrary packet crafting.
- Check target, item, exact placement orientation, selected slot synchronization, reach, line of sight, world border, collision and dimension.
- Allow at most one pending assisted placement; no frame-spam or retry without a new deliberate action and confirmation.
- Integrate with authoritative `ClientPacketListener` block-state updates (including multi-block/chunk and server corrections) to resolve, reject, expire and clear pending attempts.
- On disconnect, GUI opening, world/dimension change or schematic unload: cancel all pending work.
- Never mark a schematic ghost completed from client prediction, sound, animation, packet dispatch or any unconfirmed world state.
- Keep Hover Auto-Place disabled by default; do not enable it on servers whose rules prohibit automation.
- Preserve Freecam, four schematic formats, Easy Pick, Map Tooltips in dedicated menu, Shulker Tooltips, red wrong-block overlays, worlds, chunk render and no-voice build.

## Non-negotiable acceptance before removing lockout

| Gate | Test | Status |
| --- | --- | --- |
| A | Controlled singleplayer stone/glass/oak placement; save/quit/reload exact world-state persistence | NOT VERIFIED on patched binary |
| B | Controlled dedicated local multiplayer validates exact server block states and no malformed/duplicate interactions | NOT VERIFIED |
| C | Server rejection/correction to AIR restores correct client world; hologram persists; no fake solid blocks | NOT VERIFIED |
| D | Out-of-reach, missing support/item, wrong orientation, slot delay, rapid use, latency/loss, disconnect/dimension and GUI interruption all fail closed | NOT VERIFIED |
| E | Instrumented packet and item-use equivalence to ordinary vanilla right-click | NOT VERIFIED |
| F | Easy Pick OFF/ON × Easy Place OFF/ON independence, and Hover OFF on new profiles | NOT VERIFIED for a working Easy Place implementation |
| G | Full standalone HTML, native compile, exact SHA, Chrome tests and no-voice mod regressions | NOT VERIFIED for patched build |
| H | Publish the verified full HTML **as a normal repository file** and independently re-download/check hash | NOT VERIFIED |

Build or source-policy checks alone may pass while functional placement remains disabled. Do **not** promote, claim anticheat safety, or publish a functional Easy Place release on such evidence.

## Incident disposition

**Temporary containment implemented; functional repair and release validation remain OPEN.**

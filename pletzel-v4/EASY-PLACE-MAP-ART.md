# Pletzel V4 — Easy Place, Map Art, and Red Highlight (No Voice)

This branch extends the successfully accepted Easy Pick + Freecam no-voice client. The source and standalone build workflows are in `.github/workflows/`. See the README at the branch root for the **last verified published** binary. A newer build is a candidate until the seven real-browser acceptance jobs pass.

## Easy Place + Easy Pick

1. Load a `.litematic`, `.schematic`, `.schem`, or `.nbt` hologram.
2. In **Options → Litematica → Building / Easy Place**, turn on **Easy Place**. It starts OFF.
3. **Hold to Place** is the default mode: hold your normal, remappable Use/Place Block control while aiming at a reachable ghost with a real support block behind it. Vanilla Minecraft performs the placement.
4. Optional **Hover Auto-Place** attempts vanilla use **without** another click when the crosshair enters a *new, valid, supported* ghost target. This mode is OFF by default. It will not place through air, obstacles, unloaded chunks, or outside normal reach.
5. Turn on **Easy Pick** separately (OFF default) to select from **hotbar slots 1–9 only** using the same inventory setter as Minecraft's 1–9 number keys. No item stacks, main inventory, packets or world blocks are forged or mutated.
6. Stairs, slabs, directional states and other complex blocks must still be placed in a correct vanilla orientation. If the item/aim cannot create the requested schematic state, Easy Pick and Easy Place do not claim success.
7. **Freecam disables Easy Place**. Both options are stored through Minecraft's normal persistent options storage.

The crosshair must have a **real vanilla block hit** with line of sight. A hologram is a visualization and never grants permissions to place through walls or at arbitrary distances. Multiplayer-server compatibility has not been independently verified.

## Permanent Map Art

1. With a real filled map in your main hand, open **Building / Easy Place → Map Art Settings**.
2. Choose **Mark Held Map as Art** once to opt in to artwork previews for that particular map ID. Ambiguous terrain maps are *not* automatically assumed to be artwork.
3. Once real nonblank map pixels are received, the client stores **exactly 16,384 original packed Minecraft color bytes** in its namespaced browser storage (the same-origin storage used for other game options). It does not synthesize art from map metadata.
4. Later, with the same HTML storage origin and world/server identity, the tooltip can show the saved preview **without opening the map again**. A newly created empty client map buffer does not overwrite the last verified saved pixels.
5. **Exclude Held Map** hides any selected non-art map. Explorer/treasure/structure maps with recognizable item names or explorer decoration types are excluded when **Exclude Explorer** is ON (default).
6. **Clear Saved Art** removes stored pixel images for the current world/server scope without deleting Minecraft worlds or the user's explicit art classifications.

Settings defaults: Remember Map Art ON, Show Art Previews ON, Exclude Explorer ON. Pixel storage is scoped by local save path (or multiplayer address), dimension, and map ID. Browser storage is separate for different origins or profiles and can be deleted by browser cleanup. A server that resets its world while retaining the same address and map IDs may require clearing old art data manually. A fully transparent 128×128 map cannot be distinguished reliably from uninitialized pixels and is not learned until nonblank pixel data is actually received.

The persistent store uses a bounded **128-artwork** disk index and a **24-artwork** in-memory LRU. The GPU texture representation remains Minecraft's native map renderer.

## Huge Holograms and Incorrect Blocks

- Schematic blocks remain in the full source data; 16×16×16 spatial sections are progressively indexed and their nearby **chunk columns** are queried without scanning every distant schematic section each frame.
- Visual rendering respects the actual Minecraft render distance, camera frustum, and **already-loaded client world chunks**. Freecam changes only the visual culling camera; it requests no extra chunks.
- A bounded LRU caches render-derived section geometry and a per-frame budget limits mesh construction. The source blocks are never removed when visual sections are evicted.
- A block in the wrong real-world state draws **all original model faces** tinted red. This mismatch rendering is separate from face-culling of connected ordinary ghost blocks, so internal ghost-face merging cannot delete the wrong block's red overlay.
- Right/wrong checks use the **actual live world state**. A correction removes the red tint on subsequent renders.

**Technical limitation:** This engine still uses its native custom geometry-submission API, not persistent per-section GPU VBOs. It therefore is **not yet identical to vanilla Minecraft's GPU chunk renderer**. Performance claims must be tied to measured real Chrome logs; the earlier before/after FPS comparison failed and cannot establish a speedup.

## Verification status

The previous published no-voice binary passed separate real-Chrome suites for Easy Pick, Map Tooltip, four schematic imports, Freecam, world saving, and in-world hologram rendering. New Easy Place, persistent Map Art, section-column indexing and complete red faces require **their own seven-suite real-Chrome acceptance** against the exact compiled HTML before a new release is declared successful. See:

- `.github/workflows/pletzel-v4-litematica-freecam-no-voice.yml` — full native Java/WebAssembly compilation
- `.github/workflows/pletzel-v4-easyplace-chrome-acceptance.yml` — seven exact-binary Chrome suites
- `.github/workflows/pletzel-v4-render-distance-acceptance.yml` — actual GUI 2/4/8/16 chunk checks
- `.github/workflows/pletzel-v4-easyplace-fps-comparison.yml` — before/after software-WebGL measurements
- `.github/workflows/pletzel-v4-publish-easyplace-no-voice.yml` — Git commit, Release asset and independent SHA-256 re-download, only if acceptance passes

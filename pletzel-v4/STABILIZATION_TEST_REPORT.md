# Pletzel V4 — Stabilization Acceptance Record

**State: NOT ACCEPTED.** This file tracks actual observed evidence, not a release announcement. No test gets PASS solely because Java/TeaVM compiled or a menu rendered.

## Provenance

- Original four-mod integration source: `fda0b34781b31f510e90a49b815d9887ca36763c`, native build [#42844549237](https://github.com/PletzelOnYT/test/actions/runs/42844549237).
- Previous combined HTML SHA-256: `513bb8628b0c934943e42efc6a68acaa14f9b2c4c0db0ee97b42fb74ff132a19` (from old exact-binary Chromium run [#42845572891](https://github.com/PletzelOnYT/test/actions/runs/42845572891)).
- Native voice repair in `pletzel-v4/eaglerx-voice/PlatformEaglerVoice26.java`, integrated into the *new* combined native compile source at build trigger commit `091209f36bbaf93933dcf8d8ae0e4a6b8db3f1f3`, [native build #42937082477](https://github.com/PletzelOnYT/test/actions/runs/42937082477).
- New exact repaired HTML digest: **`8ded0acb2a1eb732015bebc6265297984392acf7d1b257ff2aafe52abcbf2f9a`**, independently verified from downloaded [native build #42937082477](https://github.com/PletzelOnYT/test/actions/runs/42937082477/artifacts/13821065027) standalone HTML (89,703,312 bytes).
- Test environment for linked automation: GitHub Actions Ubuntu 24.04 with real Playwright Chromium 141 and Xvfb software WebGL. No real Mac or external EaglerX v5 voice-enabled server has been exercised.

## Current tests (individual assertions, not feature-wide acceptance)

| Test | Result | Evidence / reason |
|---|---|---|
| Original combined Java + TeaVM Wasm-GC link | PASS | Build [#42844549237](https://github.com/PletzelOnYT/test/actions/runs/42844549237); does **not** prove gameplay |
| Standalone repaired HTML boot directly from file:// OFFLINE | PASS | [#42943012916](https://github.com/PletzelOnYT/test/actions/runs/42943012916): Chromium with HTTP(S) network blocked displayed genuine native profile/title screens and live 1280x720 canvas, zero external requests and page exceptions; world/playthrough offline not tested |
| Two-browser native WebRTC sound + mute/talk/mute | PASS | [#42936877240](https://github.com/PletzelOnYT/test/actions/runs/42936877240): received RMS 0.00111 / 0.23143 / 0.00118, cleanup succeeds; **Java native adapter JS source**, not an actual external Minecraft voice-enabled server |
| Exact compiled HTML with repaired voice | UNTESTED | [#42937082477](https://github.com/PletzelOnYT/test/actions/runs/42937082477) native compile / link underway at last check |
| Singleplayer first world boot and actual completed server ticks | PASS | [#42849879185](https://github.com/PletzelOnYT/test/actions/runs/42849879185), genuine integrated server reported 320+ completed ticks |
| Real integrated-server TPS sustained in Ubuntu Chromium | PASS | The real server heartbeat telemetry in [#42940967108](https://github.com/PletzelOnYT/test/actions/runs/42940967108) shows 19.99 TPS during seconds 150–240, 19.97 during 240–360, and 19.99 during 360–450 of the real browser session. That workflow failed from a test regex bug; ticks themselves were not stalled |
| Normal CPU three-minute actual-world endurance | PASS | Exact repaired binary [#42942047263](https://github.com/PletzelOnYT/test/actions/runs/42942047263): 3,548 real ticks / 182.84 seconds = 19.40 mean TPS, actual terrain screenshots, no JS errors |
| Single-CPU three-minute actual-world endurance | PASS | Exact repaired binary [#42942047263](https://github.com/PletzelOnYT/test/actions/runs/42942047263): 2,435 ticks / 204.28 seconds = 11.92 mean TPS, terrain screenshots, no JS errors. Passes low single-CPU smoke threshold but is substantially slower than 20 TPS |
| Smooth interactive FPS, heavy chunk exploration and physical Mac performance | UNTESTED | Xvfb software GPU measured roughly 1–4 FPS, not representative of physical Mac GPU; no actual multi-seed exploration/memory endurance completed |
| Distant 1024-block teleport causes genuine client position packet | PASS | [#42955658889](https://github.com/PletzelOnYT/test/actions/runs/42955658889): exact binary `/tp @p ~1024 ~ ~1024` reached client in 43.0 seconds; earlier tests had cheats off and commands never executed. 43 seconds is high latency, not evidence of fast teleport |
| Two real filled-map inventory items with distinct terrain previews | PASS | [#42958081051](https://github.com/PletzelOnYT/test/actions/runs/42958081051): in one real Survival world, server confirmed `PLETZEL_FIRST_FILLED_MAP` and `PLETZEL_SECOND_FILLED_MAP` from independent `execute if items entity @p hotbar.0/1 minecraft:filled_map` checks; screenshots show genuine Map ID #0 (water/green) and ID #1 (snow), 29,376 aligned preview pixels differ. This subtest PASSED even though the overall combined-session workflow FAILED after the player suffocated before Schematica import |
| Real empty + populated Shulker tooltip interaction | PASS | [#42845572891](https://github.com/PletzelOnYT/test/actions/runs/42845572891), actual /give items and 27-slot inventory screenshots; visual parity against reference mod still separately needs review |
| Map/Shulker ON/OFF controls through native UI | PASS | [#42846565732](https://github.com/PletzelOnYT/test/actions/runs/42846565732): toggles and reload screenshots; full semantic persistence check remains to be proven |
| Schematica file chooser in separate real browser session | PASS | [#42845572891](https://github.com/PletzelOnYT/test/actions/runs/42845572891): actual .schematic selection; hologram color/orientation not established by file chooser |
| Schematica .schematic file chooser in SAME map+shulker session | PASS | [#42939271086](https://github.com/PletzelOnYT/test/actions/runs/42939271086) selected genuine fixture and photographed a red translucent in-world hologram candidate; correctness of all hologram block states/positions still UNTESTED |
| Native world save, quit, reopen and changed block | PASS | [#42953514309](https://github.com/PletzelOnYT/test/actions/runs/42953514309): real ServerLevel saves, new StartServer after native Play Selected World, 320+ fresh worker ticks, and server-origin `PLETZEL_SAVE_PROBE` chat before and after reopening. Exact binary SHA-256 retained |
| Real external EaglerXServer V5 voice interoperability | BLOCKED | No controlled remote server and older native peer connected |
| Server-authoritative multiplayer movement/chunk/teleport | BLOCKED | No controlled multiplayer server session |
| Hosted macOS Apple Silicon startup and 3-minute actual integrated-server ticks | PASS | [#42953883393](https://github.com/PletzelOnYT/test/actions/runs/42953883393): macOS 15.8.2 Apple M1 (Virtual), exact binary `8ded0acb2a1eb732015bebc6265297984392acf7d1b257ff2aafe52abcbf2f9a`, offline startup PASS, visible world and 3,777 real ticks / 205.86 seconds = 18.35 TPS, no browser errors |\n| Physical USER Mac performance, inputs, storage and voice | BLOCKED | Apple M1 GitHub-hosted macOS VM is not the user's actual Mac device. Requires real-device diagnostics |
| Audio and music resource completeness | FAIL | Actual browser console noted optional music pack unavailable, with background music/discs disabled; full copyrighted asset provenance must be verified before making a release completeness claim |
| Touch/mouse switching with real Chromium pointer and touch events | PASS | [#42940784198](https://github.com/PletzelOnYT/test/actions/runs/42940784198): four consecutive toolbar activation/deactivation cycles, actual browser screenshots, no page errors |
| Native Steve/Alex profile controls and visible model geometry | PASS | [#42940784198](https://github.com/PletzelOnYT/test/actions/runs/42940784198): original model and slim model selected in real game UI, correct labels and visually different arms; persistence and multiplayer skins still UNTESTED |
| Chromebook F+3/F+5 alternatives, key rebinding and persistent input overrides | UNTESTED | Source patches exist, specific functional regression tests still missing |
| Browser crash/recovery and multi-hour endurance | UNTESTED | No multi-hour hardware-realistic test |

## Critical fix evidence

The native voice receiver now installs a hidden, **zero-volume** HTML audio playout sink for the WebRTC remote MediaStream. Chromium's WebRTC audio decoder otherwise delivered RTP packets but `totalSamplesReceived=0`. Audible audio stays routed only through the game's WebAudio gain and spatial HRTF panner; the sink is removed when a peer closes. The exact original strict RMS assertion passed only **after** this source change. No custom Pletzel plugin/gateway is introduced.

The game acceptance runner was also corrected to:
1. Restore its original 1280×720 viewport after responsive-layout testing before using fixed GUI click coordinates.
2. Avoid pressing Escape when already paused (which previously closed the pause menu).
3. Use Creative mode during long Schematica automation so a Survival death does not invalidate GUI clicks.
4. Wait for an actual received player-position packet after a distant teleport before declaring the second map geographically distinct.
5. Compare normalized, aligned terrain preview crops rather than unrelated pixel changes from moving a tooltip.

## Exact-binary regression

The [strict stabilization acceptance workflow](https://github.com/PletzelOnYT/test/actions/workflows/pletzel-v4-stabilization-acceptance.yml) downloads the new build by exact run and source commit; hashes the HTML; records screenshots, console and telemetry; executes native tooltip, Schematica, WebRTC, settings, same-world and save/reload scripts; and fails the workflow if **any** attempted smoke script fails. These are not substitutes for a real EaglerX server, real Mac or extensive vanilla gameplay suite.

**Release gate:** not satisfied. Preserve PASS/FAIL/BLOCKED/UNTESTED distinctions and do not ship as 100% accepted while gamebreaking issues remain.

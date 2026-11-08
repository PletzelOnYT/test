# Pletzel V4 — Mac Chrome field diagnosis, not a gameplay release

The exact upstream experimental standalone HTML was recovered from run #42509653180, artifact `pletzel-v4-four-bug-experimental-standalone-html` (ID 13630390161). The browser diagnostics HTML created in ChatGPT appends one self-contained, opt-in JavaScript block after the existing `<head>` and does not recompile or modify WASM or Minecraft resources.

Original HTML: 89,677,513 bytes; SHA-256 `3c149fa6dc419ba97f20387250458d715ba6a46b6fef49883e9ad9024abc1deb`.

Field-instrumented browser HTML SHA-256 `5c3a8d680977ecd359a0bba7ff8f94515c0db4e43bcda567371fcf273d7979ec`.

To activate: open the downloaded HTML locally in Chrome with `?pletzeldiag=1&perfdebug&workerlog` appended to the `file://` URL; or press Alt+Shift+D (Option+Shift+D on macOS) to toggle the panel. Mark the failure and choose Export JSON or TXT; diagnostics are OFF by default. JavaScript errors, worker activity, client WebSocket enqueue counts, buffering, WebGL context loss, console-reported server tick heartbeat, generation claims and tasks are tracked. Packet payloads, chat text, authentication credentials, and full server URLs are not recorded.

**Evidence limitations:** WebSocket.send is not a remote Minecraft server receipt acknowledgment, and it cannot prove a server-authoritative XYZ. Unless the compiled native game prints it, WASM player XYZ and internal chunk-mesh counters are unavailable to a launcher-only script. For multiplayer freeze confirmation gather an independent second-player screenshot or authoritative server position/packet log. For terrain holes, use F3 plus server chunk status and client chunk mesh diagnostics; don't assume holes are all generation failures. Native worker logs may require perfdebug&workerlog at startup.

To reproduce the overlay from the original HTML and diagnostic JS, run `python3 pletzel-v4/field-diagnostics/inject.py original.html pletzel-field-diagnostics.js output.html`. The overlay source checksum is `13f37428e78e5bb9d09fb6bf2a00c3f7e7aa48ca3ebea2223cab839d1ef1f2c0` (includes observed TPS and completed-tick duration parsing). This README and installer do not claim the Mac bug has been fixed.

Test classification: distinguish `HARNESS_ERROR` (wrong screenshot count, click selectors), `BUILD_ERROR` (Java/WASM compile), `GAMEPLAY_FAIL` (authoritative XYZ or real ticks contradict acceptance), and `MANUAL_REQUIRED` (physical Mac/GPU, genuine remote server, visual ghost flicker).

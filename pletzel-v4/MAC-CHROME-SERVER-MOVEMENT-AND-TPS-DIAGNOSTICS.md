# Pletzel V4 — Mac Chrome field verification (experimental four-bug candidate)

**Purpose:** Distinguish actual multiplayer transport desynchronization from local prediction, and a stalled integrated server from an inaccurate TPS label. The automated Linux Chromium checks **cannot** certify behavior on the player's actual Mac/GPU/remote server.

## Run without changing existing saved worlds

1. Use the checksum-verified `FOUR-BUG-NATIVE-CANDIDATE-UNVERIFIED.html`, not the old SUPERVISOR-WAKE file. Keep your old HTML and existing worlds backed up.
2. Launch in Chrome with `?perfdebug&workerlog` added to the end of the HTML file URL. If the URL already has a `?`, append `&perfdebug&workerlog` instead.
3. Open **View → Developer → JavaScript Console** (Option+Command+J), enable **Preserve log**, and retain warnings/errors.
4. Reproduce the problem in the same Chrome visibility, GPU and memory conditions as usual. **Do not reload the game when STALLED occurs**. Record an F3 screenshot, the TPS value, and console output around the event. Right-click Console → **Save as...** when available.
5. Before sharing logs, redact IP/server address, usernames, chat messages, cookies and auth tokens. Do not post unredacted data on a public GitHub issue.

## Singleplayer: classify the stalled server

Look for the following marker groups in chronological order:

- `[EagPerfHeartbeat]`: `lastTick`, `startedTick`, `activeTick`, `sinceCompleted`, `phase`, `worldgenQueue`, `claims`, `tasks`, `workerMessageBatches`, `heapUsed`, `gcTime`.
- `[PletzelActiveChunkWait]`: **new** perfdebug probe prints a `FULL@chunkX,chunkZ` requested by a server tick **while its synchronous managedBlock is still pending**, even if it never returns. An existing `[EagPerfChunkWait]` normally appears only **after** the wait ends.
- `[EagPerfClient] singleplayer inbound`, `chunk packets applied`: whether completed server chunks actually reach the client.
- Actual worker crashes, WebAssembly traps, graphics errors, or promise errors.

Interpretation:
- `lastTick` frozen, `activeTick` growing and `[PletzelActiveChunkWait]` present: server is **inside a blocking chunk future**, not idle or cosmetically stalled.
- `lastTick` frozen, `phase=idle` and no active pending wait: inspect worker wakeup/timer queue, worker console and CPU state.
- `lastTick` progresses at ~20 but chunks are visibly absent: inspect `chunk packets applied` and the client F3 rendered section count. Without incoming real chunks, it is generation/network delivery; with incoming/loaded block data but absent geometry, suspect mesh invalidation/upload.
- Heartbeats stop entirely: inspect worker crash, hidden-tab throttling, memory pressure and browser task suspension.

## Multiplayer: prove actual movement reception, not just apparent local motion

On the **same** server where the freeze occurs, reproduce with a second player or server operator observing your location. Record the moment the two player positions diverge.

Capture these existing client metrics:
- `[EagPerfClient] player movement samples=... inputActive=... localMoved=... sent=... cameraBlocked=... corrections=...`
- `[EagPerfClient] transport type=relay/eaglerx ... sent=... bufferedOutMax=... queueMax=... `
- F3 client XYZ, connection ping, and any teleport corrections or disconnect.

**The `sent` counter in player movement only means the local client generated a packet, and WebSocket `sent` can mean accepted by the browser socket API. Neither proves the remote server applied the movement.** Obtain server-side authoritative player XYZ / movement-packet receipt timestamps from a server operator if possible, and compare at the same time points. Do **not** disable server movement validation or anticheat.

Diagnostic classes:
- `localMoved>0` but movement `sent=0`: investigate client tick/controlled-camera/player packet generation.
- movement `sent>0`, transport output stays zero or browser `bufferedOutMax` keeps rising: investigate outbound Netty/WebSocket flushing, Wisp or relay backlog.
- transport output continues, buffer drains, but server position remains fixed: investigate relay loss/route, protocol movement validation, server-side packet receipt and pending teleport acknowledgement.
- server receives and accepts positions while other players see a stale location: investigate server entity tracking/broadcast independently of client outbound transport.

## Ghost overlays and terrain

For Schematica, place the real schematic at/near ground and move the camera slowly across its touching block faces. Take 2–3 screenshots at different angles. Ghost blocks should remain stable without shining through opaque blocks.

For a blank rectangular terrain area, check F3 chunk coordinates/rendered sections and try interacting with the boundary. Do not classify missing server chunks as meshing failure from the screenshot alone.

**Release rule:** This file is a field-test candidate. Successful Ubuntu Chromium jobs are useful but do not override a reproducible macOS Chrome or real remote-server synchronization failure.

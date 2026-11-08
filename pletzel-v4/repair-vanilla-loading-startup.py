#!/usr/bin/env python3
"""Restore the ORIGINAL 26.2 LevelLoadingScreen and real startup status pipeline.

This is a small overlay on top of the ALREADY VERIFIED cumulative native V4
source patch. It does not change terrain generation, collision, spawning
semantics, server tick validation, world saving, Schematica, or multiplayer.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit("usage: repair-vanilla-loading-startup.py <pinned-engine-root>")
root = Path(sys.argv[1]) / "game/src/main/java"

def replace(path, old, new):
    p = root / path
    src = p.read_text(encoding="utf-8")
    count = src.count(old)
    if count != 1:
        raise AssertionError(f"Refusing non-exact {path}: expected one anchor, saw {count}: {old[:120]!r}")
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("VANILLA_LOADING_PATCHED", path)

minecraft = "net/minecraft/client/Minecraft.java"
# Eagler's ad-hoc black "Starting integrated server" screen is the primary
# reason real vanilla world generation is never visible during spawn selection.
# The existing vanilla LevelLoadingScreen handles narration/background/font,
# the exact Mojang color map, grid positions, and world-enter transition.
replace(minecraft, """      net.lax1dude.eaglercraft.v1_8.sp.gui.EaglerIntegratedServerBusyScreen eaglerBusyScreen = null;
      if (net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()) {
         eaglerBusyScreen = new net.lax1dude.eaglercraft.v1_8.sp.gui.EaglerIntegratedServerBusyScreen();
         this.gui.setScreen(eaglerBusyScreen);
      } else {
         this.gui.setScreen(screen);
      }""", """      // Native 26.2 vanilla LevelLoadingScreen, on browser AND desktop.
      // Worker-side real chunk-status updates are bridged below, including
      // PREPARE_GLOBAL_SPAWN before the server has published its local channel.
      this.gui.setScreen(screen);""")
replace(minecraft, """                  this.gui.setScreen(screen);
                  eaglerBusyScreen = null;""", """                  this.gui.setScreen(screen);""")
replace(minecraft, """            if (eaglerBusyScreen != null) {
               eaglerBusyScreen.tick();
            } else {
               screen.tick();
            }""", """            screen.tick();""")

# Do not enter a hollow, non-renderable world just because 120 seconds elapsed.
# Vanilla desktop behavior is preserved; browser runs until actual installed
# center chunk/mesh, or surfaces the existing crash/cancel path.
tracker = "net/minecraft/client/multiplayer/LevelLoadTracker.java"
replace(tracker, """         if (Util.getMillis() > this.timeoutAfter) {
            LevelLoadTracker.LOGGER.warn("Timed out while waiting for the client to load chunks, letting the player into the world anyway");""",
"""         if (Util.getMillis() > this.timeoutAfter
            && !net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()) {
            LevelLoadTracker.LOGGER.warn("Timed out while waiting for the client to load chunks, letting the player into the world anyway");""")
replace(tracker, """         if (now > this.timeoutAfter) {
            LevelLoadTracker.LOGGER.warn("Timed out while waiting for the server to start chunk loading, letting the player into the world anyway");""",
"""         if (now > this.timeoutAfter
            && !net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()) {
            LevelLoadTracker.LOGGER.warn("Timed out while waiting for the server to start chunk loading, letting the player into the world anyway");""")

controller = "net/lax1dude/eaglercraft/v1_8/sp/SingleplayerServerController26.java"
replace(controller, """return ClientPlatformSingleplayer.isServerWorkerMode() && state == STATE_READY
            ? workerChunkStatusView : null;""",
"""return ClientPlatformSingleplayer.isServerWorkerMode()
            && (state == STATE_STARTING || state == STATE_READY)
            ? workerChunkStatusView : null;""") if False else None
# The source uses a tab before '?' - check the semantic expression by replacing
# its exact small substring rather than depending on indentation.
replace(controller, "ClientPlatformSingleplayer.isServerWorkerMode() && state == STATE_READY\n\t\t\t? workerChunkStatusView : null;",
       "ClientPlatformSingleplayer.isServerWorkerMode() && (state == STATE_STARTING || state == STATE_READY)\n\t\t\t? workerChunkStatusView : null;")

progress = "net/lax1dude/eaglercraft/v1_8/sp/server/EaglerProgressListener.java"
replace(progress, """\tprivate static String stageKey(Stage stage) {""",
"""\tprivate static net.minecraft.server.level.progress.LevelLoadProgressTracker vanillaProgress =
\t\tnew net.minecraft.server.level.progress.LevelLoadProgressTracker(true);
\tprivate static volatile ResourceKey<Level> focusDimension;
\tprivate static volatile ChunkPos focusChunk;

\tpublic static ResourceKey<Level> currentFocusDimension() { return focusDimension; }
\tpublic static ChunkPos currentFocusChunk() { return focusChunk; }

\t// The vanilla progress tracker weights initial + player-ready chunks.
\t// Never advertise 100% after just completing PREPARE_GLOBAL_SPAWN.
\tprivate static float cumulativeProgress(Stage stage) {
\t\treturn stage == Stage.LOAD_INITIAL_CHUNKS || stage == Stage.LOAD_PLAYER_CHUNKS
\t\t\t? Math.max(0.0f, Math.min(1.0f, vanillaProgress.get())) : -1.0f;
\t}

\tprivate static String stageKey(Stage stage) {""")
replace(progress, """\tpublic void start(Stage stage, int totalChunks) {
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage), totalChunks > 0 ? 0.0f : -1.0f);
\t}""",
"""\tpublic void start(Stage stage, int totalChunks) {
\t\tif(stage == Stage.START_SERVER) {
\t\t\tvanillaProgress = new net.minecraft.server.level.progress.LevelLoadProgressTracker(true);
\t\t\tfocusDimension = null;
\t\t\tfocusChunk = null;
\t\t}
\t\tvanillaProgress.start(stage, totalChunks);
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage), cumulativeProgress(stage));
\t}""")
replace(progress, """\tpublic void update(Stage stage, int currentChunks, int totalChunks) {
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage),
\t\t\t\ttotalChunks > 0 ? (float) currentChunks / (float) totalChunks : -1.0f);
\t}""",
"""\tpublic void update(Stage stage, int currentChunks, int totalChunks) {
\t\tvanillaProgress.update(stage, currentChunks, totalChunks);
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage), cumulativeProgress(stage));
\t}""")
replace(progress, """\tpublic void finish(Stage stage) {
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage), 1.0f);
\t}""",
"""\tpublic void finish(Stage stage) {
\t\tvanillaProgress.finish(stage);
\t\tEaglerIntegratedServerWorker26.reportProgress(stageKey(stage), cumulativeProgress(stage));
\t}""")
replace(progress, """\tpublic void updateFocus(ResourceKey<Level> dimension, ChunkPos chunkPos) {
\t}""",
"""\tpublic void updateFocus(ResourceKey<Level> dimension, ChunkPos chunkPos) {
\t\t// Follow the SAME changing focus as original Minecraft, not a fixed
\t\t// respawn chunk or a guessed area around (0,0).
\t\tfocusDimension = dimension;
\t\tfocusChunk = chunkPos;
\t}""")

worker = "net/lax1dude/eaglercraft/v1_8/sp/server/EaglerIntegratedServerWorker26.java"
replace(worker, "if (!serverWorkerMode || server == null || !server.isReady()) return;",
       "// During PREPARE_GLOBAL_SPAWN the server is intentionally NOT ready.\n\t\t// Status pixels must still show the real worldgen work being performed.\n\t\tif (!serverWorkerMode || server == null) return;")
replace(worker, """\t\t\tnet.minecraft.server.level.ServerLevel overworld = server.overworld();
\t\t\tif (overworld == null) return;
\t\t\tint radius = 13;
\t\t\tnet.minecraft.server.level.progress.ChunkLoadStatusView view = server.createChunkLoadStatusView(radius);
\t\t\tview.moveTo(net.minecraft.world.level.Level.OVERWORLD,
\t\t\t\tnet.minecraft.world.level.ChunkPos.containing(server.getRespawnData().pos()));""",
"""\t\t\tnet.minecraft.resources.ResourceKey<net.minecraft.world.level.Level> focusDimension =
\t\t\t\tEaglerProgressListener.currentFocusDimension();
\t\t\tnet.minecraft.world.level.ChunkPos focusChunk = EaglerProgressListener.currentFocusChunk();
\t\t\tif (focusDimension == null || focusChunk == null || server.getLevel(focusDimension) == null) return;
\t\t\t// EXACT vanilla 26.2 radius (Minecraft.doWorldLoad); never hardcode 27x27.
\t\t\tint radius = Math.max(5, 3) + net.minecraft.server.level.ChunkLevel.RADIUS_AROUND_FULL_CHUNK + 1;
\t\t\tnet.minecraft.server.level.progress.ChunkLoadStatusView view = server.createChunkLoadStatusView(radius);
\t\t\tview.moveTo(focusDimension, focusChunk);""")

# Narrow factual instrumentation for the FULL wait found in BOTH successful
# browser acceptance runs. Does not bypass vanilla spawn verification.
server = "net/minecraft/server/MinecraftServer.java"
replace(server, """               BlockPos testedPos = PlayerSpawnFinder.getSpawnPosInChunk(level, new ChunkPos(spawnChunk.x() + xChunkOffset, spawnChunk.z() + zChunkOffset));
               if (testedPos != null) {""",
"""               long eaglerSpawnCheckStarted = net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.isEnabled()
                  ? net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis() : 0L;
               BlockPos testedPos = PlayerSpawnFinder.getSpawnPosInChunk(level, new ChunkPos(spawnChunk.x() + xChunkOffset, spawnChunk.z() + zChunkOffset));
               if (eaglerSpawnCheckStarted != 0L) {
                  net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.slowPhase("spawn.validatedFullChunk",
                     net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis() - eaglerSpawnCheckStarted);
               }
               if (testedPos != null) {""")
print("SUCCESS: restore vanilla renderer + real in-progress worker statuses + exact native radius")
print("Worldgen algorithms, synchronous FULL spawn validation, save serialization and movement remain unchanged.")

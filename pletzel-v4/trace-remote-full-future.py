#!/usr/bin/env python3
"""Opt-in diagnostic hooks for an actual unresolved EAGLER_TELEPORT FULL future.

Does not change chunk status, tick counters, scheduler priority, teleport
semantics, player coordinates, futures or chunk-data storage. Server-side
logging only while a distant teleport is awaiting real terrain. The logs
identify whether the target holder is missing, stuck on a chunk generation
step, has an incomplete future, or is FULL but its callback has not run.
"""
import sys
from pathlib import Path
if len(sys.argv)!=2:raise SystemExit("usage: trace-remote-full-future.py <engine-root>")
root=Path(sys.argv[1])/"game/src/main/java/net/minecraft"
def edit(relative,old,new):
 p=root/relative
 s=p.read_text(encoding="utf8")
 n=s.count(old)
 if n!=1:raise AssertionError(f"{relative}: expected exactly one anchor, got {n}: {old[:100]!r}")
 p.write_text(s.replace(old,new,1),encoding="utf8")
 print("TRACE",relative)

edit("server/level/ChunkGenerationTask.java",
"""   public @Nullable CompletableFuture<?> runUntilWait() {""",
"""   public String eaglerDescribeTask() {
      return "target=" + this.targetStatus
         + ",scheduled=" + this.scheduledStatus
         + ",scheduling=" + this.schedulingStatus
         + ",activeLayer=" + this.scheduledLayer.size()
         + ",layerCursor=" + this.schedulingX + "," + this.schedulingZ
         + ",layerRadius=" + this.schedulingRadius
         + ",cancelled=" + this.markedForCancellation;
   }

   public @Nullable CompletableFuture<?> runUntilWait() {""")
edit("server/level/GenerationChunkHolder.java",
"""   public CompletableFuture<ChunkResult<ChunkAccess>> scheduleChunkGenerationTask(final ChunkStatus status, final ChunkMap scheduler) {""",
"""   public String eaglerDescribeFutures() {
      StringBuilder b = new StringBuilder(200);
      b.append("allowed=").append(this.highestAllowedStatus)
         .append(",started=").append(this.startedWork.get())
         .append(",refs=").append(this.generationRefCount.get())
         .append(",task=").append(this.task.get() == null
            ? "none" : this.task.get().eaglerDescribeTask())
         .append(",pending=[");
      for (ChunkStatus status : CHUNK_STATUSES) {
         CompletableFuture<ChunkResult<ChunkAccess>> f = this.futures.get(status.getIndex());
         if (f != null && !f.isDone()) {
            b.append(status).append(',');
         }
      }
      return b.append(']').toString();
   }

   public CompletableFuture<ChunkResult<ChunkAccess>> scheduleChunkGenerationTask(final ChunkStatus status, final ChunkMap scheduler) {""")
edit("server/level/ChunkMap.java",
"""      return result + "§r";
   }

   CompletableFuture<ChunkResult<List<ChunkAccess>>> getChunkRangeFuture(""",
"""      return result + "§r\u005cn" + chunkHolder.eaglerDescribeFutures();
   }

   CompletableFuture<ChunkResult<List<ChunkAccess>>> getChunkRangeFuture(""")
tele=root/"server/commands/TeleportCommand.java"
s=tele.read_text(encoding="utf8")
old='   private static final Map<ServerPlayer, Integer> EAGLER_PENDING_TELEPORTS = new WeakHashMap<>();'
new='''   private static final Map<ServerPlayer, Integer> EAGLER_PENDING_TELEPORTS = new WeakHashMap<>();
   private static final org.slf4j.Logger EAGLER_TP_LOGGER = com.mojang.logging.LogUtils.getLogger();
   private static final Map<ServerPlayer, EaglerTeleportProbe> EAGLER_TP_PROBES = new WeakHashMap<>();

   private static final class EaglerTeleportProbe {
      final ServerLevel level;
      final ChunkPos chunk;
      final java.util.concurrent.CompletableFuture<?> future;
      final long queuedAt;
      EaglerTeleportProbe(final ServerLevel level, final ChunkPos chunk,
                          final java.util.concurrent.CompletableFuture<?> future) {
         this.level = level;
         this.chunk = chunk;
         this.future = future;
         this.queuedAt = net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis();
      }
   }

   public static void eaglerTracePendingTeleports() {
      if (EAGLER_TP_PROBES.isEmpty()) return;
      long now = net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis();
      for (Map.Entry<ServerPlayer,EaglerTeleportProbe> item : EAGLER_TP_PROBES.entrySet()) {
         EaglerTeleportProbe p = item.getValue();
         EAGLER_TP_LOGGER.info("[PletzelTeleportTrace] age={}ms chunk={},{} fullNow={} futureDone={} debug={}",
             now - p.queuedAt, p.chunk.x(), p.chunk.z(),
             p.level.getChunkSource().getChunkNow(p.chunk.x(),p.chunk.z()) != null,
             p.future.isDone(), p.level.getChunkSource().getChunkDebugData(p.chunk));
      }
   }
'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''            level.getChunkSource()
               .addTicketAndLoadWithRadius(TicketType.EAGLER_TELEPORT, destinationChunk, 0)
               .whenCompleteAsync((ignored, failure) -> {'''
new='''            java.util.concurrent.CompletableFuture<?> terrainFuture = level.getChunkSource()
               .addTicketAndLoadWithRadius(TicketType.EAGLER_TELEPORT, destinationChunk, 0);
            EAGLER_TP_PROBES.put(player, new EaglerTeleportProbe(level, destinationChunk, terrainFuture));
            EAGLER_TP_LOGGER.info("[PletzelTeleportTrace] QUEUED chunk={},{} debug={}",
               destinationChunk.x(), destinationChunk.z(),
               level.getChunkSource().getChunkDebugData(destinationChunk));
            terrainFuture.whenCompleteAsync((ignored, failure) -> {
                  EaglerTeleportProbe probe = EAGLER_TP_PROBES.get(player);
                  if (probe != null && probe.future == terrainFuture) {
                     EAGLER_TP_PROBES.remove(player);
                  }
                  EAGLER_TP_LOGGER.info("[PletzelTeleportTrace] FINISHED chunk={},{} failure={} fullNow={}",
                    destinationChunk.x(), destinationChunk.z(), failure,
                    level.getChunkSource().getChunkNow(destinationChunk.x(),destinationChunk.z()) != null);'''
assert s.count(old)==1
s=s.replace(old,new,1)
tele.write_text(s,encoding="utf8")
print("TRACE server/commands/TeleportCommand.java")
edit("server/MinecraftServer.java",
"""      this.tickCount++;
      this.tickRateManager.tick();
      this.tickChildren(haveTime);""",
"""      this.tickCount++;
      this.tickRateManager.tick();
      // Opt-in low-frequency telemetry of deferred FULL chunk progress;
      // no scheduling, simulation, ticket or player-position changes.
      if (net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.isEnabled()
            && this.tickCount % 200 == 0) {
         net.minecraft.server.commands.TeleportCommand.eaglerTracePendingTeleports();
      }
      this.tickChildren(haveTime);""")
print("Installed 10-second server/teleport/holder/task source-only diagnostic")

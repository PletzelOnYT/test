#!/usr/bin/env python3
"""Bounded browser startup batching + opt-in monotonic queue/stage timing.

The vanilla ChunkPyramid, ticket levels, chunk coordinates, futures, and generation
algorithms are not modified. Only before the first interactive tick is the
conservative 2-item scheduling layer raised to 16 items. The worldgen coroutine
still yields after its existing deadline, and interactive gameplay retains 2/4.
The opt-in probes separate executor queue waiting from command execution and
measure the completion latency of each required status layer.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:
    raise SystemExit("usage: repair-startup-batch-probe.py <engine>")
root=Path(sys.argv[1])/"game/src/main/java"
def edit(rel, pairs):
    path=root/rel
    s=path.read_text()
    for tag,old,new in pairs:
        n=s.count(old)
        if n != 1:
            # 26.2's Eagler Java sources use tabs; the patch snippets are
            # visually aligned using spaces for readability. Match exact
            # indentation after converting whole leading 4-space groups.
            import re
            old=re.sub(r"(?m)^( +)", lambda m: "\t" * (len(m.group(1)) // 4) + " " * (len(m.group(1)) % 4), old)
            n=s.count(old)
        if n != 1:
            raise AssertionError(f"{rel}: {tag}: expected 1 anchor, got {n}")
        s=s.replace(old,new,1)
        print("STARTUP_BATCH_PROBE",rel,tag)
    path.write_text(s)
edit("net/lax1dude/eaglercraft/v1_8/sp/server/EaglerServerState.java",[
("startup-only batch", "private static final int NORMAL_WORLDGEN_LAYER_BATCH = 2;",
"""private static final int NORMAL_WORLDGEN_LAYER_BATCH = 2;
    // During initial preparation there are no simulation ticks to protect.
    // Collapse thousands of 2-item continuation hops into bounded 16-item runs.
    private static final int STARTUP_WORLDGEN_LAYER_BATCH = 16;"""),
("preserve interactive adaptive governor",
"""public static int getWorldgenLayerBatchSize() {
        return worldgenLayerBatch;
    }""",
"""public static int getWorldgenLayerBatchSize() {
        return interactiveWorldgen ? worldgenLayerBatch : STARTUP_WORLDGEN_LAYER_BATCH;
    }""")
])
edit("net/lax1dude/eaglercraft/v1_8/sp/server/EaglerWorldgenExecutor.java",[
("remember dequeue time", """Runnable command;
            boolean resumedFromIdle = false;""",
"""Runnable command;
            long enqueuedAt;
            boolean resumedFromIdle = false;"""),
("priority queue timing", """command = priorityQueue.removeFirst();
                    priorityEnqueuedAt.removeFirst();""",
"""command = priorityQueue.removeFirst();
                    enqueuedAt = priorityEnqueuedAt.removeFirst();"""),
("normal queue timing", """command = queue.removeFirst();
                    queueEnqueuedAt.removeFirst();""",
"""command = queue.removeFirst();
                    enqueuedAt = queueEnqueuedAt.removeFirst();"""),
("separate waiting and active duration", """if (perf) {
                EaglerServerPerf.worldgenCompleted(EagRuntime.steadyTimeMillis() - taskStarted, remaining);
            }""",
"""if (perf) {
                long completedAt = EagRuntime.steadyTimeMillis();
                EaglerServerPerf.worldgenCompleted(completedAt - taskStarted, remaining);
                if (!EaglerServerState.isInteractiveWorldgen()) {
                    EaglerServerPerf.startupQueueTask(Math.max(0L, taskStarted - enqueuedAt),
                        Math.max(0L, completedAt - taskStarted), pickedPriority);
                }
            }""")
])
edit("net/minecraft/server/level/ChunkGenerationTask.java",[
("start stage latency clock", """CompletableFuture<ChunkResult<ChunkAccess>> future = chunkHolder.applyStep(pyramid.getStepTo(status), this.chunkMap, this.cache);
      ChunkResult<ChunkAccess> now = future.getNow(null);""",
"""boolean measureStartupStage = net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.isEnabled()
         && !net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerState.isInteractiveWorldgen();
      long startedAt = measureStartupStage ? net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis() : 0L;
      CompletableFuture<ChunkResult<ChunkAccess>> future = chunkHolder.applyStep(pyramid.getStepTo(status), this.chunkMap, this.cache);
      if (measureStartupStage) {
         int stageIndex = status.getIndex();
         net.minecraft.world.level.ChunkPos target = chunkHolder.getPos();
         net.minecraft.world.level.ChunkPos focus =
            net.lax1dude.eaglercraft.v1_8.sp.server.EaglerProgressListener.currentFocusChunk();
         int radius = focus == null ? -1
            : Math.max(Math.abs(target.x() - focus.x()), Math.abs(target.z() - focus.z()));
         future.whenComplete((result, problem) ->
            net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.startupStageCompleted(
               stageIndex, Math.max(0L, net.lax1dude.eaglercraft.v1_8.EagRuntime.steadyTimeMillis() - startedAt), radius));
      }
      ChunkResult<ChunkAccess> now = future.getNow(null);""")
])
edit("net/lax1dude/eaglercraft/v1_8/sp/server/EaglerServerPerf.java",[
("monotonic startup counters", """public static void worldgenQueued(final int depth) {""",
"""private static final long[] pletzelStartupStageCount = new long[12];
    private static final long[] pletzelStartupStageSum = new long[12];
    private static final long[] pletzelStartupStageMax = new long[12];
    private static final long[] pletzelStartupStageOutside = new long[12];
    private static long pletzelQueueTasks, pletzelQueueWait, pletzelQueueWork;
    private static long pletzelQueueWaitMax, pletzelQueueWorkMax, pletzelPriorityTasks;

    public static synchronized void startupQueueTask(final long queueWait, final long work, final boolean priority) {
        if (!enabled) return;
        pletzelQueueTasks++;
        pletzelQueueWait += queueWait;
        pletzelQueueWork += work;
        pletzelQueueWaitMax = Math.max(pletzelQueueWaitMax, queueWait);
        pletzelQueueWorkMax = Math.max(pletzelQueueWorkMax, work);
        if (priority) pletzelPriorityTasks++;
    }

    public static synchronized void startupStageCompleted(final int status, final long elapsed, final int radius) {
        if (!enabled || status < 0 || status >= pletzelStartupStageCount.length) return;
        pletzelStartupStageCount[status]++;
        pletzelStartupStageSum[status] += elapsed;
        pletzelStartupStageMax[status] = Math.max(pletzelStartupStageMax[status], elapsed);
        // Radius 13 encompasses the vanilla dependency footprint of 5x5 FULL.
        if (radius > 13) pletzelStartupStageOutside[status]++;
    }

    public static void worldgenQueued(final int depth) {"""),
("periodic startup stage timing", """lastHeartbeatAtMillis = now;
        long activeTickMillis""",
"""lastHeartbeatAtMillis = now;
        // These measurements are emitted by the worker supervisor even while
        // initial spawn has not completed its first server tick.
        if (!EaglerServerState.isInteractiveWorldgen()) {
            synchronized (EaglerServerPerf.class) {
                if (pletzelQueueTasks > 0L) {
                    LOGGER.info("[PletzelStartupQueue] at={}ms tasks={} priority={} waitAvg={}ms waitMax={}ms execAvg={}ms execMax={}ms batch={}",
                        now, pletzelQueueTasks, pletzelPriorityTasks,
                        pletzelQueueWait / pletzelQueueTasks, pletzelQueueWaitMax,
                        pletzelQueueWork / pletzelQueueTasks, pletzelQueueWorkMax,
                        EaglerServerState.getWorldgenLayerBatchSize());
                    pletzelQueueTasks = pletzelPriorityTasks = pletzelQueueWait = pletzelQueueWork = 0L;
                    pletzelQueueWaitMax = pletzelQueueWorkMax = 0L;
                }
                for (int i = 0; i < pletzelStartupStageCount.length; i++) {
                    long count = pletzelStartupStageCount[i];
                    if (count != 0L) {
                        LOGGER.info("[PletzelStartupStage] at={}ms status={} count={} futureAvg={}ms futureMax={}ms outsideCriticalRadius={}",
                            now, STAGE_NAMES[i], count, pletzelStartupStageSum[i] / count,
                            pletzelStartupStageMax[i], pletzelStartupStageOutside[i]);
                        pletzelStartupStageCount[i] = pletzelStartupStageSum[i]
                            = pletzelStartupStageMax[i] = pletzelStartupStageOutside[i] = 0L;
                    }
                }
            }
        }
        long activeTickMillis""")
])
print("TARGETED SOURCE PATCH DONE; exact worldgen functions and interactive 2/4 governor unchanged")

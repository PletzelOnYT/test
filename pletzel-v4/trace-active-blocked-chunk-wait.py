#!/usr/bin/env python3
"""Show exact pending synchronous FULL chunk in a live macOS Chrome stall.

The existing [EagPerfChunkWait] log only prints AFTER managedBlock finally
returns. When a Mac browser becomes permanently STALLED, that log is absent.
This opt-in real worker heartbeat probe exposes the requested chunk/status
WHILE the main server tick is still blocked, without completing/cancelling
its future or changing TPS, chunk data or rendering.

All added writes/logging remain behind existing ?perfdebug switch.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: trace-active-blocked-chunk-wait.py <engine-root>")
root=Path(sys.argv[1])/"game/src/main/java"
perf=root/"net/lax1dude/eaglercraft/v1_8/sp/server/EaglerServerPerf.java"
src=perf.read_text(encoding="utf8")
old="	private static volatile String liveTickPhase = \"idle\";"
new="""\tprivate static volatile String liveTickPhase = "idle";
\tprivate static volatile String liveBlockingChunkTarget = "none";
\tprivate static volatile long liveBlockingChunkStartedAtMillis;

\tpublic static void beginBlockingChunkWait(final String status, final int cx, final int cz,
\t\t\tfinal boolean loadOrGenerate) {
\t\tif (enabled) {
\t\t\tliveBlockingChunkTarget = status + "@" + cx + "," + cz + " load=" + loadOrGenerate
\t\t\t\t+ " phase=" + liveTickPhase;
\t\t\tliveBlockingChunkStartedAtMillis = EagRuntime.steadyTimeMillis();
\t\t}
\t}

\tpublic static void finishBlockingChunkWait() {
\t\tif (enabled) {
\t\t\tliveBlockingChunkStartedAtMillis = 0L;
\t\t\tliveBlockingChunkTarget = "none";
\t\t}
\t}
"""
assert src.count(old)==1,"existing EagPerf heartbeat state signature changed"
src=src.replace(old,new,1)
needle="""		lastHeartbeatAtMillis = now;"""
insert="""		lastHeartbeatAtMillis = now;
		long pendingChunkMs = liveBlockingChunkStartedAtMillis == 0L ? 0L
			: Math.max(0L, now - liveBlockingChunkStartedAtMillis);
		if (pendingChunkMs >= 1000L) {
			LOGGER.warn("[PletzelActiveChunkWait] waiting={}ms requested={} serverTick={} phase={} "
				+ "worldgenQueue={} claims={} tasks={} workerMessageBatches={}",
				pendingChunkMs, liveBlockingChunkTarget, liveTickNumber, liveTickPhase,
				liveWorldgenQueueDepth, liveGenerationClaims, liveGenerationTasks, liveWorkerMessageBatches);
		}"""
# Only modify the actual supervisor heartbeat, not setEnabled initialization.
start=src.index("\tpublic static void heartbeat()")
assert src[start:].count(needle)==1,"could not isolate supervisor heartbeat"
src=src[:start]+src[start:].replace(needle,insert,1)
perf.write_text(src,encoding="utf8")
chunk=root/"net/minecraft/server/level/ServerChunkCache.java"
s=chunk.read_text(encoding="utf8")
old="\n         this.mainThreadProcessor.managedBlock(serverFuture::isDone);"
new="""         if (eaglerPerf) {
            net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.beginBlockingChunkWait(
               targetStatus.toString(), x, z, loadOrGenerate);
         }
         try {
            this.mainThreadProcessor.managedBlock(serverFuture::isDone);
         } finally {
            if (eaglerPerf) {
               net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.finishBlockingChunkWait();
            }
         }"""
assert s.count(old)==1,"getChunkFuture managedBlock source mismatch"
s=s.replace(old,new,1)
old="\n      this.mainThreadProcessor.managedBlock(serverFuture::isDone);"
new="""      if (eaglerPerf) {
         net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.beginBlockingChunkWait(
            targetStatus.toString(), x, z, loadOrGenerate);
      }
      try {
         this.mainThreadProcessor.managedBlock(serverFuture::isDone);
      } finally {
         if (eaglerPerf) {
            net.lax1dude.eaglercraft.v1_8.sp.server.EaglerServerPerf.finishBlockingChunkWait();
         }
      }"""
assert s.count(old)==1,"main getChunk managedBlock source mismatch"
s=s.replace(old,new,1)
chunk.write_text(s,encoding="utf8")
print("PATCHED: worker heartbeat will expose exact pending blocking chunk during STALLED state")
print("NO fake TPS, no future cancellation, no server/thread restart and no gameplay changes")

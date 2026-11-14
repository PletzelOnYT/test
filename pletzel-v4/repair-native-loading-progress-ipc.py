#!/usr/bin/env python3
"""Use genuine IPC 0x0D server stage progress in native 26.2 LevelLoadingScreen.

The split WasmGC worker owns the LevelLoadListener Stage callbacks; the
client's LevelLoadTracker.serverStage can remain null and suppress the native
progress bar even though EaglerProgressListener sends real currentChunks /
totalChunks through IPC. Keep desktop/local behavior byte-identical.
The colored cells already use real IPC23 stage snapshots and are unchanged.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: repair-native-loading-progress-ipc.py <engine-root>")
path=Path(sys.argv[1])/"game/src/main/java/net/minecraft/client/multiplayer/LevelLoadTracker.java"
s=path.read_text(encoding="utf8")
old="""   public float serverProgress() {
      return this.serverProgressTracker.get();
   }

   public boolean hasProgress() {
      return this.serverStage != null;
   }"""
new="""   public float serverProgress() {
      if (this.serverStage == null &&
            net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isBrowserRuntime() &&
            net.lax1dude.eaglercraft.v1_8.sp.SingleplayerServerController26.getWorkerChunkStatusView() != null) {
         // The WASM-GC server runs the real LevelLoadListener on a separate
         // worker. Its progress travels through IPC 0x0D and is never fabricated
         // from local ticks or decorative counters.
         float actualServerProgress =
            net.lax1dude.eaglercraft.v1_8.sp.SingleplayerServerController26.worldStatusProgress();
         if (actualServerProgress >= 0.0F) {
            return Math.max(0.0F, Math.min(1.0F, actualServerProgress));
         }
      }
      return this.serverProgressTracker.get();
   }

   public boolean hasProgress() {
      return this.serverStage != null || (
         net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isBrowserRuntime() &&
         net.lax1dude.eaglercraft.v1_8.sp.SingleplayerServerController26.getWorkerChunkStatusView() != null &&
         net.lax1dude.eaglercraft.v1_8.sp.SingleplayerServerController26.worldStatusProgress() >= 0.0F
      );
   }"""
n=s.count(old)
if n!=1:raise AssertionError(f"Unexpected 26.2 LevelLoadTracker source: count={n}")
path.write_text(s.replace(old,new,1),encoding="utf8")
print("PATCHED: native 26.2 progress bar uses real worker IPC 0x0D stage fraction")

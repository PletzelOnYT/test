#!/usr/bin/env python3
"""Avoid documented 17.37s FULL-chunk wait inside a browser trial-spawner tick.

The captured real Chromium heartbeat showed:
  phase=levels.blockEntities, callerKind=block_entity,
  callerType=minecraft:trial_spawner, requested=3,4,
  chunk.sync.minecraft:full=17370ms.
Do not modify vanilla spawning rules. A browser-hosted spawner may tick only
when the chunk area that its configured player scanning / spawning can inspect
is already FULL and available nonblocking. The player chunk system continues
normal asynchronous loading and the spawner resumes unchanged on later ticks.
Desktop Java behavior and Schematica are completely untouched.
"""
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit("usage: repair-trial-spawner-full-chunk-guard.py <pinned-engine-root>")
path=Path(sys.argv[1])/"game/src/main/java/net/minecraft/world/level/block/entity/trialspawner/TrialSpawner.java"
source=path.read_text(encoding="utf-8")
original="""   public void tickServer(final ServerLevel serverLevel, final BlockPos spawnerPos, final boolean isOminous) {
      this.isOminous = isOminous;"""
replacement="""   public void tickServer(final ServerLevel serverLevel, final BlockPos spawnerPos, final boolean isOminous) {
      // Pletzel V4 browser-only fix: trial-spawner raycasts and spawn checks
      // must not synchronously generate neighboring FULL chunks from inside a
      // live server tick. Doing so held levels.blockEntities for 17.37 seconds
      // in an observed Chromium Survival session, freezing ALL entity updates.
      //
      // getChunkNow() checks COMPLETED FULL chunks without initiating generation.
      // hasChunk() is insufficient: its ticket-level check may report a chunk
      // that has not yet reached FULL status.
      //
      // Bound the required area by the vanilla player-detection distance plus
      // one chunk for spawn collision / raycasts. When missing, defer this one
      // spawner tick; the ordinary chunk-ticket pipeline remains responsible
      // for loading chunks asynchronously. Never skip or fake global ticks.
      if (net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()
            && net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
                 != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP) {
         final int radius = Math.max(16, this.getRequiredPlayerRange());
         final int minX = net.minecraft.core.SectionPos.blockToSectionCoord(spawnerPos.getX() - radius);
         final int maxX = net.minecraft.core.SectionPos.blockToSectionCoord(spawnerPos.getX() + radius);
         final int minZ = net.minecraft.core.SectionPos.blockToSectionCoord(spawnerPos.getZ() - radius);
         final int maxZ = net.minecraft.core.SectionPos.blockToSectionCoord(spawnerPos.getZ() + radius);
         for (int cx = minX; cx <= maxX; ++cx) {
            for (int cz = minZ; cz <= maxZ; ++cz) {
               if (serverLevel.getChunkSource().getChunkNow(cx, cz) == null) {
                  return;
               }
            }
         }
      }
      this.isOminous = isOminous;"""
n=source.count(original)
if n!=1:raise AssertionError(f"pinned TrialSpawner.tickServer signature changed: expected 1, got {n}")
source=source.replace(original,replacement,1)
path.write_text(source,encoding="utf-8")
print("PATCHED browser-only nonblocking trial spawner tick preflight")

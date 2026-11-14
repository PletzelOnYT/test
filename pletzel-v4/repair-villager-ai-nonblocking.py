#!/usr/bin/env python3
"""Avoid a measured 6258ms villager Brain neighbor-FULL synchronous chunk wait.

This is a narrowly scoped browser-only guard for *villager AI* (not all entities).
Captured survival remote-teleport run:
 [EagPerfChunkWait] elapsed=6258ms status=minecraft:full requested=-1,6
 phase=levels.entities callerKind=entity callerType=minecraft:villager
 callerChunk=0,3.
Villager Brain can probe distant POI/pathfinding chunks while they are still
generating on browser-hosted worldgen fiber; ensure nearby FULL chunks exist
without blocking before invoking the Brain. The outer Entity.tick still runs,
including physics and health. Resume vanilla Villager AI when chunks are ready.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: repair-villager-ai-nonblocking.py <engine-root>")
path=Path(sys.argv[1])/"game/src/main/java/net/minecraft/world/entity/npc/villager/Villager.java"
src=path.read_text(encoding="utf8")
old="""   @Override
   protected void customServerAiStep(final ServerLevel level) {
      ProfilerFiller profiler = Profiler.get();"""
new="""   @Override
   protected void customServerAiStep(final ServerLevel level) {
      // Browser-hosted Villager Brain pathfinding/POI queries may synchronously
      // request FULL chunks several chunks away, starving ALL server ticks.
      // This conservative nonblocking preflight checks a 3-chunk radius, which
      // includes the recorded requested chunk. Missing areas defer only the
      // Villager AI step; the outer entity tick and physics still progress.
      // No fake chunk, dropped packet, altered AI rule, or desktop change.
      if (net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()
            && net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
                 != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP) {
         net.minecraft.world.level.ChunkPos center = this.chunkPosition();
         for (int cx = center.x() - 3; cx <= center.x() + 3; ++cx) {
            for (int cz = center.z() - 3; cz <= center.z() + 3; ++cz) {
               if (level.getChunkSource().getChunkNow(cx, cz) == null) {
                  return;
               }
            }
         }
      }
      ProfilerFiller profiler = Profiler.get();"""
assert src.count(old)==1, "Pinned Villager.customServerAiStep signature differs; do not patch"
path.write_text(src.replace(old,new,1),encoding="utf8")
print("PATCHED: hosted-browser Villager Brain nonblocking FULL-neighbor preflight; outer entity physics unchanged")

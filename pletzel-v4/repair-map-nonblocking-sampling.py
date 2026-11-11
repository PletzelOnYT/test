#!/usr/bin/env python3
"""Stop filled-map color sampling from synchronously generating FULL chunks.

Real integrated-server perf traces show chunk.sync.minecraft:full pauses in
the tens of seconds while a filled map is held and the player teleports.
The vanilla MapItem.update scans up to 128x128 map pixels, and each column
uses Level.getChunk(x,z), which may synchronously generate FULL chunks beyond
the player-visible ticket set.

In browser / Web Worker only: sample genuine completed LevelChunk data already
resident in the server chunk cache; defer unsatisfied map pixels to future map
updates. There is NO fake terrain, fake map color, chunk hiding, packet dropping
or render distance reduction. Desktop/normal vanilla keeps its original path.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
p=root/"game/src/main/java/net/minecraft/world/item/MapItem.java"
source=p.read_text(encoding="utf-8")
old='''                     LevelChunk chunk = level.getChunk(SectionPos.blockToSectionCoord(averagingAreaMinX), SectionPos.blockToSectionCoord(averagingAreaMinZ));
                     if (!chunk.isEmpty()) {'''
new='''                     int mapChunkX = SectionPos.blockToSectionCoord(averagingAreaMinX);
                     int mapChunkZ = SectionPos.blockToSectionCoord(averagingAreaMinZ);
                     LevelChunk chunk;
                     if (level instanceof ServerLevel serverLevel
                        && net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
                           != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP) {
                        // On the singleplayer Web Worker, map sampling may NEVER
                        // block on getChunk(..., FULL, true). Map pixels are
                        // filled from real completed chunks when available.
                        chunk = serverLevel.getChunkSource().getChunkNow(mapChunkX, mapChunkZ);
                        if (chunk == null) {
                           continue;
                        }
                     } else {
                        chunk = level.getChunk(mapChunkX, mapChunkZ);
                     }
                     if (!chunk.isEmpty()) {'''
assert source.count(old)==1,"26.2 MapItem real chunk sampler changed; fix anchor"
source=source.replace(old,new,1)
assert source.count("getChunkNow(mapChunkX, mapChunkZ)")==1
assert source.count("level.getChunk(mapChunkX, mapChunkZ)")==1
p.write_text(source,encoding="utf-8")
print("Browser filled-map colors now read real FULL-resident chunks without synchronous generation",flush=True)
print("No changes to desktop vanilla map sampling or missing-chunk terrain colors",flush=True)

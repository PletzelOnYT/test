#!/usr/bin/env python3
"""Keep expensive normal/biome noise generation async on the existing bounded worldgen
executor instead of TeaVM's INLINE ForkJoinPool; desktop code remains untouched.
Does not change vanilla biome/noise/structures/lighting or Pletzel rendering.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")/"game/src/main/java"
ref={
"net/minecraft/world/level/levelgen/NoiseBasedChunkGenerator.java":[
 'Util.backgroundExecutor().forName("init_biomes")',
 'Util.backgroundExecutor().forName("wgen_fill_noise")'],
"net/minecraft/world/level/chunk/ChunkGenerator.java":[
 'Util.backgroundExecutor().forName("init_biomes")']
}
# Browser hosted: the background ForkJoinPool is currently an inline executor.
# Delegate only actual chunk-generation call sites to the existing FIFO coroutine,
# which has timer-aware preemption and a bounded lighting priority queue.
prefix="""(net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()
                  && net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
                    != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP
               ? net.lax1dude.eaglercraft.v1_8.sp.server.EaglerWorldgenExecutor.INSTANCE
               : {original})"""
for rel,patterns in ref.items():
 p=root/rel
 src=p.read_text()
 for old in patterns:
  n=src.count(old)
  if n!=1:raise AssertionError(f'{rel}: expected exactly one {old}, found {n}')
  src=src.replace(old,prefix.format(original=old),1)
 p.write_text(src)
 print(f"PATCHED {rel}: {len(patterns)} host-browser-only async worldgen entrypoints")
print("Preserved desktop Java pool, world generation code, lighting, and all GUI/render classes.")

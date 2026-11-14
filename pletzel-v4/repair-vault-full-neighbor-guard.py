#!/usr/bin/env python3
"""Defer only browser Vault block-entity ticks while adjacent FULL chunks are absent.

Measured unmodified gameplay after prior trial/villager guards:
  - 5642ms: minecraft:vault requested=0,13, callerChunk=0,12
  - 4442ms: minecraft:vault requested=-16,9, callerChunk=-17,9
  - 5976ms: minecraft:vault requested=1,0, callerChunk=2,0

This patch does NOT fake TPS or chunk statuses. It skips one Vault tick until
normal async chunk tickets make the boundary FULL; the rest of the server,
entities, and chunk pipeline keep operating. It is intentionally browser-only
and applies to no desktop runtime. Vanilla vault logic is untouched otherwise.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:
    raise SystemExit("usage: repair-vault-full-neighbor-guard.py <pinned-engine-root>")
path=Path(sys.argv[1])/"game/src/main/java/net/minecraft/world/level/block/entity/vault/VaultBlockEntity.java"
src=path.read_text(encoding="utf8")
old="""      ) {
         VaultState currentState = blockState.getValue(VaultBlock.STATE);
         if (shouldCycleDisplayItem(serverLevel.getGameTime(), currentState)) {"""
new="""      ) {
         // Pletzel V4 hosted-browser safety preflight. Real gameplay traces
         // demonstrate that a vault can synchronously request a neighboring
         // FULL chunk for 4.4-6.0 seconds inside levels.blockEntities, which
         // starves all world/entity ticks on the cooperative worker. Guard
         // the original logic only until immediate neighboring FULL chunks
         // are already present. No fake chunks, altered loot tables or timers.
         if (net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()
               && net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
                    != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP) {
            final int minX = net.minecraft.core.SectionPos.blockToSectionCoord(pos.getX() - 16);
            final int maxX = net.minecraft.core.SectionPos.blockToSectionCoord(pos.getX() + 16);
            final int minZ = net.minecraft.core.SectionPos.blockToSectionCoord(pos.getZ() - 16);
            final int maxZ = net.minecraft.core.SectionPos.blockToSectionCoord(pos.getZ() + 16);
            for (int cx = minX; cx <= maxX; ++cx) {
               for (int cz = minZ; cz <= maxZ; ++cz) {
                  if (serverLevel.getChunkSource().getChunkNow(cx, cz) == null) {
                     return;
                  }
               }
            }
         }
         VaultState currentState = blockState.getValue(VaultBlock.STATE);
         if (shouldCycleDisplayItem(serverLevel.getGameTime(), currentState)) {"""
n=src.count(old)
if n!=1:
    raise AssertionError(f"Unexpected vault server tick signature; expected exactly 1, got {n}")
src=src.replace(old,new,1)
path.write_text(src,encoding="utf8")
print("PATCHED hosted-browser VaultBlockEntity.Server.tick nonblocking adjacent FULL preflight")

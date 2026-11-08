#!/usr/bin/env python3
"""Fix Mac Chrome 4s structure-starts sync wait during ServerPlayer.doTick.

Location advancements can dereference structure starts from chunks other than
the player's collision neighborhood. StructureManager.fillStartsForStructure()
calls level.getChunk(..., STRUCTURE_STARTS), which blocks a single-threaded
integrated server while waiting for worldgen. Prefetch ONLY those referenced
structure stages nonblocking and retry the original predicate until ready.

The real 26.2 advancement predicate and structure check are not deleted or
simplified. Server movement and anti-cheat remain untouched; Java/desktop
server semantics are unchanged.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit("usage: repair-player-structure-starts-nonblocking.py <engine-root>")
root=Path(sys.argv[1])/"game/src/main/java/net/minecraft"
def patch(rel,old,new):
    p=root/rel
    s=p.read_text(encoding="utf8")
    if s.count(old)!=1:raise AssertionError(f"Expected exactly one source anchor in {rel}: got {s.count(old)}")
    p.write_text(s.replace(old,new,1),encoding="utf8")
    print("FIELD_FIX",rel)
patch("server/level/ServerChunkCache.java",
"""   private CompletableFuture<ChunkResult<ChunkAccess>> getChunkFutureMainThread(
      final int x, final int z, final ChunkStatus targetStatus, final boolean loadOrGenerate
   ) {""",
"""   // Browser advancement structure lookups must NEVER enter managedBlock while
   // running inside connection.listener / ServerPlayer.doTick. The normal
   // chunk-status future is scheduled and allowed to finish naturally.
   // No fabricated completion or blocking join; this is only an opt-in
   // alternative for callers that explicitly defer work until it is ready.
   public CompletableFuture<ChunkResult<ChunkAccess>> eaglerRequestChunkStatusNoWait(
      final int x, final int z, final ChunkStatus targetStatus
   ) {
      if (Thread.currentThread() != this.mainThread) {
         throw new IllegalStateException("Nonblocking chunk request must run on the server thread");
      }
      return this.getChunkFutureMainThread(x, z, targetStatus, true);
   }

   public @Nullable ChunkAccess eaglerGetChunkStatusIfPresent(
      final int x, final int z, final ChunkStatus status
   ) {
      if (Thread.currentThread() != this.mainThread) {
         return null;
      }
      ChunkHolder holder = this.getVisibleChunkIfPresent(ChunkPos.pack(x, z));
      return holder == null ? null : holder.getChunkIfPresent(status);
   }

   private CompletableFuture<ChunkResult<ChunkAccess>> getChunkFutureMainThread(
      final int x, final int z, final ChunkStatus targetStatus, final boolean loadOrGenerate
   ) {""")
patch("world/level/StructureManager.java",
"""import net.minecraft.server.level.WorldGenRegion;""",
"""import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.world.level.chunk.LevelChunk;""")
patch("world/level/StructureManager.java",
"""   public StructureStart getStructureWithPieceAt(final BlockPos blockPos, final HolderSet<Structure> structures) {""",
"""   /**
    * Structure-based advancements are checked every 20 player ticks. An
    * already FULL player's chunk can reference STRUCTURE_STARTS in other
    * chunks which are not yet loaded; vanilla fillStartsForStructure would
    * synchronously block the integrated server for seconds. Start precisely
    * those existing chunk-status futures asynchronously, and let the
    * advancement predicate retry normally once ALL required starts are ready.
    * The actual structure data and original predicate remain authoritative.
    */
   public boolean eaglerStructureStartsAvailableWithoutBlocking(final BlockPos pos,
      final HolderSet<Structure> matchingStructures) {
      if (!(this.level instanceof ServerLevel serverLevel)) {
         return true;
      }
      ServerChunkCache cache = serverLevel.getChunkSource();
      ChunkPos center = ChunkPos.containing(pos);
      LevelChunk current = cache.getChunkNow(center.x(), center.z());
      if (current == null) {
         // Player's own FULL center chunk is supplied by existing player
         // tickets; it is never synthesized or forced ready.
         return false;
      }

      Registry<Structure> registry = this.registryAccess().lookupOrThrow(Registries.STRUCTURE);
      boolean allReady = true;
      for (Entry<Structure, LongSet> entry : current.getAllReferences().entrySet()) {
         // Do not request unrelated structures from every advancement.
         if (!registry.get(registry.getId(entry.getKey())).map(matchingStructures::contains).orElse(false)) {
            continue;
         }
         LongIterator cursor = entry.getValue().iterator();
         while (cursor.hasNext()) {
            ChunkPos referenced = ChunkPos.unpack(cursor.nextLong());
            if (cache.eaglerGetChunkStatusIfPresent(referenced.x(), referenced.z(), ChunkStatus.STRUCTURE_STARTS) == null) {
               cache.eaglerRequestChunkStatusNoWait(referenced.x(), referenced.z(), ChunkStatus.STRUCTURE_STARTS);
               allReady = false;
            }
         }
      }
      return allReady;
   }

   public StructureStart getStructureWithPieceAt(final BlockPos blockPos, final HolderSet<Structure> structures) {""")
patch("world/level/StructureManager.java",
"""import net.minecraft.world.level.chunk.StructureAccess;""",
"""import net.minecraft.world.level.chunk.StructureAccess;
import net.minecraft.world.level.chunk.LevelChunk;""" if False else """import net.minecraft.world.level.chunk.StructureAccess;""")
# Now the narrow advancement-only check in the existing LOCATION predicate.
patch("advancements/predicates/LocationPredicate.java",
"""      if (!this.biomes.isPresent() || loaded && this.biomes.get().contains(level.getBiome(pos))) {
         if (!this.structures.isPresent() || loaded && level.structureManager().getStructureWithPieceAt(pos, this.structures.get()).isValid()) {""",
"""      if (!this.biomes.isPresent() || loaded && this.biomes.get().contains(level.getBiome(pos))) {
         if (!this.structures.isPresent() || loaded
            && (!net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isBrowserRuntime()
               || level.structureManager().eaglerStructureStartsAvailableWithoutBlocking(pos, this.structures.get()))
            && level.structureManager().getStructureWithPieceAt(pos, this.structures.get()).isValid()) {""")
print("STRUCTURE_STARTS player advancement now retries after real futures finish; no anti-cheat or content changes.")

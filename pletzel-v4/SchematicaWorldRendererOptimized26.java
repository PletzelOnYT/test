package net.pletzel.schematica;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.QuadInstance;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.block.BlockStateModelSet;
import net.minecraft.client.renderer.block.dispatch.BlockStateModel;
import net.minecraft.client.renderer.block.dispatch.BlockStateModelPart;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.client.renderer.state.level.CameraRenderState;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.model.geometry.BakedQuad;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.SectionPos;
import net.minecraft.util.ARGB;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * Native no-voice, section-indexed hologram renderer.
 *
 * Source schematic cells remain in SchematicaSession; an independent,
 * incremental 16x16x16 spatial index is built only once per schematic version.
 * A bounded LRU contains baked section geometry ONLY for sections in the
 * camera frustum, inside the player's chosen render distance, and whose real
 * client-world chunks are already loaded. No chunk tickets are requested.
 *
 * Minecraft 26.2's custom geometry API restages visible quads every frame:
 * this is not persistent GPU-resident VBO meshing. The per-frame quad budget,
 * solid interior-face culling and small LRU bound that cost explicitly.
 */
public final class SchematicaWorldRenderer {
    private static final int INDEX_CELLS_PER_FRAME=8192;
    private static final long INDEX_NANOS_PER_FRAME=2500000L;
    private static final int MESH_CELLS_PER_FRAME=2048;
    private static final long MESH_NANOS_PER_FRAME=2500000L;
    private static final int CACHE_SECTION_LIMIT=64;
    private static final int CACHE_CELL_LIMIT=65536;
    private static final int FRAME_QUAD_LIMIT=100000;
    private static final long REPORT_INTERVAL_NANOS=5000000000L;

    private static final Map<BlockState,List<BakedQuad>> MODEL_CACHE=new HashMap<>();
    private static BlockStateModelSet modelCacheOwner;
    private static final Map<Long,SourceSection> INDEX=new HashMap<>();
    private static final LinkedHashMap<Long,MeshSection> MESH_CACHE=new LinkedHashMap<>(80,0.75f,true);
    private static long indexVersion=Long.MIN_VALUE;
    private static int indexCursor;
    private static long lastReportNanos;
    private static int cachedCellCount;
    private static ClientLevel levelOwner;
    private SchematicaWorldRenderer() {}

    private record SourceCell(BlockPos pos, BlockState expected) {}
    private static final class SourceSection {
        final List<SourceCell> cells=new ArrayList<>();
        final BitSet solidBlocks=new BitSet(4096);
        // Sparse local block lookup; never allocate a full 4096-cell array
        // per section just because one distant schematic block exists.
        final it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap<BlockState> expectedBlocks=
            new it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap<>();
    }
    private record DrawCell(BlockPos pos, BlockState expected, List<BakedQuad> quads) {}
    private static final class MeshSection {
        final List<DrawCell> cells=new ArrayList<>();
        int nextCell;
        int quadCount;
    }
    private record VisibleSection(long key, SourceSection source, double distanceSq) {}

    public static void clearModelCache() {
        MODEL_CACHE.clear();
        modelCacheOwner=null;
        INDEX.clear();
        MESH_CACHE.clear();
        cachedCellCount=0;
        indexCursor=0;
        indexVersion=Long.MIN_VALUE;
        lastReportNanos=0L;
    }

    private static int localIndex(BlockPos pos) {
        return (pos.getX()&15)|((pos.getY()&15)<<4)|((pos.getZ()&15)<<8);
    }
    /**
     * Read-only lookup for Easy Pick. Uses the SAME progressive spatial index
     * as the hologram; no million-cell linear scan on right-click. A source
     * section not yet indexed returns null rather than choosing a wrong item.
     */
    public static BlockState expectedAt(final BlockPos worldPos) {
        if (!SchematicaSession.loaded()) return null;
        if (indexVersion!=SchematicaSession.version()) {
            INDEX.clear();
            MESH_CACHE.clear();
            cachedCellCount=0;
            indexCursor=0;
            indexVersion=SchematicaSession.version();
        }
        indexSome();
        SourceSection source=INDEX.get(SectionPos.asLong(worldPos));
        return source == null ? null : source.expectedBlocks.get(localIndex(worldPos));
    }

    private static void indexSome() {
        final List<SchematicaSession.Cell> all=SchematicaSession.cells();
        final long start=System.nanoTime();
        int processed=0;
        while(indexCursor<all.size() && processed<INDEX_CELLS_PER_FRAME) {
            // Always process at least one cell, even on systems with a coarse clock.
            if (processed>0 && System.nanoTime()-start>INDEX_NANOS_PER_FRAME) break;
            SchematicaSession.Cell raw=all.get(indexCursor++);
            processed++;
            if (!SchematicaSession.displayLayer(raw)) continue;
            BlockPos world=SchematicaSession.positionOf(raw);
            BlockState expected=SchematicaSession.orientedState(raw);
            long key=SectionPos.asLong(world);
            SourceSection section=INDEX.computeIfAbsent(key,k->new SourceSection());
            section.cells.add(new SourceCell(world,expected));
            section.expectedBlocks.put(localIndex(world),expected);
            if (expected.isSolidRender()) section.solidBlocks.set(localIndex(world));
        }
    }

    private static List<BakedQuad> resolveQuads(BlockStateModelSet models, BlockState state) {
        BlockStateModel model=models.get(state);
        List<BlockStateModelPart> parts=new ArrayList<>();
        model.collectParts(RandomSource.create(0L),parts);
        List<BakedQuad> result=new ArrayList<>();
        for(BlockStateModelPart part:parts) {
            for(Direction direction:Direction.values()) result.addAll(part.getQuads(direction));
            result.addAll(part.getQuads(null));
        }
        return result;
    }

    private static List<BakedQuad> culledQuads(SourceSection source, SourceCell cell,
                                                 BlockStateModelSet models) {
        List<BakedQuad> all=MODEL_CACHE.computeIfAbsent(cell.expected(),s->resolveQuads(models,s));
        if (!cell.expected().isSolidRender() || all.isEmpty()) return all;
        List<BakedQuad> visible=null;
        for(BakedQuad quad:all) {
            Direction facing=quad.direction();
            boolean hidden=false;
            if (facing!=null && quad.isFullBlockBoundaryFace()) {
                BlockPos neighbor=cell.pos().relative(facing);
                if (SectionPos.asLong(neighbor)==SectionPos.asLong(cell.pos())) {
                    hidden=source.solidBlocks.get(localIndex(neighbor));
                }
            }
            if(hidden) {
                if(visible==null) {
                    visible=new ArrayList<>(all.size());
                    // Preserve all previously examined quads, excluding this hidden one.
                    for(BakedQuad prior:all) {
                        if(prior==quad) break;
                        visible.add(prior);
                    }
                }
            } else if(visible!=null) visible.add(quad);
        }
        return visible==null?all:visible;
    }

    private static MeshSection meshFor(VisibleSection ref) {
        MeshSection mesh=MESH_CACHE.get(ref.key());
        if(mesh==null) {
            mesh=new MeshSection();
            MESH_CACHE.put(ref.key(),mesh);
        }
        return mesh;
    }

    private static void buildVisible(List<VisibleSection> visible, BlockStateModelSet models) {
        final long start=System.nanoTime();
        int built=0;
        for (VisibleSection ref:visible) {
            if (built>=MESH_CELLS_PER_FRAME) break;
            if (built>0 && System.nanoTime()-start>MESH_NANOS_PER_FRAME) break;
            MeshSection mesh=meshFor(ref);
            List<SourceCell> cells=ref.source().cells;
            while(mesh.nextCell<cells.size() && built<MESH_CELLS_PER_FRAME) {
                if (built>0 && System.nanoTime()-start>MESH_NANOS_PER_FRAME) break;
                SourceCell c=cells.get(mesh.nextCell++);
                built++;
                List<BakedQuad> quads=culledQuads(ref.source(),c,models);
                if(quads.isEmpty()) continue;
                mesh.cells.add(new DrawCell(c.pos(),c.expected(),quads));
                mesh.quadCount+=quads.size();
                cachedCellCount++;
            }
        }
        // The index and the source blocks survive eviction. Only derived
        // render geometry is discarded, so moving back rebuilds it lazily.
        Iterator<Map.Entry<Long,MeshSection>> itr=MESH_CACHE.entrySet().iterator();
        while((MESH_CACHE.size()>CACHE_SECTION_LIMIT || cachedCellCount>CACHE_CELL_LIMIT)
                && itr.hasNext()) {
            MeshSection victim=itr.next().getValue();
            cachedCellCount-=victim.cells.size();
            itr.remove();
        }
    }

    private static List<VisibleSection> visibleSections(CameraRenderState camera,
                                                         ClientLevel level, int renderDistance) {
        List<VisibleSection> visible=new ArrayList<>();
        Vec3 pos=camera.pos;
        final int cx=(int)Math.floor(pos.x/16.0);
        final int cz=(int)Math.floor(pos.z/16.0);
        for(Map.Entry<Long,SourceSection> entry:INDEX.entrySet()) {
            long key=entry.getKey();
            int sx=SectionPos.x(key),sy=SectionPos.y(key),sz=SectionPos.z(key);
            // Vanilla-style horizontal chunk view distance, relative to the
            // detached Freecam if enabled. Never change server chunk tickets.
            if(Math.abs((long)sx-cx)>renderDistance || Math.abs((long)sz-cz)>renderDistance) continue;
            if(level.getChunkSource().getChunkNow(sx,sz)==null) continue;
            double x=(double)sx*16.0,y=(double)sy*16.0,z=(double)sz*16.0;
            if(!camera.cullFrustum.isVisible(new AABB(x,y,z,x+16.0,y+16.0,z+16.0))) continue;
            double dx=x+8.0-pos.x,dy=y+8.0-pos.y,dz=z+8.0-pos.z;
            visible.add(new VisibleSection(key,entry.getValue(),dx*dx+dy*dy+dz*dz));
        }
        visible.sort(Comparator.comparingDouble(VisibleSection::distanceSq));
        return visible;
    }

    public static void submit(SubmitNodeCollector submits, CameraRenderState camera,
                              BlockStateModelSet models) {
        if(!SchematicaSession.loaded() || !SchematicaSession.visible()) return;
        Minecraft mc=Minecraft.getInstance();
        ClientLevel level=mc.level;
        if(level==null) return;
        if(levelOwner!=level) {
            clearModelCache();
            levelOwner=level;
        }
        if(modelCacheOwner!=models) {
            clearModelCache();
            modelCacheOwner=models;
        }
        if(indexVersion!=SchematicaSession.version()) {
            INDEX.clear();
            MESH_CACHE.clear();
            cachedCellCount=0;
            indexCursor=0;
            indexVersion=SchematicaSession.version();
        }

        indexSome();
        final int renderDistance=Math.max(2,mc.options.getEffectiveRenderDistance());
        List<VisibleSection> visible=visibleSections(camera,level,renderDistance);
        buildVisible(visible,models);
        final Vec3 cameraPos=camera.pos;
        final int alpha=Math.round(SchematicaSession.opacity()*255.0f);
        final int alertAlpha=Math.max(150,Math.min(235,alpha+70));
        final int colorMissing=ARGB.color(alpha,180,245,255);
        final int colorWrong=ARGB.color(alertAlpha,255,60,60);
        final int colorRotation=ARGB.color(alertAlpha,255,165,45);
        int quadsSubmitted=0,sectionsDrawn=0,cellsConsidered=0;
        for(VisibleSection ref:visible) {
            MeshSection mesh=MESH_CACHE.get(ref.key());
            if(mesh==null || mesh.cells.isEmpty()) continue;
            if(quadsSubmitted+mesh.quadCount>FRAME_QUAD_LIMIT) continue;
            quadsSubmitted+=mesh.quadCount;
            sectionsDrawn++;
            cellsConsidered+=mesh.cells.size();
            // Only already-loaded client world chunks are compared. Existing
            // hologram semantics (correct blocks hidden, wrong blocks red)
            // are evaluated live, without modifying world data.
            submits.submitCustomGeometry(new PoseStack(),
                RenderTypes.pletzelHologram(TextureAtlas.LOCATION_BLOCKS),
                (pose,buffer)-> {
                    QuadInstance instance=new QuadInstance();
                    instance.setLightCoords(0x00f000f0);
                    instance.setOverlayCoords(OverlayTexture.NO_OVERLAY);
                    PoseStack blockPose=new PoseStack();
                    for(DrawCell cell:mesh.cells) {
                        if(!level.hasChunkAt(cell.pos())) continue;
                        BlockState actual=level.getBlockState(cell.pos());
                        if(actual.equals(cell.expected())) continue;
                        boolean missing=actual.isAir();
                        instance.setColor(missing?colorMissing:
                            actual.getBlock()==cell.expected().getBlock()?colorRotation:colorWrong);
                        blockPose.pushPose();
                        blockPose.translate(cell.pos().getX()-cameraPos.x,
                                            cell.pos().getY()-cameraPos.y,
                                            cell.pos().getZ()-cameraPos.z);
                        if(!missing) {
                            blockPose.translate(.5,.5,.5);
                            blockPose.scale(1.006f,1.006f,1.006f);
                            blockPose.translate(-.5,-.5,-.5);
                        }
                        for(BakedQuad quad:cell.quads()) buffer.putBakedQuad(blockPose.last(),quad,instance);
                        blockPose.popPose();
                    }
                });
        }
        long now=System.nanoTime();
        if(now-lastReportNanos>REPORT_INTERVAL_NANOS) {
            lastReportNanos=now;
            System.out.println("[PletzelSchematicPerf] cellsIndexed="+indexCursor+
                " cellsTotal="+SchematicaSession.cells().size()+
                " sourceSections="+INDEX.size()+
                " visibleSections="+visible.size()+
                " drawnSections="+sectionsDrawn+
                " cachedSections="+MESH_CACHE.size()+
                " cachedCells="+cachedCellCount+
                " consideredCells="+cellsConsidered+
                " submittedQuads="+quadsSubmitted+
                " renderDistance="+renderDistance);
        }
    }
}

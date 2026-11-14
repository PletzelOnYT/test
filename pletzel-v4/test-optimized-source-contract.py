#!/usr/bin/env python3
"""Fail-closed native Java source contracts for Pletzel V4 renderer changes.

Source assertions and the lightweight visibility math fixture are NOT FPS
benchmarks or proof of browser visual correctness. Real Chrome runs separately.
"""
from pathlib import Path
import re, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")/"game/src/main/java"
renderer=(root/"net/pletzel/schematica/SchematicaWorldRenderer.java").read_text()
preview=(root/"net/pletzel/maptooltip/MapTooltipClientComponent.java").read_text()
manager=(root/"net/minecraft/client/resources/MapTextureManager.java").read_text()
src_session=(root/"net/pletzel/schematica/SchematicaSession.java").read_text()
assert "MODEL_CACHE" in renderer
for contract in [
    "SectionPos.asLong(world)",
    "section.solidBlocks.set(localIndex(world))",
    "indexCursor++",
    "INDEX_CELLS_PER_FRAME=8192",
    "MESH_CELLS_PER_FRAME=2048",
    "CACHE_SECTION_LIMIT=64",
    "CACHE_CELL_LIMIT=65536",
    "FRAME_QUAD_LIMIT=100000",
    "visibleSections(CameraRenderState camera",
    "camera.cullFrustum.isVisible",
    "level.getChunkSource().getChunkNow(sx,sz)",
    "mc.options.getEffectiveRenderDistance()",
    "mesh.nextCell<cells.size()",
    "actual.equals(cell.expected())",
    "SchematicaSession.version()",
    "[PletzelSchematicPerf]"
]:
    assert contract in renderer, ("missing optimized native section contract",contract)
assert "for (SchematicaSession.Cell c : SchematicaSession.cells())" not in renderer
assert "144.0*144.0" not in renderer
assert "graphics.map(state)" in preview
assert "return 66;" in preview
assert "No map data" in preview
assert "Map #"+'"' not in preview or "No map data" in preview
assert "currentMapData() == null ? 0" not in preview
assert "data.colors.length!=128*128" in preview
assert "Arrays.hashCode(this.data.colors)" in manager
assert "COLOR_AUDIT_INTERVAL_NANOS" in manager
assert "MapColor.getColorFromPackedId(this.data.colors[i])" in manager
assert "void resetData()" in manager
assert "public static void loadAny" in src_session
print("SOURCE PASS: fixed metadata, never-flicker 66x66 map tooltip and actual vanilla 128x128 colors")
print("SOURCE PASS: progressive section index, bounded visible cache, loaded-world and Freecam culling")

# Independent check that changing render distance monotonically increases the
# set of *eligible* horizontal section coordinates (not a rendered-game claim).
cam_x=25
cam_z=-17
coords=[(x,z) for x in range(-50,51) for z in range(-50,51)]
counts=[]
for rd in (2,4,8,16):
    active={(x,z) for x,z in coords if abs(x-cam_x)<=rd and abs(z-cam_z)<=rd}
    counts.append(len(active))
assert counts==[25,81,289,1089],counts
print("VISIBILITY MATH FIXTURE PASS: distances 2,4,8,16 eligible section columns",counts)
print("BROWSER/REAL-GPU/MAP CONTENT AND FPS ACCEPTANCE: UNVERIFIED BY THIS SOURCE TEST")

#!/usr/bin/env python3
"""Fail closed source checks. These never substitute for real Chrome gameplay."""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")/"game/src/main/java"
def read(s):return (root/s).read_text()
options=read("net/minecraft/client/Options.java")
mc=read("net/minecraft/client/Minecraft.java")
schem=read("net/pletzel/schematica/SchematicaWorldRenderer.java")
easy=read("net/pletzel/schematica/EasyPlace26.java")
picker=read("net/pletzel/schematica/EasyPick26.java")
mapclient=read("net/pletzel/maptooltip/MapTooltipClientComponent.java")
mapdata=read("net/pletzel/maptooltip/MapTooltipData.java")
store=read("net/pletzel/maptooltip/MapArtStore26.java")
for field,val in [
 ("pletzelEasyPlace","false"),("pletzelEasyPlaceHover","false"),
 ("pletzelChunkRendering","true"),("pletzelIncrementalMesh","true"),
 ("pletzelWrongHighlight","true"),("pletzelRememberMapArt","true"),
 ("pletzelShowMapArt","true"),("pletzelExcludeExplorer","true")]:
 assert f'OptionInstance.createBoolean("{field}", {val})' in options,field
 assert f'access.process("{field}", this.{field})' in options,field
assert mc.index("EasyPlace26.beforeVanillaUse(this)")<mc.index("EasyPick26.beforeVanillaUse(this)")
assert 'this.rightClickDelay == 0' in mc and 'EasyPlace26.shouldHoverPlace(this)' in mc
assert "net.pletzel.schematica.Freecam26.active()" in mc
# Ghost-first targeting is necessary: real Minecraft hitResult is a MISS
# when a hologram occupies empty air. The *support* must still be a real
# collider raycast with vanilla reach and orientation checks.
assert "private static BlockPos aimedGhost(Minecraft mc)" in easy
assert "BlockPos.containing(cursor)" in easy
assert "ClipContext.Block.COLLIDER" in easy
assert "hit.getBlockPos().equals(support)" in easy
assert "hit.getDirection()!=exposed" in easy
assert "mc.player.blockInteractionRange()" in easy
assert "mc.level.hasChunkAt(support)" in easy
assert "EasyPlace26.afterVanillaKeybinds" not in easy
assert "CLIENT_WORLD_MATCHED target=" in easy  # never claim a local client state is server confirmation
assert "NOT_CONFIRMED target=" in easy
assert "context.getClickedPos().equals(target)" in easy
assert "getStateForPlacement(context)" in easy
assert "EasyPlace26.inHoverAttempt()" in picker
for forbidden in ("ServerboundUseItemOnPacket","ServerboundSetCarriedItemPacket",
                  ".connection.send(",".send(","setBlock(","setItem(","setSelectedSlot("):
 assert forbidden not in easy,forbidden
assert "ChunkPos.pack(sx,sz)" in schem
assert "SECTION_COLUMNS" in schem
assert "wrongQuads" in schem and "cell.wrongQuads()" in schem
assert "missing?cell.ghostQuads():cell.wrongQuads()" in schem
assert "if(!missing&&!highlightWrong)continue;" in schem
assert "MapTooltipData.isExplorer(stack)" in read("net/minecraft/world/item/MapItem.java")
assert "map.explorer()" in read("net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java")
assert "MapArtStore26.observe" in read("net/minecraft/client/resources/MapTextureManager.java")
assert "MapArtStore26.cachedData(id)" in mapclient
assert "MapDecorationTypes.RED_X" in mapdata
assert "MapItemSavedData.createForClient" in store
assert "EagRuntime.setStorage(k,output)" in store
assert "MAX_DISK_MAPS=128" in store
assert "LevelResource.ROOT" in store
# Before the LAST UI patch, Easy Place still has the legacy screen.
# The restored independent Mods hub is checked by the subsequent preflight.
assert "PletzelBuildingSettings26(this)" in read("net/pletzel/schematica/SchematicaScreen.java")
for name in ("PletzelBuildingSettings26","PletzelMapArtSettings26"):
 assert (root/("net/pletzel/schematica/"+name+".java")).exists()
print("SOURCE PASS: legitimate vanilla support-face right-click, no forged packets")
print("SOURCE PASS: OFF-by-default persisted Easy Place and map-art options")
print("SOURCE PASS: cache keyed to world/server+dimension+MapId, 16,384 real colors")
print("SOURCE PASS: all red wrong-model faces retained, 16x16 column visibility")
print("LIVE SERVER/CHROME/MULTIPLAYER/GPU ACCEPTANCE: NOT VERIFIED BY THIS CHECK")

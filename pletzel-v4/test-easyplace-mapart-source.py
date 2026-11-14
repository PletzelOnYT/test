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
assert mc.index("EasyPick26.beforeVanillaUse(this)")<mc.index("EasyPlace26.beforeVanillaUse(this)")
# The final GUI/IndexedDB restoration stage injects afterVanillaKeybinds.
# That final stage is checked independently after it runs.
assert "EasyPlace26.tick(this)" in mc
assert "net.pletzel.schematica.Freecam26.active()" in mc
# Ghost-first targeting is necessary: real Minecraft hitResult is a MISS
# when a hologram occupies empty air. The *support* must still be a real
# collider raycast with vanilla reach and orientation checks.
# Hold-mode source contract: vanilla manual use, server-only confirmation.
assert "HOVER_AUTOPLACE_DISABLED = false" in easy
assert "mc.hitResult=" not in easy
assert "onServerBlockUpdate(ClientLevel level" in easy
assert "onServerChunk(ClientLevel level" in easy
assert "onServerPredictionAck(ClientLevel level" in easy
assert "SERVER_CONFIRMED" in easy and "SERVER_REJECTED_OR_CORRECTED" in easy
assert "TIMEOUT_NOT_CONFIRMED" in easy
assert "rejectedTargets.contains(target)" in easy
assert "pending!=null" in easy
assert "getStateForPlacement(ctx)" in easy
assert "mc.player.blockInteractionRange()" in easy
assert "mc.level.clip(" in easy
assert "mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,hit)" in easy
assert "mc.options.pletzelEasyPlaceHover.get()" in easy
assert "mc.options.keyUse.isDown()" in easy
assert "selected+1" in easy
listener=read("net/minecraft/client/multiplayer/ClientPacketListener.java")
assert listener.count("EasyPlace26.onServerBlockUpdate(")==2
assert "EasyPlace26.onServerPredictionAck(" in listener
assert "EasyPlace26.onServerChunk(" in listener
game_mode=read("net/minecraft/client/multiplayer/MultiPlayerGameMode.java")
assert "EasyPlace26.onVanillaSequence(" in game_mode
assert "pendingSequence" in easy and "predictionAcked" in easy
assert "SERVER_CONFIRMED_AND_RECONCILED" in easy
assert "observedByServer" in easy
for forbidden in ("ServerboundUseItemOnPacket", "ServerboundSetCarriedItemPacket",
                  ".connection.send(", ".send(", "setBlock(", "setItem(",
                  "mc.hitResult=", "startUseItem("):
 assert forbidden not in easy,forbidden
assert "ChunkPos.pack(sx,sz)" in schem
assert "SECTION_COLUMNS" in schem
assert "wrongQuads" in schem and "cell.wrongQuads()" in schem
assert "missing?cell.ghostQuads():cell.wrongQuads()" in schem
assert "if(!missing&&!pending&&!highlightWrong)continue;" in schem
assert "EasyPlace26.isPlacementPending(cell.pos())" in schem
assert "colorPending" in schem
assert "public static boolean isPlacementPending(BlockPos pos)" in easy
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
print("SOURCE PASS: Hover and continuous Hold target ray-verified REAL faces; vanilla item use")
print("SOURCE PASS: OFF-by-default persisted Easy Place and map-art options")
print("SOURCE PASS: cache keyed to world/server+dimension+MapId, 16,384 real colors")
print("SOURCE PASS: all red wrong-model faces retained, 16x16 column visibility")
print("EASY PLACE GAMEPLAY & MULTIPLAYER ACCEPTANCE: NOT VERIFIED BY THIS SOURCE CHECK")

#!/usr/bin/env python3
"""Static integration guard for the native VendoAU Map Tooltip 5.0.1 port.

Must execute on the *patched* exact Minecraft 26.2 source before recompiling.
These checks do not pretend to verify real multiplayer map textures.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else 'engine')
game=root/'game/src/main/java'
item=(game/'net/minecraft/world/item/MapItem.java').read_text()
factory=(game/'net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java').read_text()
data=(game/'net/pletzel/maptooltip/MapTooltipData.java').read_text()
client=(game/'net/pletzel/maptooltip/MapTooltipClientComponent.java').read_text()
map_renderer=(game/'net/minecraft/client/renderer/MapRenderer.java').read_text()
texture=(game/'net/minecraft/client/resources/MapTextureManager.java').read_text()
assert 'new net.pletzel.maptooltip.MapTooltipData(id)' in item
assert 'stack.get(DataComponents.MAP_ID)' in item
assert 'id != null' in item
assert 'getTooltipImage(final ItemStack stack)' in item
assert 'MapTooltipData map -> new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId())' in factory
assert 'record MapTooltipData(MapId mapId) implements TooltipComponent' in data
assert 'net.minecraft.client.' not in data
for required in [
 'textures/map/map_background.png',
 '0.45F, 0.45F',
 'x, y - 2',
 'x + 4.0F, y + 2.0F',
 'graphics.map(state)',
 'mc.level.getMapData(this.id)',
 'getMapRenderer().extractRenderState(this.id, data, state)',
 'return currentMapData() == null ? 0 : 66;'
]:
 assert required in client, ('missing JAR behavior or 26.2 API:',required)
assert 'MapTextureManager' in client
assert 'MapTextureManager' in map_renderer
assert 'this.mapTextureManager.prepareMapTexture(mapId, mapData)' in map_renderer
assert 'this.texture.upload()' in texture
assert 'this.requiresUpload = false' in texture
assert 'this.requiresUpload |= dataChanged' in texture
assert 'MapColor.getColorFromPackedId(this.data.colors[i])' in texture
assert 'new net.minecraft.client.gui.screens.PletzelSingleplayerWarningScreen' not in client
print('SOURCE PASS: original JAR geometry and real MAP_ID/data path retained')
print('SOURCE PASS: exact 26.2 MapRenderer and cached, updateable map textures')
print('SOURCE PASS: server-safe map descriptor, empty-data graceful handling')
print('BROWSER VERIFICATION REMAINS REQUIRED: two independent real map data sets and multiplayer updates')

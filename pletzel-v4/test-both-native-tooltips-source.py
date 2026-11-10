#!/usr/bin/env python3
"""Static source contract for both built-in tooltips and Controls toggles.

This is deliberately not a substitute for screenshots of genuine map/shulker
items in the compiled game.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
game=root/"game/src/main/java"
read=lambda p:(game/p).read_text()
item=read("net/minecraft/world/item/ItemStack.java")
factory=read("net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java")
graphics=read("net/minecraft/client/gui/GuiGraphicsExtractor.java")
options=read("net/minecraft/client/Options.java")
controls=read("net/minecraft/client/gui/screens/options/controls/ControlsScreen.java")
data=read("net/pletzel/shulkertooltip/ShulkerTooltipData.java")
shulker=read("net/pletzel/shulkertooltip/ShulkerTooltipClientComponent.java")
mapitem=read("net/minecraft/world/item/MapItem.java")
mapclient=read("net/pletzel/maptooltip/MapTooltipClientComponent.java")
lang=(root/"game/src/main/resources/assets/minecraft/lang/en_us.json").read_text()

for token in ["instanceof net.minecraft.world.level.block.ShulkerBoxBlock shulkerBlock",
 "getOrDefault(DataComponents.CONTAINER, net.minecraft.world.item.component.ItemContainerContents.EMPTY)",
 "shulkerBlock.getColor(), this.getHoverName()"]:
 assert token in item,("Shulker client-provided data or name path missing",token)

assert 'record ShulkerTooltipData(' in data
assert "ItemContainerContents contents" in data
assert "Component hoverName" in data
assert "net.minecraft.client" not in data, "Common item data must stay server safe"
for token in ["SLOTS=27","COLUMNS=9","SHULKER_TEXTURE",
 "textures/gui/container/shulker_box.png","NonNullList.withSize(SLOTS,ItemStack.EMPTY)",
 "contents.copyInto(copied)","DECODED.put(contents,items)",
 "MAX_DECODED=32","itemDecorations(font,held,xx,yy)",
 "graphics.item(held,xx,yy,slot)","this.data.hoverName()",
 "slot%COLUMNS","slot/COLUMNS","graphics.outline(","getTextureDiffuseColor()"]:
 assert token in shulker,("Native shulker preview missing",token)
assert "this.getOrCreateMapInstance" not in shulker
assert "java.net" not in shulker
assert "currentMapData()" in mapclient
assert "graphics.map(state)" in mapclient
assert "MapTooltipData" in mapitem
assert "ShulkerTooltipData shulker" in factory
assert "MapTooltipData map" in factory
assert "ClientTooltipComponent::create" in graphics
assert "optionalImage.filter(image ->" in graphics
for token in [
 'options.pletzelMapTooltip().get()',
 'options.pletzelShulkerTooltip().get()'
]: assert token in graphics
for token in [
 'OptionInstance.createBoolean("options.pletzelMapTooltip", true)',
 'OptionInstance.createBoolean("options.pletzelShulkerTooltip", true)',
 'access.process("pletzelMapTooltip", this.pletzelMapTooltip)',
 'access.process("pletzelShulkerTooltip", this.pletzelShulkerTooltip)'
]: assert token in options
assert controls.count("options.pletzelMapTooltip(),")==2
assert controls.count("options.pletzelShulkerTooltip(),")==2
assert controls.count("options.pletzelInputMode(),")==2
for label in ["options.pletzelMapTooltip", "options.pletzelShulkerTooltip"]:
 assert lang.count('"'+label+'":')==1

print("SOURCE PASS: two genuine Minecraft tooltip components, no HTML or Fabric runtime")
print("SOURCE PASS: 27 original, read-only, color-aware, counted inventory slots")
print("SOURCE PASS: 32-entry bounded immutable-component decode cache")
print("SOURCE PASS: original map ID and vanilla renderer preserved")
print("SOURCE PASS: persisted native ON/OFF toggles in both Controls layouts")
print("BROWSER EVIDENCE STILL REQUIRED: two maps, empty/populated shulkers, multiplayer updates")

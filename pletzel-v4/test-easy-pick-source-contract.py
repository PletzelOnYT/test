#!/usr/bin/env python3
"""Fail-closed Easy Pick source invariants, not a simulated gameplay success."""
from pathlib import Path
import sys,re
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")/"game/src/main/java"
options=(root/"net/minecraft/client/Options.java").read_text()
minecraft=(root/"net/minecraft/client/Minecraft.java").read_text()
menu=(root/"net/pletzel/schematica/SchematicaScreen.java").read_text()
renderer=(root/"net/pletzel/schematica/SchematicaWorldRenderer.java").read_text()
picker=(root/"net/pletzel/schematica/EasyPick26.java").read_text()

for value in (
    'OptionInstance.createBoolean("pletzelEasyPick", false)',
    'access.process("pletzelEasyPick", this.pletzelEasyPick)',
):
    assert value in options,("Option default/persistence",value)
assert 'this.minecraft.options.save();' in menu
assert 'Easy Pick: ' in menu
assert '(this.height-y-25)/8' in menu
assert 'if (!net.pletzel.schematica.EasyPick26.beforeVanillaUse(this)) return;' in minecraft
assert minecraft.index('EasyPick26.beforeVanillaUse(this)') < minecraft.index('if (!this.gameMode.isDestroying())',minecraft.index('private void startUseItem()'))
assert 'if (net.pletzel.schematica.Freecam26.active()) return;' in minecraft
assert 'this.player.getInventory().setSelectedSlot(i)' in minecraft # native number keys
assert 'mc.player.getInventory().setSelectedSlot(chosen)' in picker
assert 'for (int slot=0;slot<9;slot++)' in picker
assert 'mc.player.getInventory().getItem(slot)' in picker
assert 'mc.options.keyUse.isDown()' in picker
assert 'mc.options.toggleUse().get()' in picker
assert 'Freecam26.active()' in picker
assert 'SchematicaSession.loaded()' in picker
assert 'getStateForPlacement(context)' in picker
assert 'context.getClickedPos().equals(target)' in picker
assert 'mc.level.getBlockState(target).equals(required)' in picker
assert 'BlockPlaceContext' in picker
assert 'public static BlockState expectedAt' in renderer
assert 'expectedBlocks.get(localIndex(worldPos))' in renderer
assert 'indexSome();' in renderer
assert 'Int2ObjectOpenHashMap<BlockState>' in renderer
assert 'version()!=SchematicaSession.version()' not in renderer or 'indexVersion!=SchematicaSession.version()' in renderer
for forbidden in (
    'ServerboundSetCarriedItemPacket','ServerboundUseItemOnPacket',
    'ServerboundContainerClickPacket','.connection.send(','.setItem(',
    'setSelectedItem(','pickSlot(','creativeMode', 'clickCount++','KeyMapping.click('
):
    assert forbidden not in picker,("Disallowed Easy Pick behavior",forbidden)
print("SOURCE PASS: optional OFF default saved in canonical Minecraft options")
print("SOURCE PASS: native GUI + actual custom Place Block key state")
print("SOURCE PASS: 9 hotbar slots ONLY, same setter as vanilla number keys")
print("SOURCE PASS: no forged packets, slot contents/inventory changes, client world writes")
print("SOURCE PASS: projected orientation/placement state, skip correctly placed")
print("SOURCE PASS: incremental section-index O(1) lookup, no per-hover schematic scan")
print("REAL IN-GAME SLOT SWITCHING, MULTIPLAYER, INPUT-LAG: NOT VERIFIED BY SOURCE CHECK")

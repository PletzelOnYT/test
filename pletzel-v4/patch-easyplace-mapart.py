#!/usr/bin/env python3
"""Fail-closed integration of new Easy Place, full red overlays and map-art cache.

Run AFTER native Schematica, map tooltip, Freecam, optimized renderer, and the
existing Easy Pick patch have all been applied.
"""
from pathlib import Path
import re,sys,shutil

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
java=root/"game/src/main/java"
here=Path(__file__).parent

def swap(path,old,new):
    p=java/path
    src=p.read_text()
    n=src.count(old)
    if n!=1:raise RuntimeError(f"unexpected native Java patch anchor {path}: {n} occurrences of {old[:110]!r}")
    p.write_text(src.replace(old,new,1))
    print("PLETZEL_NEXT_PATCHED",path)

opts="net/minecraft/client/Options.java"
decl='''   public final OptionInstance<Boolean> pletzelEasyPick =
      OptionInstance.createBoolean("pletzelEasyPick", false);'''
extra='''   public final OptionInstance<Boolean> pletzelEasyPick =
      OptionInstance.createBoolean("pletzelEasyPick", false);
   public final OptionInstance<Boolean> pletzelEasyPlace =
      OptionInstance.createBoolean("pletzelEasyPlace", false);
   public final OptionInstance<Boolean> pletzelEasyPlaceHover =
      OptionInstance.createBoolean("pletzelEasyPlaceHover", false);
   public final OptionInstance<Boolean> pletzelChunkRendering =
      OptionInstance.createBoolean("pletzelChunkRendering", true);
   public final OptionInstance<Boolean> pletzelIncrementalMesh =
      OptionInstance.createBoolean("pletzelIncrementalMesh", true);
   public final OptionInstance<Boolean> pletzelWrongHighlight =
      OptionInstance.createBoolean("pletzelWrongHighlight", true);
   public final OptionInstance<Boolean> pletzelRememberMapArt =
      OptionInstance.createBoolean("pletzelRememberMapArt", true);
   public final OptionInstance<Boolean> pletzelShowMapArt =
      OptionInstance.createBoolean("pletzelShowMapArt", true);
   public final OptionInstance<Boolean> pletzelExcludeExplorer =
      OptionInstance.createBoolean("pletzelExcludeExplorer", true);'''
swap(opts,decl,extra)
swap(opts,
'''      access.process("pletzelEasyPick", this.pletzelEasyPick);''',
'''      access.process("pletzelEasyPick", this.pletzelEasyPick);
      access.process("pletzelEasyPlace", this.pletzelEasyPlace);
      access.process("pletzelEasyPlaceHover", this.pletzelEasyPlaceHover);
      access.process("pletzelChunkRendering", this.pletzelChunkRendering);
      access.process("pletzelIncrementalMesh", this.pletzelIncrementalMesh);
      access.process("pletzelWrongHighlight", this.pletzelWrongHighlight);
      access.process("pletzelRememberMapArt", this.pletzelRememberMapArt);
      access.process("pletzelShowMapArt", this.pletzelShowMapArt);
      access.process("pletzelExcludeExplorer", this.pletzelExcludeExplorer);''')

swap("net/minecraft/client/Minecraft.java",
'''      if (!net.pletzel.schematica.EasyPick26.beforeVanillaUse(this)) return;''',
'''      // Vanilla key-hold selection first; Easy Place then verifies the
      // actual selected item and untouched crosshair before normal use.
      if (!net.pletzel.schematica.EasyPick26.beforeVanillaUse(this)) return;
      if (!net.pletzel.schematica.EasyPlace26.beforeVanillaUse(this)) return;''')
swap("net/minecraft/client/Minecraft.java",
'''      if (this.options.keyUse.isDown() && this.rightClickDelay == 0 && !this.player.isUsingItem()) {
         this.startUseItem();
      }''',
'''      if (this.options.keyUse.isDown() && this.rightClickDelay == 0 && !this.player.isUsingItem()) {
         // Actual user input only: Hover Auto-Place is prohibited.
         this.startUseItem();
      }''')

# Independent Easy Pick remains unmodified: physical right-click only.
screen=java/"net/pletzel/schematica/SchematicaScreen.java"
s=screen.read_text()
pattern=r'        this\.addRenderableWidget\(Button\.builder\(\s*Component\.literal\("Easy Pick: "[\s\S]*?\}\)\.bounds\(left,y,150,20\)\.build\(\)\);'
replacement='''        add(left,y,"Building / Easy Place",()->this.minecraft.gui.setScreen(
            new PletzelBuildingSettings26(this)));'''
s,n=re.subn(pattern,replacement,s,count=1)
if n!=1:raise RuntimeError(f"Easy Pick legacy main-screen button does not match: {n}")
screen.write_text(s)

# These common-side classes remain server-safe: descriptor uses ItemStack
# metadata, not the client GUI or storage implementation.
swap("net/minecraft/world/item/MapItem.java",
'''new net.pletzel.maptooltip.MapTooltipData(id)''',
'''new net.pletzel.maptooltip.MapTooltipData(id,
            net.pletzel.maptooltip.MapTooltipData.isExplorer(stack))''')
swap("net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java",
'''new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId())''',
'''new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId(),map.explorer())''')
swap("net/minecraft/client/resources/MapTextureManager.java",
'''   public void update(final MapId id, final MapItemSavedData data) {
      this.getOrCreateMapInstance(id, data).forceUpload();''',
'''   public void update(final MapId id, final MapItemSavedData data) {
      net.pletzel.maptooltip.MapArtStore26.observe(id,data);
      this.getOrCreateMapInstance(id, data).forceUpload();''')
swap("net/minecraft/client/resources/MapTextureManager.java",
'''   public Identifier prepareMapTexture(final MapId id, final MapItemSavedData data) {
      MapTextureManager.MapInstance mapInstance = this.getOrCreateMapInstance(id, data);''',
'''   public Identifier prepareMapTexture(final MapId id, final MapItemSavedData data) {
      net.pletzel.maptooltip.MapArtStore26.observe(id,data);
      MapTextureManager.MapInstance mapInstance = this.getOrCreateMapInstance(id, data);''')

for original,dest in (
    ("EasyPlace26.java","net/pletzel/schematica/EasyPlace26.java"),
    ("PletzelBuildingSettings26.java","net/pletzel/schematica/PletzelBuildingSettings26.java"),
    ("PletzelMapArtSettings26.java","net/pletzel/schematica/PletzelMapArtSettings26.java"),
    ("MapArtStore26.java","net/pletzel/maptooltip/MapArtStore26.java"),
    ("MapTooltipData26.java","net/pletzel/maptooltip/MapTooltipData.java"),
    ("MapTooltipClientPersistent26.java","net/pletzel/maptooltip/MapTooltipClientComponent.java"),
):
    source=here/original
    target=java/dest
    if not source.is_file() or not target.parent.is_dir():
        raise RuntimeError("Missing exact source/target path "+str(target))
    shutil.copyfile(source,target)
    print("PLETZEL_NEXT_INSTALLED",dest)

# Record the sequence allocated by the ORIGINAL vanilla game mode.
# We never create packets: the original useItemOn still controls item use,
# selected slot synchronization, prediction and packet construction.
swap("net/minecraft/client/multiplayer/MultiPlayerGameMode.java",
'''         return new ServerboundUseItemOnPacket(hand, blockHit, sequence);''',
'''         net.pletzel.schematica.EasyPlace26.onVanillaSequence(
            this.minecraft, sequence, hand, blockHit);
         return new ServerboundUseItemOnPacket(hand, blockHit, sequence);''')

# Server-authoritative callbacks (read only). The original vanilla item-use
# sequence assignment and client prediction reconciliation remain unmodified.
listener="net/minecraft/client/multiplayer/ClientPacketListener.java"
swap(listener,
'''      packet.runUpdates((pos, state) -> this.level.setServerVerifiedBlockState(pos, state, 19));''',
'''      packet.runUpdates((pos, state) -> {
         this.level.setServerVerifiedBlockState(pos, state, 19);
         net.pletzel.schematica.EasyPlace26.onServerBlockUpdate(this.level, pos, state);
      });''')
swap(listener,
'''      this.level.setServerVerifiedBlockState(packet.getPos(), packet.getBlockState(), 19);''',
'''      this.level.setServerVerifiedBlockState(packet.getPos(), packet.getBlockState(), 19);
      net.pletzel.schematica.EasyPlace26.onServerBlockUpdate(
         this.level, packet.getPos(), packet.getBlockState());''')
swap(listener,
'''      this.level.handleBlockChangedAck(packet.sequence());''',
'''      this.level.handleBlockChangedAck(packet.sequence());
      net.pletzel.schematica.EasyPlace26.onServerPredictionAck(this.level, packet.sequence());''')
swap(listener,
'''      this.updateLevelChunk(x, z, packet.getChunkData());''',
'''      this.updateLevelChunk(x, z, packet.getChunkData());
      net.pletzel.schematica.EasyPlace26.onServerChunk(this.level, x, z);''')
swap("net/minecraft/client/Minecraft.java",
'''         this.handleKeybinds();
         if (this.missTime > 0) {''',
'''         this.handleKeybinds();
         net.pletzel.schematica.EasyPlace26.afterVanillaKeybinds(this);
         if (this.missTime > 0) {''')
swap("net/minecraft/client/Minecraft.java",
'''      this.gui.tick();
      if (this.gui.screen() != null) {''',
'''      this.gui.tick();
      // Clear Easy Place pending state even if a GUI captures key input.
      net.pletzel.schematica.EasyPlace26.tick(this);
      if (this.gui.screen() != null) {''')

assert 'new PletzelBuildingSettings26(this)' in screen.read_text()
print("PLETZEL_NEXT_NATIVE_SOURCE_PATCH_COMPLETE")

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
'''      // A ghost does NOT authorize a fake hit. Easy Place rejects any target
      // without a reachable real support face from the vanilla crosshair.
      if (!net.pletzel.schematica.EasyPlace26.beforeVanillaUse(this)) return;
      if (!net.pletzel.schematica.EasyPick26.beforeVanillaUse(this)) return;''')
swap("net/minecraft/client/Minecraft.java",
'''      if (this.options.keyUse.isDown() && this.rightClickDelay == 0 && !this.player.isUsingItem()) {
         this.startUseItem();
      }''',
'''      if (this.options.keyUse.isDown() && this.rightClickDelay == 0 && !this.player.isUsingItem()) {
         this.startUseItem();
      }
      // Optional hover mode triggers the *normal* vanilla right-click method
      // once per valid new ghost target. The built-in four-tick delay applies.
      if (this.rightClickDelay == 0 && !this.player.isUsingItem()
          && net.pletzel.schematica.EasyPlace26.shouldHoverPlace(this)) {
         this.startUseItem();
      }''')

swap("net/pletzel/schematica/EasyPick26.java",
'''if (!mc.options.keyUse.isDown() || mc.options.toggleUse().get()) return true;''',
'''if ((!mc.options.keyUse.isDown() &&
             !EasyPlace26.inHoverAttempt()) || mc.options.toggleUse().get()) return true;''')
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

assert 'new PletzelBuildingSettings26(this)' in screen.read_text()
print("PLETZEL_NEXT_NATIVE_SOURCE_PATCH_COMPLETE")

#!/usr/bin/env python3
"""Attach legitimate Litematica Easy Pick to exact Minecraft 26.2 APIs.

Runs after native map, full 4-format Schematica, Freecam and optimized hologram
patches. Every source replacement is fail-closed: a changed upstream API must
cause build failure, not a silent success.
"""
from pathlib import Path
import shutil, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
base=root/"game/src/main/java"

def replace(rel, old, new):
    p=base/rel
    text=p.read_text()
    count=text.count(old)
    assert count==1, (rel,"anchor not unique",count,old[:120])
    p.write_text(text.replace(old,new,1))
    print("EASY_PICK_PATCHED",rel,len(text),"->",len(text)-len(old)+len(new))

# Options is already saved to options.txt AND the Eaglercraft profile "g".
# Register this as a real OptionInstance, not independent localStorage hacks.
replace("net/minecraft/client/Options.java",
    '   private final OptionInstance<Boolean> showPerformanceCounters = OptionInstance.createBoolean("options.eaglerPerformanceCounters", true);',
    '''   private final OptionInstance<Boolean> showPerformanceCounters = OptionInstance.createBoolean("options.eaglerPerformanceCounters", true);
   // Client-local opt-in, persisted through native Options processing.
   public final OptionInstance<Boolean> pletzelEasyPick =
      OptionInstance.createBoolean("pletzelEasyPick", false);''')
replace("net/minecraft/client/Options.java",
    '      access.process("eaglerPerformanceCounters", this.showPerformanceCounters);',
    '''      access.process("eaglerPerformanceCounters", this.showPerformanceCounters);
      access.process("pletzelEasyPick", this.pletzelEasyPick);''')

# Called immediately before the vanilla startUseItem implementation, so the
# normal placement cooldowns, game mode validation, and inventory slot sync
# remain untouched.
replace("net/minecraft/client/Minecraft.java",
    '''private void startUseItem() {
      if (net.pletzel.schematica.Freecam26.active()) return;''',
    '''private void startUseItem() {
      if (net.pletzel.schematica.Freecam26.active()) return;
      if (!net.pletzel.schematica.EasyPick26.beforeVanillaUse(this)) return;''')

screen="net/pletzel/schematica/SchematicaScreen.java"
replace(screen,
    'int rowPitch=Math.max(20, Math.min(24, (this.height-y-25)/7));',
    'int rowPitch=Math.max(20, Math.min(24, (this.height-y-25)/8));')
replace(screen,
    '''        add(left,y,"Layer Down",SchematicaSession::layerDown);
        add(right,y,"Done",this::onClose);''',
    '''        add(left,y,"Layer Down",SchematicaSession::layerDown);
        y+=rowPitch;
        this.addRenderableWidget(Button.builder(
            Component.literal("Easy Pick: " + (this.minecraft.options.pletzelEasyPick.get() ? "ON" : "OFF")),
            b -> {
                boolean next=!this.minecraft.options.pletzelEasyPick.get();
                this.minecraft.options.pletzelEasyPick.set(next);
                System.out.println("[PletzelEasyPick] SETTING enabled="+next);
                this.minecraft.options.save();
                b.setMessage(Component.literal("Easy Pick: " + (next ? "ON" : "OFF")));
                status="Easy Pick " + (next?"ON":"OFF") +
                    ": hold Place Block to select matching hotbar items 1-9; never auto-place";
            }).bounds(left,y,150,20).build());
        add(right,y,"Done",this::onClose);''')

target=base/"net/pletzel/schematica/EasyPick26.java"
assert not target.exists(),str(target)
shutil.copyfile(Path(__file__).with_name("EasyPick26.java"),target)
text=target.read_text()
assert "getInventory().setSelectedSlot(chosen)" in text
assert "getInventory().getItem(slot)" in text
assert "mc.options.keyUse.isDown()" in text
assert "getStateForPlacement(context)" in text
assert "Freecam26.active()" in text
assert "new Serverbound" not in text
assert ".send(" not in text
assert "setBlock(" not in text
assert "getFreeSlot" not in text
print("NATIVE_PLETZEL_EASY_PICK_PATCH_APPLIED")

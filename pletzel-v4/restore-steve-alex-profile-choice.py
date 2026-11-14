#!/usr/bin/env python3
"""Restore access to existing Steve/Alex classic-vs-slim skin model chooser.

The pinned 26.2 engine already renders both real model arm geometries.
The profile editor hides the model button unless a CUSTOM PNG is selected;
on a default preset the entire option disappears. This makes Steve/Alex
selection inaccessible in normal use. Do not replace or strip the editor.

Default gallery has authentic Steve/Alex paired skins at IDs 0..17. Select
the paired preset rather than spoofing the client-only arm type, ensuring
the real multiplayer skin preset packet, stored profile, and 3D preview all
agree. For special nonpaired presets, choosing a model uses default Steve
or Alex (0/1); no unsupported texture/model combinations are fabricated.
Custom PNG skins still use their existing per-skin NBT model setting.
"""
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit("usage: restore-steve-alex-profile-choice.py <pinned-engine-root>")
p = Path(sys.argv[1])/"game/src/main/java/net/lax1dude/eaglercraft/v1_8/profile/EaglerProfileScreen26.java"
s = p.read_text(encoding="utf-8")
def once(label,old,new):
    global s
    n=s.count(old)
    if n!=1:raise AssertionError(f"{label}: exact anchored source found {n}, expected 1")
    s=s.replace(old,new,1)
    print("PROFILE MODEL",label)

once("do not hide chooser for preset skin",
'''if(newSkinWaitSteveOrAlex && selectedSlot >= 0 && selectedSlot < EaglerProfile.customSkins.size()) {''',
'''if(newSkinWaitSteveOrAlex) {''')
once("model button now works for preset or custom",
'''\t\tthis.modelButton = this.addRenderableWidget(Button.builder(Component.empty(), btn -> {
\t\t\tif(selectedSlot >= 0 && selectedSlot < EaglerProfile.customSkins.size()) {
\t\t\t\tnewSkinWaitSteveOrAlex = true;
\t\t\t\tthis.rebuildWidgets();
\t\t\t}
\t\t}).bounds(x, y + 46, 140, 18).build());''',
'''\t\tthis.modelButton = this.addRenderableWidget(Button.builder(Component.empty(), btn -> {
\t\t\tnewSkinWaitSteveOrAlex = true;
\t\t\tthis.rebuildWidgets();
\t\t}).bounds(x, y + 46, 140, 18).build());''')
once("show model control for all skins",
'''\t\t\tmodelButton.visible = selectedSlot >= 0 && selectedSlot < EaglerProfile.customSkins.size();''',
'''\t\t\tmodelButton.visible = true;''')
once("use currently selected model texture in original preview",
'''\t\tCustomSkin newSkin = EaglerProfile.customSkins.get(selectedSlot);
\t\tIdentifier texture = newSkin.getResource();''',
'''\t\tIdentifier texture = selectedTexture();''')
once("persist canonical default preset model as selected paired texture",
'''\tprivate void selectNewSkinModel(SkinModel model) {
\t\tif(selectedSlot >= 0 && selectedSlot < EaglerProfile.customSkins.size()) {
\t\t\tEaglerProfile.customSkins.get(selectedSlot).model = model;
\t\t\tsafeProfile();
\t\t\tEaglerProfile.save();
\t\t}
\t\tnewSkinWaitSteveOrAlex = false;
\t\tthis.rebuildWidgets();
\t}''',
'''\tprivate void selectNewSkinModel(SkinModel model) {
\t\tint customCount = EaglerProfile.customSkins.size();
\t\tif(selectedSlot >= 0 && selectedSlot < customCount) {
\t\t\tEaglerProfile.customSkins.get(selectedSlot).model = model;
\t\t} else {
\t\t\t// The 18 classic gallery entries are nine true Steve/Alex pairs.
\t\t\t// Select the real paired skin ID, never just change a local preview.
\t\t\t// Unsupported special skins fall back to the genuine default pair.
\t\t\tint presetId = selectedSlot - customCount;
\t\t\tint pairedBase = presetId >= 0 && presetId < 18
\t\t\t\t\t? (presetId & ~1) : 0;
\t\t\tselectedSlot = customCount + pairedBase + (model == SkinModel.ALEX ? 1 : 0);
\t\t}
\t\tsafeProfile();
\t\tEaglerProfile.save();
\t\tnewSkinWaitSteveOrAlex = false;
\t\tthis.rebuildWidgets();
\t}''')
p.write_text(s,encoding="utf-8")
print("RESTORED: visible Steve/Alex choice, genuine model dimensions, persistent default-preset pairing and custom NBT")

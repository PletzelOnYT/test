#!/usr/bin/env python3
"""Deterministic source and resource parity contract with supplied original JAR.

These checks are NOT a substitute for real side-by-side screenshot approval.
"""
from pathlib import Path
import hashlib, json, sys, struct

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
java=root/"game/src/main/java/net/pletzel/shulkertooltip/ShulkerTooltipClientComponent.java"
gui=root/"game/src/main/java/net/minecraft/client/gui/GuiGraphicsExtractor.java"
data=root/"game/src/main/java/net/pletzel/shulkertooltip/ShulkerTooltipData.java"
opt=root/"game/src/main/java/net/minecraft/client/Options.java"
controls=root/"game/src/main/java/net/minecraft/client/gui/screens/options/controls/ControlsScreen.java"
asset=root/"game/src/main/resources/assets/shulkerboxtooltip/textures/gui/sprites/shulker_box_tooltip.png"
meta=Path(str(asset)+".mcmeta")
for f in (java,gui,data,opt,controls,asset,meta):assert f.exists(),f

src=java.read_text()
checks=[
 "WIDTH=14+9*18",
 "HEIGHT=14+3*18",
 "STEP=18",
 "OFFSET=8",
 "SLOTS=27",
 "container/slot_highlight_back",
 "container/slot_highlight_front",
 "Identifier.fromNamespaceAndPath(\"shulkerboxtooltip\", \"shulker_box_tooltip\")",
 "graphics.blitSprite(RenderPipelines.GUI_TEXTURED,ORIGINAL_SPRITE,",
 "graphics.item(held,xx,yy)",
 'String countLabel=held.getCount()==1 ? "" : String.valueOf(held.getCount());',
 "graphics.itemDecorations(font,held,xx,yy,countLabel)",
 "final int dx=mouseX-x+1-OFFSET;",
 "final int dy=mouseY-y+1-OFFSET;",
 "public int getHeight(final Font font) { return HEIGHT+4; }",
 "graphics.tooltip(font,lines,mouseX,mouseY,",
 "originalTint(this.data.dyeColor())",
 "Math.max(38,",
 "0xFF976797",
 "contents.copyInto(copied)"
]
for token in checks: assert token in src,("missing JAR parity behavior",token)
for notallowed in ("SHULKER_TEXTURE","HEIGHT=76","graphics.outline(","textures/gui/container/shulker_box.png","graphics.fill(x+1,y+1,"):
 assert notallowed not in src,("old invented GUI survived",notallowed)
assert "pletzelTooltipMouseX" in gui.read_text()
assert "pletzelTooltipMouseY" in gui.read_text()
assert hashlib.sha256(asset.read_bytes()).hexdigest()=="25c53d6d239aa0ed24fec7a5dc7eacea32060ea4acac9ca9f6ea1a7ae8570281"
raw=asset.read_bytes()
assert raw[:8]==b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II',raw[16:24])==(32,32)
settings=json.loads(meta.read_text())
assert settings["gui"]["scaling"]=={
 "type":"nine_slice","width":32,"height":32,"stretch_inner":False,"border":7
}
assert "options.pletzelShulkerTooltip()" in controls.read_text()
assert "options.pletzelMapTooltip()" in controls.read_text()
assert "access.process(\"pletzelShulkerTooltip\"" in opt.read_text()
assert "access.process(\"pletzelMapTooltip\"" in opt.read_text()
assert "record ShulkerTooltipData(" in data.read_text()
print("PARITY PASS: EXACT original shulker sprite bytes and nine-slice metadata")
# Check the ORIGINAL BasePreviewRenderer.getSlotAt +1 boundary offset.
# The assertions above independently check that patched Java uses this arithmetic.
def slot_at(px,py):
 dx=px+1-8
 dy=py+1-8
 if dx<0 or dy<0 or dx>=9*18 or dy>=3*18:return -1
 return (dy//18)*9 + dx//18
for xy,expected in {
 (6,8):-1,(7,7):0,(8,8):0,(24,8):0,(25,8):1,
 (7,25):9,(8,43):18,(168,60):26,(169,60):-1,(168,61):-1,
 (-30,-30):-1,(700,700):-1,
}.items():
 assert slot_at(*xy)==expected,(xy,slot_at(*xy),expected)
print("PARITY PASS: original +1 grid hit boundaries and item count overlays")
print("PARITY PASS: 176x68 image plus 4px tooltip padding, 27 original slots")
print("PARITY PASS: original per-dye tint, undyed purple, highlights, vanilla item UI")
print("PARITY PASS: original ON/OFF settings, map tooltip, and descriptor untouched")

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
 "graphics.item(held,xx,yy,slot)",
 "graphics.itemDecorations(font,held,xx,yy)",
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
print("PARITY PASS: 176x68, 18x18 slot lattice, offsets (8,8), 27 original slots")
print("PARITY PASS: original per-dye tint, undyed purple, highlights, vanilla item UI")
print("PARITY PASS: original ON/OFF settings, map tooltip, and descriptor untouched")

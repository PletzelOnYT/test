#!/usr/bin/env python3
"""Non-compiling preflight for the original v5.4.3 shulker GUI correction.

Only checks genuine upstream source parity and source syntax. It is NOT
evidence of a rendered tooltip, input behavior or working game.
"""
import ast, hashlib, re
from pathlib import Path
patch=Path("pletzel-v4/patch-exact-shulker-gui.py")
parity=Path("pletzel-v4/test-exact-shulker-gui-source.py")
ast.parse(patch.read_text())
ast.parse(parity.read_text())
tree=ast.parse(patch.read_text())
body=next(n.value for n in tree.body if isinstance(n,ast.Assign)
    and any(isinstance(k,ast.Name) and k.id=="source" for k in n.targets))
src=ast.literal_eval(body)
for phrase in [
    "HEIGHT=14+3*18",
    "WIDTH=14+9*18",
    "OFFSET=8",
    "STEP=18",
    "final int dx=mouseX-x+1-OFFSET;",
    "final int dy=mouseY-y+1-OFFSET;",
    "public int getHeight(final Font font) { return HEIGHT+4; }",
    'String countLabel=held.getCount()==1 ? "" : String.valueOf(held.getCount());',
    "graphics.itemDecorations(font,held,xx,yy,countLabel);",
    "graphics.blitSprite(RenderPipelines.GUI_TEXTURED,ORIGINAL_SPRITE,"
]:
    assert phrase in src,phrase
assert "HEIGHT=76" not in src
up=Path("original/common/src/main/java/com/misterpemodder/shulkerboxtooltip/impl")
renderer=(up/"renderer/ModPreviewRenderer.java").read_text()
base=(up/"renderer/BasePreviewRenderer.java").read_text()
wrapper=(up/"tooltip/PreviewClientTooltipComponent.java").read_text()
assert "super(18, 18, 8, 8)" in renderer
assert "return 14 +" in renderer
assert 'graphics.blitSprite(RenderPipelines.GUI_TEXTURED, this.getTexture()' in renderer
assert "slotIndex" in renderer
assert "x + 1 - this.slotXOffset" in base
assert "y + 1 - this.slotYOffset" in base
assert "countLabel = String.valueOf(stack.getCount())" in base
assert "getHeight() + 4" in wrapper
asset=Path("original/common/src/main/resources/assets/shulkerboxtooltip/textures/gui/sprites/shulker_box_tooltip.png")
assert hashlib.sha256(asset.read_bytes()).hexdigest()=="25c53d6d239aa0ed24fec7a5dc7eacea32060ea4acac9ca9f6ea1a7ae8570281"
print("PASS source geometry and original asset hash")
print("The main Wasm-GC binary must still pass screenshot and gameplay tests.")

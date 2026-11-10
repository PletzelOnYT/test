#!/usr/bin/env python3
"""Build a transparent evidence board from an original public screenshot and
unchanged browser game screenshots. Not a fabricated mod runtime comparison.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path("original-shulker-gui-gameplay-evidence")
ref=Path("original-shulker-mod-full-preview.png")
actual=[root/(p+".png") for p in [
 "12-undyed-empty","15-green-partial","16-yellow-counts",
 "17-purple-full","19-resized-inventory"]]
actual=[p for p in actual if p.exists()]
if not actual:raise SystemExit("No compiled-game screenshot available")
w=820; h=490; out=Image.new("RGB",(w*2,h*max(1,len(actual))),(27,29,33))
draw=ImageDraw.Draw(out)
font=ImageFont.load_default()
refimg=Image.open(ref).convert("RGB") if ref.exists() else None
for i,p in enumerate(actual):
 draw.rectangle((0,i*h,w*2,i*h+26),fill=(50,52,56))
 draw.text((12,i*h+8),"Official mod Full Preview screenshot (reference, not same world)",font=font,fill="white")
 draw.text((w+12,i*h+8),"Pletzel V4 browser capture: "+p.stem,font=font,fill="white")
 if refimg:
  copy=refimg.copy();copy.thumbnail((w-18,h-45))
  out.paste(copy,(int((w-copy.width)/2),i*h+28))
 img=Image.open(p).convert("RGB");img.thumbnail((w-18,h-45))
 out.paste(img,(w+int((w-img.width)/2),i*h+28))
out.save(root/"reference-vs-pletzel-browser.png",optimize=True)
print("CREATED evidence comparison board; reference remains publicly published image, NOT a locally run Fabric client.")

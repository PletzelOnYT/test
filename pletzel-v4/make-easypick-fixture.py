#!/usr/bin/env python3
"""Deterministic real Sponge NBT with ten block types (nine in hotbar)."""
from pathlib import Path
import gzip,struct

MATERIALS=[
 "minecraft:stone","minecraft:oak_planks","minecraft:glass",
 "minecraft:cobblestone","minecraft:dirt","minecraft:sandstone",
 "minecraft:bricks","minecraft:gravel","minecraft:birch_planks",
 "minecraft:obsidian"
]
assert len(MATERIALS)==10 and len(set(MATERIALS))==10

def named(tag,name,payload):
 name=name.encode("utf8")
 return bytes([tag])+struct.pack(">H",len(name))+name+payload
def t_int(name,n):return named(3,name,struct.pack(">i",n))
def t_short(name,n):return named(2,name,struct.pack(">h",n))
def t_byte_array(name,data):return named(7,name,struct.pack(">i",len(data))+bytes(data))
def t_compound(name,*tags):return named(10,name,b"".join(tags)+b"\0")
def create(directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 # Each palette ID is under 128, so its Sponge varint takes exactly one byte.
 palette=t_compound("Palette",*(t_int(block,i) for i,block in enumerate(MATERIALS)))
 blob=t_compound("",t_int("Version",2),t_short("Width",10),t_short("Height",1),
                 t_short("Length",1),palette,
                 t_byte_array("BlockData",range(10)))
 out=directory/"easypick-ten-materials.schem"
 out.write_bytes(gzip.compress(blob,mtime=0))
 return out

if __name__=="__main__":
 import sys
 output=create(sys.argv[1] if len(sys.argv)>1 else "easypick-fixtures")
 print("EASY_PICK_FIXTURE",output,output.stat().st_size,"10 states")

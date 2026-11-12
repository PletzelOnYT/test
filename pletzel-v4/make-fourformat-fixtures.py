#!/usr/bin/env python3
"""Deterministic independent NBT fixtures for native Schematica browser tests.
All four formats and the required six block volumes, with invalid input fixture.
"""
from pathlib import Path
import gzip
import struct
import sys

def named(t,name,payload):
    n=name.encode("utf-8")
    return bytes([t])+struct.pack(">H",len(n))+n+payload
def t_str(name,s):
    p=s.encode("utf-8")
    return named(8,name,struct.pack(">H",len(p))+p)
def t_int(name,n):return named(3,name,struct.pack(">i",n))
def t_short(name,n):return named(2,name,struct.pack(">h",n))
def t_bytearray(name,b):return named(7,name,struct.pack(">i",len(b))+bytes(b))
def t_longarray(name,seq):return named(12,name,struct.pack(">i",len(seq))+b"".join(struct.pack(">Q",i&((1<<64)-1)) for i in seq))
def t_intarray(name,seq):return named(11,name,struct.pack(">i",len(seq))+b"".join(struct.pack(">i",i) for i in seq))
def compound_payload(*members):return b"".join(members)+b"\x00"
def t_compound(name,*members):return named(10,name,compound_payload(*members))
def t_list(name,t,payloads):return named(9,name,bytes([t])+struct.pack(">i",len(payloads))+b"".join(payloads))
def int_list(name,seq):return t_list(name,3,[struct.pack(">i",x) for x in seq])
def root(*members):return t_compound("",*members)
def compress(b):return gzip.compress(b,mtime=0)
def blocks_schem(w,h,l):
    size=w*h*l
    palette=t_compound("Palette",t_int("minecraft:stone",0))
    # Sponge varint 0 for every stone block; 1 byte per block.
    return compress(root(t_int("Version",2),t_short("Width",w),t_short("Height",h),
                         t_short("Length",l),palette,t_bytearray("BlockData",bytes(size))))
def legacy():
    w,h,l=5,4,5; size=w*h*l
    blocks=bytearray()
    for y in range(h):
        for z in range(l):
            for x in range(w):
                blocks.append(1 if y==0 or x in (0,w-1) or z in (0,l-1) else 0)
    return compress(root(t_short("Width",w),t_short("Height",h),t_short("Length",l),
        t_bytearray("Blocks",blocks),t_bytearray("Data",bytes(size)),t_str("Materials","Alpha")))
def structure():
    w,h,l=8,2,8
    blockrecords=[]
    for x in range(w):
        for z in range(l):
            for y in range(h):
                blockrecords.append(compound_payload(int_list("pos",[x,y,z]),t_int("state",0)))
    palette=t_list("palette",10,[compound_payload(t_str("Name","minecraft:stone"))])
    return compress(root(int_list("size",[w,h,l]),palette,t_list("blocks",10,blockrecords)))
def litematic():
    w,h,l=10,2,10;volume=w*h*l
    # A single stone palette entry uses the Litematica 2-bit minimum.
    words=[0]*((volume*2+63)//64)
    reg=t_compound("stone_build",
        t_compound("Position",t_int("x",-11),t_int("y",65),t_int("z",-13)),
        t_compound("Size",t_int("x",w),t_int("y",h),t_int("z",l)),
        t_list("BlockStatePalette",10,[compound_payload(t_str("Name","minecraft:stone"))]),
        t_longarray("BlockStates",words))
    return compress(root(t_compound("Regions",reg),t_int("MinecraftDataVersion",3465),t_int("Version",6)))
def produce(out):
    out.mkdir(parents=True,exist_ok=True)
    data={
      "basic.schematic":legacy(),
      "basic.schem":blocks_schem(8,2,8),
      "basic.nbt":structure(),
      "basic.litematic":litematic(),
      "bad.schem":b"not-a-valid-nbt",
    }
    for n in (4000,10000,50000,100000,500000,1000000):
        data[f"stress-{n}.schem"]=blocks_schem(100,1,n//100)
    for name,body in data.items():
        (out/name).write_bytes(body)
        print(name,len(body),"bytes",flush=True)
    assert all((out/name).stat().st_size>0 for name in data)
    return list(data)
if __name__=="__main__":produce(Path(sys.argv[1]) if len(sys.argv)>1 else Path("schematic-fixtures"))

package net.pletzel.schematica;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.zip.InflaterInputStream;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

/**
 * Native NBT schematic decoder. No small artificial block limit. Unknown states are
 * fatal errors instead of being silently replaced with unrelated blocks.
 *
 * Source coordinate convention: X-major within each Y/Z row, with a normalized
 * local bounding box. The placement anchor remains the existing Schematica origin.
 */
public final class SchematicFormats26 {
    public record Parsed(int width, int height, int length,
                         List<SchematicaSession.Cell> cells, int unknownCount) {}
    private record Tmp(int x, int y, int z, BlockState state) {}
    private static final class Accumulator {
        private final ArrayList<Tmp> blocks = new ArrayList<>();
        private int minX=Integer.MAX_VALUE,minY=Integer.MAX_VALUE,minZ=Integer.MAX_VALUE;
        private int maxX=Integer.MIN_VALUE,maxY=Integer.MIN_VALUE,maxZ=Integer.MIN_VALUE;
        private void bounds(int x,int y,int z,int w,int h,int l) throws IOException {
            if (w<=0||h<=0||l<=0) throw new IOException("Invalid schematic dimensions");
            long endX=(long)x+w-1,endY=(long)y+h-1,endZ=(long)z+l-1;
            if(endX>Integer.MAX_VALUE||endY>Integer.MAX_VALUE||endZ>Integer.MAX_VALUE
                ||endX<Integer.MIN_VALUE||endY<Integer.MIN_VALUE||endZ<Integer.MIN_VALUE)
                throw new IOException("Schematic coordinates overflow");
            minX=Math.min(minX,x);minY=Math.min(minY,y);minZ=Math.min(minZ,z);
            maxX=Math.max(maxX,(int)endX);maxY=Math.max(maxY,(int)endY);maxZ=Math.max(maxZ,(int)endZ);
        }
        private void add(int x,int y,int z,BlockState state) {
            if (!state.isAir()) blocks.add(new Tmp(x,y,z,state));
        }
        private Parsed finish() throws IOException {
            if(minX==Integer.MAX_VALUE) throw new IOException("No valid schematic region");
            long w=(long)maxX-minX+1,h=(long)maxY-minY+1,l=(long)maxZ-minZ+1;
            if(w>Integer.MAX_VALUE||h>Integer.MAX_VALUE||l>Integer.MAX_VALUE
              ||w*h>Integer.MAX_VALUE||w*h*l>Integer.MAX_VALUE)
                throw new IOException("Schematic exceeds 32-bit Java indexed-volume capacity");
            List<SchematicaSession.Cell> result=new ArrayList<>(blocks.size());
            for(Tmp b:blocks) result.add(new SchematicaSession.Cell(b.x-minX,b.y-minY,b.z-minZ,b.state));
            return new Parsed((int)w,(int)h,(int)l,result,0);
        }
    }
    private SchematicFormats26() {}

    public static Parsed read(byte[] input,String filename) throws IOException {
        if(input==null||input.length==0) throw new IOException("Empty schematic");
        // NbtAccounter bounds decompression to a practical 512 MiB; no block-count cap.
        // This is a resource safety boundary, not a 4,096/100,000-block limit.
        CompoundTag root;
        try {
            root=NbtIo.readCompressed(new ByteArrayInputStream(input),NbtAccounter.create(512L*1024*1024));
        } catch(Exception gzipError) {
            try(DataInputStream in=new DataInputStream(new InflaterInputStream(new ByteArrayInputStream(input)))) {
                root=NbtIo.read(in,NbtAccounter.create(512L*1024*1024));
            } catch(Exception zlibError) {
                try(DataInputStream in=new DataInputStream(new ByteArrayInputStream(input))) {
                    root=NbtIo.read(in,NbtAccounter.create(512L*1024*1024));
                } catch(Exception rawError) {
                    throw new IOException("NBT unreadable as gzip, zlib, or raw: "+rawError.getMessage(),rawError);
                }
            }
        }
        if(root.getCompound("Regions").isPresent()) return litematic(root);
        if(root.getList("blocks").isPresent() && root.getList("palette").isPresent()) return structure(root);
        CompoundTag sponge=root.getCompound("Schematic").orElse(root);
        if(sponge.getCompound("Blocks").isPresent() || sponge.getCompound("Palette").isPresent())
            return sponge(sponge);
        if(root.getByteArray("Blocks").isPresent() && root.getByteArray("Data").isPresent())
            return classic(root);
        throw new IOException("Unknown schematic layout in "+filename);
    }

    private static int intEither(CompoundTag t,String name) {
        return t.getInt(name).orElseGet(()->(int)t.getShortOr(name,(short)0));
    }
    private static int[] size3(CompoundTag t,String k) throws IOException {
        int[] a=t.getIntArray(k).orElse(null);
        if(a!=null&&a.length==3)return a;
        ListTag b=t.getListOrEmpty(k);
        if(b.size()==3)return new int[]{b.getIntOr(0,0),b.getIntOr(1,0),b.getIntOr(2,0)};
        throw new IOException("Missing 3D vector: "+k);
    }
    private static int[] compoundVec(CompoundTag t) {
        return new int[]{t.getIntOr("x",0),t.getIntOr("y",0),t.getIntOr("z",0)};
    }
    private static int count(int w,int h,int l) throws IOException {
        if(w<=0||h<=0||l<=0) throw new IOException("Invalid dimensions "+w+"x"+h+"x"+l);
        long size=(long)w*h*l;
        if(size>Integer.MAX_VALUE) throw new IOException("32-bit indexed schematic volume exceeded: "+size);
        return (int)size;
    }

    @SuppressWarnings({"rawtypes","unchecked"})
    private static BlockState modernState(String name,CompoundTag properties) throws IOException {
        final Identifier identifier;
        try { identifier=Identifier.parse(name); }
        catch(RuntimeException ex) {throw new IOException("Invalid block identifier "+name,ex);}
        if(!BuiltInRegistries.BLOCK.containsKey(identifier))
            throw new IOException("Block not present in Minecraft 26.2: "+name);
        Block block=BuiltInRegistries.BLOCK.getValue(identifier);
        BlockState state=block.defaultBlockState();
        for(String key:properties.keySet()) {
            Property property=block.getStateDefinition().getProperty(key);
            if(property==null) throw new IOException("Unsupported property "+name+"["+key+"]");
            String raw=properties.getStringOr(key,"");
            Optional value=property.getValue(raw);
            if(value.isEmpty()) throw new IOException("Invalid block-state value "+name+"["+key+"="+raw+"]");
            state=state.setValue(property,(Comparable)value.get());
        }
        return state;
    }
    private static BlockState paletteEntry(CompoundTag tag) throws IOException {
        return modernState(tag.getStringOr("Name","minecraft:air"),tag.getCompoundOrEmpty("Properties"));
    }
    private static BlockState stateString(String string) throws IOException {
        int bracket=string.indexOf('[');
        if(bracket<0) return modernState(string,new CompoundTag());
        if(!string.endsWith("]"))throw new IOException("Invalid palette entry: "+string);
        CompoundTag props=new CompoundTag();
        String inner=string.substring(bracket+1,string.length()-1);
        if(!inner.isEmpty()) for(String part:inner.split(",")) {
            String[] p=part.trim().split("=",2);
            if(p.length!=2)throw new IOException("Invalid palette property: "+part);
            props.putString(p[0].trim(),p[1].trim());
        }
        return modernState(string.substring(0,bracket),props);
    }
    private static Parsed classic(CompoundTag root) throws IOException {
        int w=intEither(root,"Width"),h=intEither(root,"Height"),l=intEither(root,"Length");
        int total=count(w,h,l);
        byte[] blocks=root.getByteArray("Blocks").orElseThrow(()->new IOException("Missing Blocks"));
        byte[] data=root.getByteArray("Data").orElseThrow(()->new IOException("Missing Data"));
        byte[] high=root.getByteArray("AddBlocks").orElse(new byte[0]);
        if(blocks.length!=total||data.length!=total||
            (high.length>0&&high.length<(total+1L)/2))
            throw new IOException("Legacy Blocks/Data/AddBlocks lengths disagree with dimensions");
        Accumulator a=new Accumulator();a.bounds(0,0,0,w,h,l);
        for(int i=0;i<total;i++) {
            int id=blocks[i]&255;
            if(high.length>0) id|=((high[i>>1]>>((i&1)*4))&15)<<8;
            if(id==0)continue;
            BlockState state=SchematicaSession.resolveLegacy(id,data[i]&15);
            if(state==null)throw new IOException("Unsupported legacy ID "+id+":"+(data[i]&15)+" at block "+i);
            int x=i%w,z=(i/w)%l,y=i/(w*l);
            a.add(x,y,z,state);
        }
        return a.finish();
    }
    private static Parsed sponge(CompoundTag root) throws IOException {
        int version=root.getIntOr("Version",2);
        if(version<1||version>3)throw new IOException("Unsupported Sponge schematic version "+version);
        int w=intEither(root,"Width"),h=intEither(root,"Height"),l=intEither(root,"Length");
        int total=count(w,h,l);
        CompoundTag blocksCompound=root.getCompound("Blocks").orElse(null);
        CompoundTag paletteTag=blocksCompound==null ? root.getCompoundOrEmpty("Palette"):blocksCompound.getCompoundOrEmpty("Palette");
        byte[] packed=blocksCompound==null ? root.getByteArray("BlockData").orElse(new byte[0])
            :blocksCompound.getByteArray("Data").orElse(new byte[0]);
        if(paletteTag.size()==0||packed.length==0)throw new IOException("Missing Sponge palette or block data");
        int max=-1;
        for(String key:paletteTag.keySet())max=Math.max(max,paletteTag.getIntOr(key,-1));
        if(max<0||max>total+65536L)throw new IOException("Invalid Sponge palette indices");
        BlockState[] palette=new BlockState[max+1];
        for(String key:paletteTag.keySet()) {
            int idx=paletteTag.getIntOr(key,-1);
            if(idx<0||idx>=palette.length||palette[idx]!=null)throw new IOException("Duplicate/bad palette index");
            palette[idx]=stateString(key);
        }
        int[] offset=root.getIntArray("Offset").orElse(new int[]{0,0,0});
        if(offset.length!=3)throw new IOException("Invalid Sponge Offset");
        Accumulator a=new Accumulator();a.bounds(offset[0],offset[1],offset[2],w,h,l);
        int cursor=0;
        for(int i=0;i<total;i++) {
            int value=0,shift=0,b;
            do {
                if(cursor>=packed.length||shift>28)throw new IOException("Corrupted Sponge palette varint at "+i);
                b=packed[cursor++]&255;
                value|=(b&127)<<shift;
                shift+=7;
            } while((b&128)!=0);
            if(value<0||value>=palette.length||palette[value]==null)
                throw new IOException("Unknown Sponge palette index "+value+" at "+i);
            int x=i%w,z=(i/w)%l,y=i/(w*l);
            a.add(offset[0]+x,offset[1]+y,offset[2]+z,palette[value]);
        }
        if(cursor!=packed.length)throw new IOException("Unexpected trailing Sponge block data");
        return a.finish();
    }
    private static Parsed structure(CompoundTag root) throws IOException {
        int[] size=size3(root,"size");
        int w=size[0],h=size[1],l=size[2];count(w,h,l);
        ListTag colors=root.getListOrEmpty("palette");
        if(colors.size()==0)throw new IOException("Structure block palette empty");
        BlockState[] palette=new BlockState[colors.size()];
        for(int i=0;i<palette.length;i++)palette[i]=paletteEntry(colors.getCompoundOrEmpty(i));
        Accumulator a=new Accumulator();a.bounds(0,0,0,w,h,l);
        ListTag blocks=root.getListOrEmpty("blocks");
        for(int i=0;i<blocks.size();i++) {
            CompoundTag b=blocks.getCompoundOrEmpty(i);
            int[] pos=size3(b,"pos");
            if(pos[0]<0||pos[1]<0||pos[2]<0||pos[0]>=w||pos[1]>=h||pos[2]>=l)
                throw new IOException("Structure block outside bounds at index "+i);
            int state=b.getIntOr("state",-1);
            if(state<0||state>=palette.length)throw new IOException("Invalid structure palette index "+state);
            a.add(pos[0],pos[1],pos[2],palette[state]);
        }
        return a.finish();
    }
    private static Parsed litematic(CompoundTag root) throws IOException {
        CompoundTag regions=root.getCompoundOrEmpty("Regions");
        if(regions.size()==0)throw new IOException("Litematic has no regions");
        Accumulator a=new Accumulator();
        for(String key:regions.keySet()) {
            CompoundTag region=regions.getCompoundOrEmpty(key);
            int[] origin=compoundVec(region.getCompoundOrEmpty("Position"));
            int[] size=compoundVec(region.getCompoundOrEmpty("Size"));
            int w=Math.abs(size[0]),h=Math.abs(size[1]),l=Math.abs(size[2]);
            int count=count(w,h,l);
            int lowX=origin[0]+Math.min(0,size[0]+1),lowY=origin[1]+Math.min(0,size[1]+1);
            int lowZ=origin[2]+Math.min(0,size[2]+1);
            a.bounds(lowX,lowY,lowZ,w,h,l);
            ListTag colors=region.getListOrEmpty("BlockStatePalette");
            BlockState[] palette=new BlockState[colors.size()];
            if(palette.length==0)throw new IOException("Missing Litematic block palette: "+key);
            for(int i=0;i<palette.length;i++)palette[i]=paletteEntry(colors.getCompoundOrEmpty(i));
            long[] states=region.getLongArray("BlockStates").orElseThrow(()->new IOException("Missing packed block states: "+key));
            int bits=Math.max(2,32-Integer.numberOfLeadingZeros(palette.length-1));
            if((long)states.length*64<count*(long)bits)throw new IOException("Truncated Litematic packed states");
            long mask=(1L<<bits)-1L;
            for(int i=0;i<count;i++) {
                long bit=(long)i*bits;
                int word=(int)(bit>>>6),shift=(int)(bit&63);
                long value=states[word]>>>shift;
                if(shift+bits>64)value|=states[word+1]<<(64-shift);
                int idx=(int)(value&mask);
                if(idx<0||idx>=palette.length)throw new IOException("Litematic palette index out of range "+idx);
                int x=i%w,z=(i/w)%l,y=i/(w*l);
                int px=origin[0]+(size[0]<0?-x:x),py=origin[1]+(size[1]<0?-y:y);
                int pz=origin[2]+(size[2]<0?-z:z);
                a.add(px,py,pz,palette[idx]);
            }
        }
        return a.finish();
    }
}

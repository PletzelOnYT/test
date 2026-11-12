package net.pletzel.maptooltip;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Base64;
import net.lax1dude.eaglercraft.v1_8.EagRuntime;
import net.minecraft.client.Minecraft;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.saveddata.maps.MapId;
import net.minecraft.world.level.saveddata.maps.MapItemSavedData;
import net.minecraft.world.level.saveddata.maps.MapDecoration;
import net.minecraft.world.level.saveddata.maps.MapDecorationTypes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.component.MapDecorations;

/**
 * Durable original 128x128 Minecraft packed-color bytes, NOT generated art.
 * EagRuntime storage uses namespaced browser localStorage, including across
 * game restarts at the same origin. Maps are scoped by local world save path
 * or multiplayer server address, dimension and exact numeric MapId.
 *
 * Ambiguous ordinary maps are never automatically called "map art": user
 * marking is required. Recognizable explorer/structure icons are excluded.
 * The cache is deliberately bounded to avoid browser storage exhaustion.
 */
public final class MapArtStore26 {
    public static final int UNMARKED=0, ART=1, EXCLUDED=2;
    private static final int PIXELS=128*128, MAX_DISK_MAPS=128, MAX_MEMORY_MAPS=24;
    private static final byte[] HEADER=new byte[]{'P','M','A','R','T','2','6',1};
    private static final LinkedHashMap<String,byte[]> MEMORY=new LinkedHashMap<>(32,.75f,true);
    private static final LinkedHashMap<String,MapItemSavedData> RENDER_DATA=new LinkedHashMap<>(32,.75f,true);
    private static final Map<String,Integer> LABELS=new LinkedHashMap<>();
    private static final Map<String,Long> LAST_CHECK=new LinkedHashMap<>();
    private static String currentWorld="";
    private MapArtStore26(){}

    public static String worldScope() {
        Minecraft mc=Minecraft.getInstance();
        if(mc==null || mc.level==null) return null;
        String origin;
        if(mc.getSingleplayerServer()!=null) {
            origin="save:"+mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT);
        } else if(mc.getCurrentServer()!=null) {
            origin="server:"+mc.getCurrentServer().ip;
        } else return null;
        // A different browser origin has different EagRuntime storage.
        return origin+";dimension="+mc.level.dimension().identifier();
    }

    private static String encodedScope() {
        String world=worldScope();
        if(world==null) return null;
        if(!world.equals(currentWorld)) {
            currentWorld=world;
            MEMORY.clear(); RENDER_DATA.clear(); LABELS.clear(); LAST_CHECK.clear();
        }
        return Base64.getUrlEncoder().withoutPadding().encodeToString(world.getBytes(StandardCharsets.UTF_8));
    }
    private static String key(MapId id, String kind) {
        String scope=encodedScope();
        return scope==null?null:"pletzel.mapart26."+kind+"."+scope+"."+id.id();
    }
    private static String registry() {
        String scope=encodedScope();
        return scope==null?null:"pletzel.mapart26.index."+scope;
    }
    private static void capMemory() {
        while(MEMORY.size()>MAX_MEMORY_MAPS) MEMORY.remove(MEMORY.keySet().iterator().next());
        while(RENDER_DATA.size()>MAX_MEMORY_MAPS) RENDER_DATA.remove(RENDER_DATA.keySet().iterator().next());
    }
    private static String[] indexed() {
        String k=registry();if(k==null)return new String[0];
        byte[] raw=EagRuntime.getStorage(k);
        return raw==null||raw.length==0?new String[0]:new String(raw,StandardCharsets.UTF_8).split(",");
    }
    private static void register(MapId id) {
        String index=registry();if(index==null)return;
        String idValue=Integer.toString(id.id());
        java.util.LinkedHashSet<String> ids=new java.util.LinkedHashSet<>();
        for(String entry:indexed()) if(!entry.isEmpty()&&!entry.equals(idValue)) ids.add(entry);
        ids.add(idValue);
        while(ids.size()>MAX_DISK_MAPS) {
            String oldest=ids.iterator().next();ids.remove(oldest);
            String scope=encodedScope();
            EagRuntime.setStorage("pletzel.mapart26.pixel."+scope+"."+oldest,null);
            EagRuntime.setStorage("pletzel.mapart26.policy."+scope+"."+oldest,null);
        }
        EagRuntime.setStorage(index,String.join(",",ids).getBytes(StandardCharsets.UTF_8));
    }

    public static int policy(MapId id) {
        String k=key(id,"policy");if(k==null)return UNMARKED;
        Integer cached=LABELS.get(k);if(cached!=null)return cached;
        byte[] bytes=EagRuntime.getStorage(k);
        int p=bytes!=null&&bytes.length==1&&(bytes[0]==1||bytes[0]==2)?bytes[0]:UNMARKED;
        LABELS.put(k,p);return p;
    }
    public static void setPolicy(MapId id,int p) {
        if(p<0||p>2)return;
        String k=key(id,"policy");if(k==null)return;
        if(p==UNMARKED)EagRuntime.setStorage(k,null);
        else EagRuntime.setStorage(k,new byte[]{(byte)p});
        LABELS.put(k,p);
        register(id);
        if(p==ART) {
            Minecraft mc=Minecraft.getInstance();
            if(mc.level!=null)observe(id,mc.level.getMapData(id));
        }
        System.out.println("[PletzelMapArt] POLICY id="+id.id()+" mode="+p);
    }

    public static boolean isExplorer(ItemStack stack) {
        String name=stack.getHoverName().getString().toLowerCase(java.util.Locale.ROOT);
        if(name.contains("explorer")||name.contains("treasure")||name.contains("buried")||
           name.contains("woodland")||name.contains("monument")||
           name.contains("structure")||name.contains("village"))return true;
        MapDecorations decorations=stack.getOrDefault(DataComponents.MAP_DECORATIONS, MapDecorations.EMPTY);
        for(MapDecorations.Entry e:decorations.decorations().values()) {
            if(e.type().is(MapDecorationTypes.WOODLAND_MANSION)||
               e.type().is(MapDecorationTypes.OCEAN_MONUMENT)||
               e.type().is(MapDecorationTypes.RED_X))return true;
        }
        return false;
    }
    public static boolean isExplorer(MapItemSavedData data) {
        if(data==null)return false;
        for(MapDecoration d:data.getDecorations()) {
            if(d.type().is(MapDecorationTypes.WOODLAND_MANSION)||
               d.type().is(MapDecorationTypes.OCEAN_MONUMENT)||
               d.type().is(MapDecorationTypes.RED_X))return true;
        }
        return false;
    }
    public static boolean canPreview(MapId id,boolean itemExplorer,MapItemSavedData live) {
        Minecraft mc=Minecraft.getInstance();
        return mc!=null && mc.options.pletzelShowMapArt.get() &&
          policy(id)==ART &&
          (!mc.options.pletzelExcludeExplorer.get() || (!itemExplorer&&!isExplorer(live)));
    }

    /**
     * A newly created client MapItemSavedData has a 16384-byte array of zeroes
     * before any real map-color packet. That is NOT proof that the map was
     * actually observed, so it must never overwrite persisted artwork.
     * Previously observed packed colors remain untouched until actual pixels
     * arrive from the server. A fully transparent/empty map cannot be
     * distinguished from an uninitialized map and is left unlearned.
     */
    public static boolean hasObservedColors(MapItemSavedData live) {
        if(live==null||live.colors==null||live.colors.length!=PIXELS)return false;
        for(byte color:live.colors)if(color!=0)return true;
        return false;
    }
    /** Exactly the actual map pixel bytes, copied unchanged, plus version. */
    public static void observe(MapId id,MapItemSavedData live) {
        if(id==null||!hasObservedColors(live))return;
        Minecraft mc=Minecraft.getInstance();
        if(mc==null||mc.options==null||!mc.options.pletzelRememberMapArt.get())return;
        if(!canPreview(id,false,live))return;
        String k=key(id,"pixel");if(k==null)return;
        long now=System.nanoTime();
        Long checked=LAST_CHECK.get(k);
        if(checked!=null&&now-checked<750000000L)return;
        LAST_CHECK.put(k,now);
        byte[] existing=read(id);
        if(existing!=null&&Arrays.equals(existing,live.colors))return;
        byte[] output=new byte[HEADER.length+PIXELS];
        System.arraycopy(HEADER,0,output,0,HEADER.length);
        System.arraycopy(live.colors,0,output,HEADER.length,PIXELS);
        EagRuntime.setStorage(k,output);
        MEMORY.put(k,live.colors.clone());
        MapItemSavedData rendered=RENDER_DATA.get(k);
        if(rendered!=null)System.arraycopy(live.colors,0,rendered.colors,0,PIXELS);
        capMemory();register(id);
        System.out.println("[PletzelMapArt] SAVED id="+id.id()+" pixels=16384");
    }
    public static byte[] read(MapId id) {
        String k=key(id,"pixel");if(k==null)return null;
        byte[] cached=MEMORY.get(k);if(cached!=null)return cached.clone();
        byte[] stored=EagRuntime.getStorage(k);
        if(stored==null||stored.length!=HEADER.length+PIXELS)return null;
        for(int i=0;i<HEADER.length;i++)if(stored[i]!=HEADER[i])return null;
        byte[] colors=Arrays.copyOfRange(stored,HEADER.length,stored.length);
        MEMORY.put(k,colors);capMemory();
        return colors.clone();
    }
    public static MapItemSavedData cachedData(MapId id) {
        Minecraft mc=Minecraft.getInstance();if(mc==null||mc.level==null)return null;
        byte[] colors=read(id);if(colors==null)return null;
        // This object only adapts ORIGINAL previously seen server pixels to
        // Minecraft's vanilla renderer. No pixel values are invented.
        String k=key(id,"pixel");
        MapItemSavedData snapshot=RENDER_DATA.get(k);
        if(snapshot!=null)return snapshot;
        snapshot=MapItemSavedData.createForClient((byte)0,false,mc.level.dimension());
        System.arraycopy(colors,0,snapshot.colors,0,PIXELS);
        RENDER_DATA.put(k,snapshot);capMemory();
        return snapshot;
    }
    public static void clearSaved() {
        String scope=encodedScope();if(scope==null)return;
        for(String id:indexed()) {
            if(id.isEmpty())continue;
            EagRuntime.setStorage("pletzel.mapart26.pixel."+scope+"."+id,null);
        }
        MEMORY.keySet().removeIf(k->k.contains("."+scope+"."));
        RENDER_DATA.keySet().removeIf(k->k.contains("."+scope+"."));
        String index=registry();
        // Keep labels (user's deliberate Map Art/Exclude classifications),
        // but release the real-image storage. They can be learned again.
        System.out.println("[PletzelMapArt] CLEAR scope="+scope);
    }
    public static void markHeld(boolean art) {
        Minecraft mc=Minecraft.getInstance();
        if(mc==null||mc.player==null)return;
        ItemStack stack=mc.player.getMainHandItem();
        MapId id=stack.get(DataComponents.MAP_ID);
        if(id==null)return;
        if(art&&isExplorer(stack)&&mc.options.pletzelExcludeExplorer.get()) {
            System.out.println("[PletzelMapArt] BLOCKED_EXPLORER id="+id.id());return;
        }
        setPolicy(id,art?ART:EXCLUDED);
    }
}

package net.lax1dude.eaglercraft.v1_8.internal;

import org.teavm.jso.JSBody;

/**
 * TeaVM browser-only IndexedDB backing for persistent real MapId pixel bytes.
 * Java Map Tooltip callers remain synchronous: reads return a cache hit or
 * pending (null); after IndexedDB resolves, the next hovered frame succeeds.
 *
 * Per-browser-origin DB; per-world/server+dimension+MapId keys are constructed
 * in MapArtStore26. No fake map colors or GPU resources are stored.
 */
public final class PletzelMapArtIndexedDB26 {
    private PletzelMapArtIndexedDB26() {}

    @JSBody(script="return typeof indexedDB !== 'undefined';")
    private static native boolean browserHasIndexedDB();

    @JSBody(script=
        "if(globalThis.__pletzelMapArtIndexedDB26)return;"+
        "var s={db:null,cache:new Map(),fetching:new Set(),queued:[],disabled:false};"+
        "globalThis.__pletzelMapArtIndexedDB26=s;"+
        "try{var req=indexedDB.open('pletzel-map-art-v1',1);"+
        "req.onupgradeneeded=function(){if(!req.result.objectStoreNames.contains('pixels'))"+
        "req.result.createObjectStore('pixels');};"+
        "req.onsuccess=function(){s.db=req.result;"+
        "for(var i=0;i<s.queued.length;i++){var item=s.queued[i];"+
        "try{var tx=s.db.transaction('pixels','readwrite');"+
        "var os=tx.objectStore('pixels');"+
        "if(item[1]===null)os.delete(item[0]);else os.put(item[1],item[0]);}catch(e){}}"+
        "s.queued=[];};"+
        "req.onerror=function(){s.disabled=true;};"+
        "}catch(e){s.disabled=true;}"
    )
    private static native void initializeJs();

    @JSBody(script="var s=globalThis.__pletzelMapArtIndexedDB26;return s&&!s.disabled;")
    private static native boolean usableJs();

    @JSBody(params={"key","value"},script=
        "var s=globalThis.__pletzelMapArtIndexedDB26;"+
        "if(!s||s.disabled)return;"+
        "s.cache.set(key,value);"+
        "if(!s.db){s.queued.push([key,value]);return;}"+
        "try{var tx=s.db.transaction('pixels','readwrite');"+
        "var os=tx.objectStore('pixels');"+
        "if(value===null)os.delete(key);else os.put(value,key);}catch(e){}"
    )
    private static native void writeJs(String key,String value);

    @JSBody(params={"key"},script=
        "var s=globalThis.__pletzelMapArtIndexedDB26;"+
        "if(!s||s.disabled)return null;"+
        "if(s.cache.has(key))return s.cache.get(key);"+
        "if(s.db&&!s.fetching.has(key)){"+
        "s.fetching.add(key);"+
        "try{var req=s.db.transaction('pixels','readonly').objectStore('pixels').get(key);"+
        "req.onsuccess=function(){s.cache.set(key,req.result===undefined?null:req.result);"+
        "s.fetching.delete(key);};"+
        "req.onerror=function(){s.fetching.delete(key);};"+
        "}catch(e){s.fetching.delete(key);}}"+
        "return null;"
    )
    private static native String readJs(String key);

    public static boolean available() {
        if(!browserHasIndexedDB())return false;
        initializeJs();
        return usableJs();
    }

    /** Nonblocking write; false means the regular EagRuntime fallback applies. */
    public static boolean put(String fullKey,String base64OrNull) {
        if(!available())return false;
        writeJs(fullKey,base64OrNull);
        return true;
    }

    /** Nonblocking read; null means not cached or not yet hydrated. */
    public static String get(String fullKey) {
        if(!available())return null;
        return readJs(fullKey);
    }
}

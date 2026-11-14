package net.pletzel.maptooltip;

import net.lax1dude.eaglercraft.v1_8.EagRuntime;

/** Map Tooltip-only native GUI size setting; independent of Schematica. */
public final class MapTooltipPreviewSize26 {
    private static final String KEY="pletzel.maptooltip.previewSize26";
    private static int size;
    private MapTooltipPreviewSize26(){}
    public static int get() {
        if(size==0) {
            byte[] saved=EagRuntime.getStorage(KEY);
            size=saved!=null&&saved.length==1&&saved[0]==96?96:
                 saved!=null&&saved.length==1&&saved[0]==(byte)128?128:66;
        }
        return size;
    }
    public static int cycle() {
        size=get()==66?96:get()==96?128:66;
        EagRuntime.setStorage(KEY,new byte[]{(byte)size});
        return size;
    }
}

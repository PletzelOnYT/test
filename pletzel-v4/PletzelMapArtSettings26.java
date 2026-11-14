package net.pletzel.schematica;

import net.pletzel.maptooltip.MapArtStore26;
import net.pletzel.maptooltip.MapTooltipPreviewSize26;
import net.minecraft.client.OptionInstance;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Independent Map Tooltip settings reached ONLY from Pletzel Mods. */
public final class PletzelMapArtSettings26 extends Screen {
    private final Screen parent;
    private String note="All ordinary maps are previewed; explorer maps excluded.";
    public PletzelMapArtSettings26(Screen parent) {
        super(Component.literal("Map Tooltips Settings"));
        this.parent=parent;
    }
    private int widthOfButtons() {
        return Math.min(150,Math.max(72,(this.width-24)/2));
    }
    private void button(int x,int y,int w,String label,Runnable action) {
        this.addRenderableWidget(Button.builder(Component.literal(label),b->action.run())
            .bounds(x,y,w,20).build());
    }
    private void option(int x,int y,int w,String label,OptionInstance<Boolean> value) {
        this.addRenderableWidget(Button.builder(
            Component.literal(label+": "+(value.get()?"ON":"OFF")),
            b->{
                boolean next=!value.get();
                value.set(next);this.minecraft.options.save();
                b.setMessage(Component.literal(label+": "+(next?"ON":"OFF")));
                note=label+" "+(next?"enabled":"disabled")+" (saved)";
                System.out.println("[PletzelMapTooltipSettings] "+label+"="+next);
            }).bounds(x,y,w,20).build());
    }
    @Override protected void init() {
        System.out.println("[PletzelMapTooltipSettings] OPEN");
        int w=widthOfButtons(),left=this.width/2-w-4,right=this.width/2+4;
        int top=Math.max(52,Math.min(60,this.height-154));
        option(left,top,w,"Enable Map Tooltips",this.minecraft.options.pletzelShowMapArt);
        option(right,top,w,"Remember Maps",this.minecraft.options.pletzelRememberMapArt);
        option(left,top+28,w,"Persistent Map Cache",this.minecraft.options.pletzelMapPersistentCache);
        option(right,top+28,w,"Exclude Explorer",this.minecraft.options.pletzelExcludeExplorer);
        button(left,top+56,w,"Preview Size: "+MapTooltipPreviewSize26.get(),()->
            {int px=MapTooltipPreviewSize26.cycle();
             note="Map preview: "+px+"x"+px+" GUI pixels (saved)";this.rebuildWidgets();});
        button(right,top+56,w,"Exclude Held Map",()->
            {MapArtStore26.markHeld(false);note="Selected held map excluded";});
        button(left,top+84,w,"Allow Held Map",()->
            {MapArtStore26.markHeld(true);note="Held map eligible for normal preview";});
        button(right,top+84,w,"Clear Saved Maps",()->
            {MapArtStore26.clearSaved();note="Saved map pixels cleared for this world/server";});
        button(this.width/2-Math.min(w,110)/2,this.height-28,Math.min(w,110),
            "Done",this::onClose);
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g,int mx,int my,float delta) {
        super.extractRenderState(g,mx,my,delta);
        g.centeredText(this.font,Component.literal("Map Tooltips (independent mod)"),
            this.width/2,8,0xffffffff);
        g.centeredText(this.font,Component.literal(
            this.font.plainSubstrByWidth(note,Math.max(64,this.width-20))),
            this.width/2,29,0xffaaffff);
    }
    @Override public void onClose() {this.minecraft.gui.setScreen(parent);}
}

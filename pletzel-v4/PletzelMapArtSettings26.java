package net.pletzel.schematica;

import net.pletzel.maptooltip.MapArtStore26;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Explicit, persistent map art classification; explorer maps stay excluded. */
public final class PletzelMapArtSettings26 extends Screen {
    private final Screen parent;
    private String note="Hold a filled map, then choose Mark or Exclude.";
    public PletzelMapArtSettings26(Screen parent) {
        super(Component.literal("Map Art Settings"));this.parent=parent;
    }
    private void button(int x,int y,String name,Runnable action) {
        this.addRenderableWidget(Button.builder(Component.literal(name),b->action.run())
            .bounds(x,y,150,20).build());
    }
    private void option(int x,int y,String label,net.minecraft.client.OptionInstance<Boolean> o) {
        this.addRenderableWidget(Button.builder(
            Component.literal(label+": "+(o.get()?"ON":"OFF")),b->{
                boolean next=!o.get();o.set(next);this.minecraft.options.save();
                b.setMessage(Component.literal(label+": "+(next?"ON":"OFF")));
            }).bounds(x,y,150,20).build());
    }
    @Override protected void init(){
        int left=this.width/2-154,right=this.width/2+4;
        int y=Math.max(48,Math.min(60,this.height-160));
        option(left,y,"Remember Map Art",this.minecraft.options.pletzelRememberMapArt);
        option(right,y,"Show Art Previews",this.minecraft.options.pletzelShowMapArt);
        y+=25;
        option(left,y,"Exclude Explorer",this.minecraft.options.pletzelExcludeExplorer);
        button(right,y,"Mark Held Map as Art",()->{
            MapArtStore26.markHeld(true);note="Marked held map as art, if eligible";});
        y+=25;
        button(left,y,"Exclude Held Map",()->{
            MapArtStore26.markHeld(false);note="Excluded held map from art previews";});
        button(right,y,"Clear Saved Art",()->{
            MapArtStore26.clearSaved();note="Cleared stored map pixel images for this world/server";});
        y+=25;
        button(left,y,"Back",this::onClose);
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g,int mx,int my,float delta){
        super.extractRenderState(g,mx,my,delta);
        g.centeredText(this.font,Component.literal("Map Tooltip / Map Art"),this.width/2,5,0xffffffff);
        g.centeredText(this.font,Component.literal(
            this.font.plainSubstrByWidth(note,this.width-14)),this.width/2,26,0xffeeeeee);
        g.centeredText(this.font,Component.literal("Unmarked terrain maps are NOT assumed to be artwork."),
            this.width/2,Math.max(150,this.height-24),0xffaaffff);
    }
    @Override public void onClose(){this.minecraft.gui.setScreen(parent);}
}

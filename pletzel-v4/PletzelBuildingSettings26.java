package net.pletzel.schematica;

import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/**
 * Separate 720p-safe settings page: original Schematica controls and Done
 * remain on the primary screen without being covered by extra toggle rows.
 */
public final class PletzelBuildingSettings26 extends Screen {
    private final Screen parent;
    private String note="Only actual vanilla right-clicks can place blocks. OFF by default.";
    public PletzelBuildingSettings26(Screen parent) {
        super(Component.literal("Litematica Building Settings"));this.parent=parent;
    }
    private void add(int x,int y,String label,Runnable action) {
        this.addRenderableWidget(Button.builder(Component.literal(label),b->action.run())
            .bounds(x,y,150,20).build());
    }
    private void option(int x,int y,String label,net.minecraft.client.OptionInstance<Boolean> value) {
        this.addRenderableWidget(Button.builder(
            Component.literal(label+": "+(value.get()?"ON":"OFF")),
            b->{
                boolean changed=!value.get();value.set(changed);
                this.minecraft.options.save();
                b.setMessage(Component.literal(label+": "+(changed?"ON":"OFF")));
                note="Saved "+label+": "+(changed?"ON":"OFF");
                System.out.println("[PletzelBuildSettings] "+label+"="+changed);
            }).bounds(x,y,150,20).build());
    }
    @Override protected void init() {
        int left=this.width/2-154,right=this.width/2+4;
        int y=Math.max(45,Math.min(52,this.height-155));
        option(left,y,"Easy Place",this.minecraft.options.pletzelEasyPlace);
        this.addRenderableWidget(Button.builder(
            Component.literal("Mode: "+(this.minecraft.options.pletzelEasyPlaceHover.get()?"Hover Auto-Place":"Hold to Place")),
            b->{
                boolean hover=!this.minecraft.options.pletzelEasyPlaceHover.get();
                this.minecraft.options.pletzelEasyPlaceHover.set(hover);
                this.minecraft.options.save();
                b.setMessage(Component.literal("Mode: "+(hover?"Hover Auto-Place":"Hold to Place")));
                note=hover?"Hover mode actively uses vanilla right-click at valid ghost targets":"Hold uses your custom Place Block key";
            }).bounds(right,y,150,20).build());
        y+=24;
        option(left,y,"Easy Pick",this.minecraft.options.pletzelEasyPick);
        option(right,y,"Chunk Rendering",this.minecraft.options.pletzelChunkRendering);
        y+=24;
        option(left,y,"Incremental Mesh",this.minecraft.options.pletzelIncrementalMesh);
        option(right,y,"Wrong Highlight",this.minecraft.options.pletzelWrongHighlight);
        y+=24;
        add(left,y,"Distance: Follow MC",()->note="Uses actual Minecraft render-distance: "+
            this.minecraft.options.getEffectiveRenderDistance()+" chunks");
        add(right,y,"Wrong Color: Red",()->note="All original expected-model faces receive the red mismatch tint");
        y+=24;
        add(left,y,"Map Art Settings",()->this.minecraft.gui.setScreen(new PletzelMapArtSettings26(this)));
        add(right,y,"Back to Litematica",this::onClose);
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g,int mx,int my,float delta) {
        super.extractRenderState(g,mx,my,delta);
        g.centeredText(this.font,Component.literal("Litematica / Easy Place"),this.width/2,5,0xffffffff);
        g.centeredText(this.font,Component.literal(
            this.font.plainSubstrByWidth(note,Math.max(80,this.width-14))),this.width/2,26,0xffdddddd);
        g.centeredText(this.font,Component.literal(
            "Hover placement never bypasses vanilla reach or support faces."),
            this.width/2,Math.max(174,this.height-22),0xffaaffff);
    }
    @Override public void onClose() {this.minecraft.gui.setScreen(parent);}
}

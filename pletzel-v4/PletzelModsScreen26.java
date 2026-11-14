package net.pletzel.schematica;

import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Separate native Mods hub: no map settings are embedded in Schematica. */
public final class PletzelModsScreen26 extends Screen {
    private final Screen parent;
    public PletzelModsScreen26(Screen parent) {
        super(Component.literal("Pletzel Mods"));
        this.parent=parent;
    }
    @Override protected void init() {
        System.out.println("[PletzelModsMenu] OPEN");
        int w=Math.min(170,Math.max(80,this.width-30));
        int x=this.width/2-w/2;
        int top=Math.max(48,Math.min(66,this.height-160));
        this.addRenderableWidget(Button.builder(Component.literal("Schematica / Litematica"),
            b->this.minecraft.gui.setScreen(new SchematicaScreen(this)))
            .bounds(x,top,w,20).build());
        this.addRenderableWidget(Button.builder(Component.literal("Map Tooltips"),
            b->this.minecraft.gui.setScreen(new PletzelMapArtSettings26(this)))
            .bounds(x,top+30,w,20).build());
        this.addRenderableWidget(Button.builder(Component.literal("Done"),b->onClose())
            .bounds(x,Math.max(top+70,this.height-28),w,20).build());
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g,int mx,int my,float delta){
        super.extractRenderState(g,mx,my,delta);
        g.centeredText(this.font,Component.literal("Pletzel Mods"),this.width/2,12,0xffffffff);
        g.centeredText(this.font,Component.literal("Independent mod settings"),
            this.width/2,30,0xffaaffff);
    }
    @Override public void onClose(){this.minecraft.gui.setScreen(parent);}
}

package net.pletzel.maptooltip;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTooltipComponent;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.client.renderer.state.MapRenderState;
import net.minecraft.resources.Identifier;
import net.minecraft.world.level.saveddata.maps.MapId;
import net.minecraft.world.level.saveddata.maps.MapItemSavedData;

/** Original vanilla map pixels with optional scoped durable art fallback.
 * Not every terrain map is art. Unmarked maps and explorer maps have no
 * special artwork preview; mark a map as art using Map Art Settings.
 */
public final class MapTooltipClientComponent implements ClientTooltipComponent {
    private static final Identifier BACKGROUND=Identifier.withDefaultNamespace("textures/map/map_background.png");
    private final MapId id;
    private final boolean explorer;
    public MapTooltipClientComponent(MapId id,boolean explorer) {
        this.id=id;this.explorer=explorer;
    }
    private boolean permitted() {
        Minecraft mc=Minecraft.getInstance();
        if(mc==null||mc.level==null||mc.options==null)return false;
        MapItemSavedData live=mc.level.getMapData(id);
        return MapArtStore26.canPreview(id,explorer,live);
    }
    private MapItemSavedData current() {
        if(!permitted())return null;
        Minecraft mc=Minecraft.getInstance();
        MapItemSavedData live=mc.level.getMapData(id);
        if(live!=null&&live.colors!=null&&live.colors.length==128*128) {
            MapArtStore26.observe(id,live);
            return live;
        }
        return MapArtStore26.cachedData(id);
    }
    @Override public int getHeight(Font font) {
        return permitted()?66:0;
    }
    @Override public int getWidth(Font font) {
        return permitted()?66:0;
    }
    @Override public void extractImage(Font font,int x,int y,int width,int height,GuiGraphicsExtractor graphics) {
        if(!permitted())return;
        graphics.blit(RenderPipelines.GUI_TEXTURED,BACKGROUND,x,y-2,0.0F,0.0F,66,66,66,66);
        MapItemSavedData data=current();
        if(data==null) {
            graphics.text(font,"Map #"+id.id(),x+6,y+16,0xffeeeeee);
            graphics.text(font,"Awaiting map art",x+2,y+30,0xffffd49b);
            return;
        }
        graphics.pose().pushMatrix();
        try {
            graphics.pose().translate(x+4.0F,y+2.0F);
            graphics.pose().scale(.45F,.45F);
            MapRenderState state=new MapRenderState();
            Minecraft.getInstance().getMapRenderer().extractRenderState(id,data,state);
            graphics.map(state);
        } finally {
            graphics.pose().popMatrix();
        }
    }
}

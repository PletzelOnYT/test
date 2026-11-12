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
import org.jspecify.annotations.Nullable;

/**
 * A real (never fabricated) 128x128 filled-map preview.
 *
 * Always reserves its complete 66x66 tooltip box, including while the client
 * waits for the map packet. The previous implementation returned width and
 * height 0 before map data arrived; a tooltip could disappear while hovered.
 * The actual pixels and decorations are rendered by vanilla MapRenderer and
 * cached by vanilla MapTextureManager using the real MapId and packet updates.
 */
public final class MapTooltipClientComponent implements ClientTooltipComponent {
    private static final Identifier MAP_BACKGROUND =
        Identifier.withDefaultNamespace("textures/map/map_background.png");
    private final MapId id;

    public MapTooltipClientComponent(final MapId id) {
        this.id=id;
    }

    private @Nullable MapItemSavedData currentMapData() {
        Minecraft mc=Minecraft.getInstance();
        return mc.level==null ? null : mc.level.getMapData(id);
    }

    @Override
    public int getHeight(final Font font) {
        // Never collapse the active tooltip while waiting for map data.
        return 66;
    }

    @Override
    public int getWidth(final Font font) {
        return 66;
    }

    @Override
    public void extractImage(final Font font, final int x, final int y,
                             final int width, final int height,
                             final GuiGraphicsExtractor graphics) {
        graphics.blit(RenderPipelines.GUI_TEXTURED, MAP_BACKGROUND,
            x,y-2,0.0F,0.0F,66,66,66,66);
        MapItemSavedData data=currentMapData();
        if (data==null || data.colors==null || data.colors.length!=128*128) {
            graphics.text(font,"Map #"+id.id(),x+6,y+18,0xffeeeeee);
            graphics.text(font,"No map data",x+6,y+31,0xffffd49b);
            return;
        }

        graphics.pose().pushMatrix();
        try {
            graphics.pose().translate(x+4.0F,y+2.0F);
            graphics.pose().scale(0.45F,0.45F);
            MapRenderState state=new MapRenderState();
            Minecraft.getInstance().getMapRenderer().extractRenderState(id,data,state);
            graphics.map(state);
        } finally {
            graphics.pose().popMatrix();
        }
    }
}

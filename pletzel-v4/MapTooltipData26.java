package net.pletzel.maptooltip;

import java.util.Locale;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.inventory.tooltip.TooltipComponent;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.MapDecorations;
import net.minecraft.world.level.saveddata.maps.MapDecorationTypes;
import net.minecraft.world.level.saveddata.maps.MapId;

/**
 * Common-side map identity and conservative explorer-map metadata.
 * No Minecraft client renderer classes enter the integrated server.
 */
public record MapTooltipData(MapId mapId, boolean explorer) implements TooltipComponent {
    public static boolean isExplorer(ItemStack stack) {
        // Custom-titled map artwork is not a navigation map merely because
        // its title contains "treasure" or "village". Prefer known vanilla
        // explorer-item names and genuine map decoration components.
        String name=stack.getHoverName().getString().toLowerCase(Locale.ROOT);
        if(!stack.has(DataComponents.CUSTOM_NAME) &&
           (name.contains("explorer map")||name.contains("treasure map")||
            name.contains("buried treasure")||name.contains("structure locator map")))
            return true;
        MapDecorations data=stack.getOrDefault(DataComponents.MAP_DECORATIONS,MapDecorations.EMPTY);
        for(MapDecorations.Entry entry:data.decorations().values()) {
            if(entry.type().is(MapDecorationTypes.WOODLAND_MANSION)||
               entry.type().is(MapDecorationTypes.OCEAN_MONUMENT)||
               entry.type().is(MapDecorationTypes.RED_X)) return true;
        }
        return false;
    }
}

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
        String name=stack.getHoverName().getString().toLowerCase(Locale.ROOT);
        if(name.contains("explorer")||name.contains("treasure")||
           name.contains("woodland")||name.contains("monument")||
           name.contains("village")||name.contains("structure")) return true;
        MapDecorations data=stack.getOrDefault(DataComponents.MAP_DECORATIONS,MapDecorations.EMPTY);
        for(MapDecorations.Entry entry:data.decorations().values()) {
            if(entry.type().is(MapDecorationTypes.WOODLAND_MANSION)||
               entry.type().is(MapDecorationTypes.OCEAN_MONUMENT)||
               entry.type().is(MapDecorationTypes.RED_X)) return true;
        }
        return false;
    }
}

#!/usr/bin/env python3
"""Native Pletzel V4 port of VendoAU Map Tooltip 5.0.1 (Minecraft 26.1 Fabric).

Port of user-supplied MIT-labeled JAR. Neither Fabric nor its mixin framework
is required at runtime. The actual 26.2 map data, GPU texture manager and
vanilla MapRenderer are used. Run after the rest of the V4 source patches.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "engine")
base = root / "game/src/main/java"
map_item = base / "net/minecraft/world/item/MapItem.java"
tooltip_factory = base / "net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java"
port_dir = base / "net/pletzel/maptooltip"
port_dir.mkdir(parents=True, exist_ok=True)

def change(path, needle, replacement, context):
    src = path.read_text()
    assert src.count(needle) == 1, f"{context}: expected one anchor, got {src.count(needle)}"
    path.write_text(src.replace(needle, replacement, 1))

# The JAR's MapItemMixin replaces Item.getTooltipImage(). Preserve the same
# vanilla extension point without Fabric. The descriptor is COMMON code:
# server worker does not need to link any client GUI type.
needle = """   public MapItem(final Item.Properties properties) {
      super(properties);
   }
"""
addition = """   public MapItem(final Item.Properties properties) {
      super(properties);
   }

   // Native port of VendoAU's MIT MapTooltip 5.0.1 MapItemMixin.
   // Only FILLED_MAP items with MAP_ID create map tooltip data.
   @Override
   public java.util.Optional<net.minecraft.world.inventory.tooltip.TooltipComponent> getTooltipImage(final ItemStack stack) {
      MapId id = stack.get(DataComponents.MAP_ID);
      return id != null
         ? java.util.Optional.of(new net.pletzel.maptooltip.MapTooltipData(id))
         : java.util.Optional.empty();
   }
"""
change(map_item, needle, addition, "MapItem.getTooltipImage")

# Direct native component dispatch, equivalent to Fabric
# ClientTooltipComponentCallback registration. All other vanilla cases remain.
needle = """      return switch (component) {
         case BundleTooltip bundleTooltip -> new ClientBundleTooltip(bundleTooltip.contents());"""
addition = """      return switch (component) {
         case net.pletzel.maptooltip.MapTooltipData map -> new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId());
         case BundleTooltip bundleTooltip -> new ClientBundleTooltip(bundleTooltip.contents());"""
change(tooltip_factory, needle, addition, "ClientTooltipComponent dispatch")

data = '''package net.pletzel.maptooltip;

import net.minecraft.world.inventory.tooltip.TooltipComponent;
import net.minecraft.world.level.saveddata.maps.MapId;

/**
 * Server-safe map ID descriptor used in vanilla tooltip flow.
 * Native adaptation of VendoAU Map Tooltip 5.0.1 (MIT).
 * No client/renderer dependency is visible to the integrated server.
 */
public record MapTooltipData(MapId mapId) implements TooltipComponent {
}
'''

client = '''package net.pletzel.maptooltip;

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
 * Native 26.2 port of VendoAU Map Tooltip 5.0.1 by VendoAU (MIT).
 *
 * Rendering faithfully follows MapTooltip.java + GraphicsHelper.java from
 * the user-supplied v5.0.1+26.1 Fabric JAR:
 * 66x66 vanilla map frame, (0,-2) frame offset, (4,4) inner map offset,
 * 0.45x real MapRenderer, no generated/fake terrain or alternate textures.
 *
 * Uses vanilla client MapTextureManager's per-map cache and update invalidation.
 * No static cache holds ClientLevel/MapItemSavedData across world disconnects.
 */
public final class MapTooltipClientComponent implements ClientTooltipComponent {
   private static final Identifier MAP_BACKGROUND =
      Identifier.withDefaultNamespace("textures/map/map_background.png");
   private final MapId id;

   public MapTooltipClientComponent(final MapId id) {
      this.id = id;
   }

   private @Nullable MapItemSavedData currentMapData() {
      Minecraft mc = Minecraft.getInstance();
      return mc.level == null ? null : mc.level.getMapData(this.id);
   }

   @Override
   public int getHeight(final Font font) {
      // Never reserve an empty image slot if the server has not delivered map
      // colors. There is intentionally no fabricated terrain fallback.
      return currentMapData() == null ? 0 : 66;
   }

   @Override
   public int getWidth(final Font font) {
      return currentMapData() == null ? 0 : 66;
   }

   @Override
   public void extractImage(final Font font, final int x, final int y,
                            final int width, final int height,
                            final GuiGraphicsExtractor graphics) {
      MapItemSavedData data = currentMapData();
      if (data == null) {
         return;
      }

      // Same background texture, GUI dimensions and offsets as the JAR.
      graphics.blit(RenderPipelines.GUI_TEXTURED, MAP_BACKGROUND,
         x, y - 2, 0.0F, 0.0F, 66, 66, 66, 66);

      graphics.pose().pushMatrix();
      try {
         graphics.pose().translate(x + 4.0F, y + 2.0F);
         graphics.pose().scale(0.45F, 0.45F);
         MapRenderState state = new MapRenderState();
         Minecraft.getInstance().getMapRenderer().extractRenderState(this.id, data, state);
         graphics.map(state);
      } finally {
         graphics.pose().popMatrix();
      }
   }
}
'''
for name, content in [("MapTooltipData.java",data),
                      ("MapTooltipClientComponent.java",client)]:
    file = port_dir / name
    assert not file.exists(), f"{file} already exists; avoid duplicate port"
    file.write_text(content)

factory = tooltip_factory.read_text()
item = map_item.read_text()
assert item.count("new net.pletzel.maptooltip.MapTooltipData(id)") == 1
assert factory.count("MapTooltipClientComponent(map.mapId())") == 1
assert client.count("graphics.map(state)") == 1
assert client.count("scale(0.45F, 0.45F)") == 1
assert client.count("currentMapData()") == 4
print("Map Tooltip 5.0.1 native Java port patched into Minecraft 26.2.")
print("Preserved Item.getTooltipImage, ClientTooltipComponent mapping, vanilla map renderer and cache.")
print("Map data missing: image omitted without guessed colors or crash.")

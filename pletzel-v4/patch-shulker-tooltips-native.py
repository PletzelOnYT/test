#!/usr/bin/env python3
"""Pletzel V4 native Shulker Box Tooltip, map toggle, and persisted settings.

Apply AFTER the existing native Map Tooltip port and active-input-mode patch.
The Fabric Shulker Box Tooltip 5.4.3+26.2 JAR was inspected for its provider,
rendering and color semantics. This is a focused MIT-licensed adaptation using
the existing vanilla 26.2 container component and shulker GUI texture.
No Fabric runtime, server requests, NBT edits, or GUI overlays are added.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
game=root/"game/src/main/java"
item=game/"net/minecraft/world/item/ItemStack.java"
factory=game/"net/minecraft/client/gui/screens/inventory/tooltip/ClientTooltipComponent.java"
graphics=game/"net/minecraft/client/gui/GuiGraphicsExtractor.java"
options=game/"net/minecraft/client/Options.java"
controls=game/"net/minecraft/client/gui/screens/options/controls/ControlsScreen.java"
en=root/"game/src/main/resources/assets/minecraft/lang/en_us.json"
dest=game/"net/pletzel/shulkertooltip"
dest.mkdir(parents=True,exist_ok=True)

def swap(file, old, new, label):
    text=file.read_text()
    count=text.count(old)
    assert count==1, f"{label}: expected one exact source anchor; found {count}"
    file.write_text(text.replace(old,new,1))

# The REAL vanilla 26.2 shulker's ItemStack holds DataComponents.CONTAINER;
# ItemContainerContents is immutable and preserves sparse slot indexes.
# This descriptor is server-safe; rendering code never enters server classes.
old="""   public Optional<TooltipComponent> getTooltipImage() {
      return this.getItem().getTooltipImage(this);
   }"""
new="""   public Optional<TooltipComponent> getTooltipImage() {
      if (!this.isEmpty()
         && this.getItem() instanceof BlockItem blockItem
         && blockItem.getBlock() instanceof net.minecraft.world.level.block.ShulkerBoxBlock shulkerBlock) {
         net.minecraft.world.item.component.ItemContainerContents contents =
            this.getOrDefault(DataComponents.CONTAINER, net.minecraft.world.item.component.ItemContainerContents.EMPTY);
         return Optional.of(new net.pletzel.shulkertooltip.ShulkerTooltipData(
            contents, shulkerBlock.getColor(), this.getHoverName()));
      }
      return this.getItem().getTooltipImage(this);
   }"""
swap(item,old,new,"ItemStack native filled shulker hook")

old="""         case net.pletzel.maptooltip.MapTooltipData map -> new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId());"""
new="""         case net.pletzel.shulkertooltip.ShulkerTooltipData shulker ->
            new net.pletzel.shulkertooltip.ShulkerTooltipClientComponent(shulker);
         case net.pletzel.maptooltip.MapTooltipData map -> new net.pletzel.maptooltip.MapTooltipClientComponent(map.mapId());"""
swap(factory,old,new,"Native 26.2 tooltip client dispatch")

# Central *client GUI* feature switches, not common ItemStack/MapItem switches.
# Works for all inventory tooltip call sites using normal TooltipComponent.
old="""      optionalImage.ifPresent(image -> components.add(components.isEmpty() ? 0 : 1, ClientTooltipComponent.create(image)));"""
new="""      optionalImage.filter(image ->
         !(image instanceof net.pletzel.maptooltip.MapTooltipData && !this.minecraft.options.pletzelMapTooltip().get())
         && !(image instanceof net.pletzel.shulkertooltip.ShulkerTooltipData && !this.minecraft.options.pletzelShulkerTooltip().get())
      ).ifPresent(image -> components.add(components.isEmpty() ? 0 : 1, ClientTooltipComponent.create(image)));"""
swap(graphics,old,new,"Both global native tooltip switches")

# Both settings are the same persistent OptionInstance mechanism as native
# Controls->Input Mode. Defaults are ON. No localStorage hack.
old="""   private final OptionInstance<Integer> pletzelInputMode = new OptionInstance<>("""
new="""   private final OptionInstance<Boolean> pletzelMapTooltip =
      OptionInstance.createBoolean("options.pletzelMapTooltip", true);
   private final OptionInstance<Boolean> pletzelShulkerTooltip =
      OptionInstance.createBoolean("options.pletzelShulkerTooltip", true);
   private final OptionInstance<Integer> pletzelInputMode = new OptionInstance<>("""
swap(options,old,new,"persistent tooltip options fields")
old="""   public OptionInstance<Integer> pletzelInputMode() {
      return this.pletzelInputMode;
   }"""
new="""   public OptionInstance<Integer> pletzelInputMode() {
      return this.pletzelInputMode;
   }

   public OptionInstance<Boolean> pletzelMapTooltip() {
      return this.pletzelMapTooltip;
   }

   public OptionInstance<Boolean> pletzelShulkerTooltip() {
      return this.pletzelShulkerTooltip;
   }"""
swap(options,old,new,"persistent tooltip option getters")
old='      access.process("pletzelInputMode", this.pletzelInputMode);'
new='''      access.process("pletzelInputMode", this.pletzelInputMode);
      access.process("pletzelMapTooltip", this.pletzelMapTooltip);
      access.process("pletzelShulkerTooltip", this.pletzelShulkerTooltip);'''
swap(options,old,new,"persist both toggle values across restart")

# Touch and desktop Controls screens expose both settings in the native menu.
# Input Mode and all previous settings remain in their existing positions.
s=controls.read_text()
assert s.count("options.pletzelInputMode(),")==2, "Both touch and desktop Controls variants must exist"
touch="""            options.pletzelInputMode(),
            options.touchControls(),"""
assert s.count(touch)==1, "Touch Controls setting insertion point changed"
s=s.replace(touch,"""            options.pletzelInputMode(),
            options.pletzelMapTooltip(),
            options.pletzelShulkerTooltip(),
            options.touchControls(),""",1)
desktop="""         options.pletzelInputMode(),
         options.touchControls(),"""
assert s.count(desktop)==1, "Desktop Controls setting insertion point changed"
s=s.replace(desktop,"""         options.pletzelInputMode(),
         options.pletzelMapTooltip(),
         options.pletzelShulkerTooltip(),
         options.touchControls(),""",1)
controls.write_text(s)

old='  "options.pletzelInputMode": "Input Mode",'
new='''  "options.pletzelMapTooltip": "Map Tooltip",
  "options.pletzelShulkerTooltip": "Shulker Box Tooltip",
  "options.pletzelInputMode": "Input Mode",'''
swap(en,old,new,"native English option labels")

descriptor="""package net.pletzel.shulkertooltip;

import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.tooltip.TooltipComponent;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.component.ItemContainerContents;
import org.jspecify.annotations.Nullable;

/**
 * Immutable clientbound item data only. No block entity or client GUI.
 * Native 26.2 adaptation of Shulker Box Tooltip by MisterPeModder (MIT).
 */
public record ShulkerTooltipData(
   ItemContainerContents contents,
   @Nullable DyeColor dyeColor,
   Component hoverName
) implements TooltipComponent {
}
"""

client="""package net.pletzel.shulkertooltip;

import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTooltipComponent;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.core.NonNullList;
import net.minecraft.resources.Identifier;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemContainerContents;

/**
 * Read-only 9x3 shulker preview, adapted from the MIT-licensed
 * Shulker Box Tooltip 5.4.3 by MisterPeModder and contributors.
 *
 * The 26.2 item uses DataComponents.CONTAINER; no NBT roundtrip, world
 * inventory mutation, server callback, or guessed contents is performed.
 * Identical to the vanilla GUI's slot coordinates and native item renderer.
 */
public final class ShulkerTooltipClientComponent implements ClientTooltipComponent {
   private static final Identifier SHULKER_TEXTURE =
      Identifier.withDefaultNamespace("textures/gui/container/shulker_box.png");
   private static final int WIDTH=176;
   private static final int HEIGHT=76;
   private static final int COLUMNS=9;
   private static final int SLOTS=27;
   private static final int MAX_DECODED=32;
   private final ShulkerTooltipData data;

   // Cache only 32 component snapshots; no server Level or BlockEntity
   // references. The immutable component is the exact cache key, preventing
   // contents from one shulker leaking into another. LRU is bounded.
   private static final Map<ItemContainerContents,ItemStack[]> DECODED =
      new LinkedHashMap<ItemContainerContents,ItemStack[]>(32,0.75f,true) {
         @Override
         protected boolean removeEldestEntry(final Map.Entry<ItemContainerContents,ItemStack[]> eldest) {
            return this.size() > MAX_DECODED;
         }
      };

   public ShulkerTooltipClientComponent(final ShulkerTooltipData data) {
      this.data = data;
   }

   private static ItemStack[] copiedSlots(final ItemContainerContents contents) {
      ItemStack[] found=DECODED.get(contents);
      if (found != null) {
         return found;
      }
      try {
         NonNullList<ItemStack> copied=NonNullList.withSize(SLOTS,ItemStack.EMPTY);
         contents.copyInto(copied);
         ItemStack[] items=new ItemStack[SLOTS];
         for(int index=0;index<SLOTS;index++) {
            items[index]=copied.get(index);
         }
         DECODED.put(contents,items);
         return items;
      } catch (RuntimeException invalid) {
         // A damaged or incompatible component must not crash the tooltip.
         return null;
      }
   }

   @Override
   public int getWidth(final Font font) {
      return WIDTH;
   }

   @Override
   public int getHeight(final Font font) {
      return HEIGHT;
   }

   @Override
   public void extractImage(final Font font,final int x,final int y,
                            final int width,final int height,final GuiGraphicsExtractor graphics) {
      ItemStack[] items=copiedSlots(this.data.contents());
      if(items==null) {
         return;
      }
      // Real vanilla 26.2 shulker inventory sprite, cropped above player slots.
      graphics.blit(RenderPipelines.GUI_TEXTURED, SHULKER_TEXTURE,
         x, y, 0.0F, 0.0F, WIDTH, HEIGHT, 256, 256);

      DyeColor color=this.data.dyeColor();
      int accent=color==null ? 0xFF9877AE : color.getTextureDiffuseColor();
      graphics.outline(x, y, WIDTH, HEIGHT, accent);
      graphics.fill(x+1,y+1,x+WIDTH-1,y+3,accent);

      // Original vanilla item name above remains part of the normal tooltip.
      // This is the matching in-container label, including custom names.
      if(font.width(this.data.hoverName())<=156) {
         graphics.text(font,this.data.hoverName(),x+8,y+6,0xFF404040,false);
      }

      for(int slot=0;slot<SLOTS;slot++) {
         ItemStack held=items[slot];
         if(held==null || held.isEmpty()) {
            continue;
         }
         int xx=x+8+(slot%COLUMNS)*18;
         int yy=y+18+(slot/COLUMNS)*18;
         graphics.item(held,xx,yy,slot);
         graphics.itemDecorations(font,held,xx,yy);
      }
   }
}
"""
for path,body in ((dest/"ShulkerTooltipData.java",descriptor),(dest/"ShulkerTooltipClientComponent.java",client)):
    assert not path.exists(),f"Refusing to overwrite existing source {path}"
    path.write_text(body)

assert 'PletzelSingleplayerWarningScreen' in (game/"net/minecraft/client/gui/screens/TitleScreen.java").read_text()
assert 'options.pletzelInputMode()' in controls.read_text()
assert 'MapTooltipData' in factory.read_text()
print("Native Shulker Box Tooltip 5.4.3 and Map Tooltip switch port added.")
print("27 genuine server-supplied slots, vanilla 26.2 shulker texture and item renderer.")
print("Both toggles persisted in existing Options and exposed via native Controls UI.")

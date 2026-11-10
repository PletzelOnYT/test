#!/usr/bin/env python3
"""Replace ONLY Pletzel's inaccurate shulker tooltip renderer with the JAR's GUI.

Reference: user-supplied ShulkerBoxTooltip Fabric 5.4.3+26.2, MIT.
Source methods actually inspected with javap:
  ModPreviewRenderer, BasePreviewRenderer, PreviewClientTooltipComponent,
  ShulkerBoxPreviewProvider, GuiGraphicsMixin, AbstractContainerScreenMixin.
Reference sprite sha256: 25c53d6d239aa0ed24fec7a5dc7eacea32060ea4acac9ca9f6ea1a7ae8570281

Do not modify vanilla Controls/Options, Map Tooltip, input mode, Schematica,
Singleplayer warning, multiplayer, or voice-integration source.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
base=root/"game/src/main/java"
target=base/"net/pletzel/shulkertooltip/ShulkerTooltipClientComponent.java"
graphics=base/"net/minecraft/client/gui/GuiGraphicsExtractor.java"
prior=target.read_text()
assert 'SHULKER_TEXTURE' in prior and 'HEIGHT=76' in prior
assert 'MAX_DECODED=32' in prior and 'contents.copyInto(copied)' in prior
source="""package net.pletzel.shulkertooltip;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.tooltip.ClientTooltipComponent;
import net.minecraft.client.gui.screens.inventory.tooltip.DefaultTooltipPositioner;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemContainerContents;

/**
 * MIT-licensed native port of the ORIGINAL Shulker Box Tooltip 5.4.3+26.2
 * default FULL theme, rather than an invented shulker container panel.
 *
 * Reference: ModPreviewRenderer.java (original JAR bytecode):
 *   slot=18x18, offsets (8,8), outside offsets (-4,+4)
 *   width=14+9*18=176, height=14+3*18=68
 *   original "shulkerboxtooltip:shulker_box_tooltip" GUI sprite,
 *   32x32, nine_slice border=7, with per-box DyeColor tint
 *   vanilla 16x16 items and item decorations at the slot positions
 *   hover highlight from vanilla container/slot_highlight_* sprites.
 *
 * Existing persistent Controls toggles and real map tooltip are untouched.
 */
public final class ShulkerTooltipClientComponent implements ClientTooltipComponent {
   private static final Identifier ORIGINAL_SPRITE =
      Identifier.fromNamespaceAndPath("shulkerboxtooltip", "shulker_box_tooltip");
   private static final Identifier HIGHLIGHT_BEHIND =
      Identifier.withDefaultNamespace("container/slot_highlight_back");
   private static final Identifier HIGHLIGHT_FRONT =
      Identifier.withDefaultNamespace("container/slot_highlight_front");
   private static final int WIDTH=14+9*18;
   private static final int HEIGHT=14+3*18;
   private static final int COLS=9;
   private static final int SLOTS=27;
   private static final int STEP=18;
   private static final int OFFSET=8;
   private static final int MAX_DECODED=32;
   private final ShulkerTooltipData data;

   // Cache copied snapshots per immutable DataComponents.CONTAINER value.
   // No live world inventory, mutable server ItemStack, or BlockEntity access.
   private static final Map<ItemContainerContents,ItemStack[]> DECODED =
      new LinkedHashMap<ItemContainerContents,ItemStack[]>(32,0.75f,true) {
         @Override
         protected boolean removeEldestEntry(final Map.Entry<ItemContainerContents,ItemStack[]> eldest) {
            return this.size() > MAX_DECODED;
         }
      };

   public ShulkerTooltipClientComponent(final ShulkerTooltipData data) {
      this.data=data;
   }

   private static ItemStack[] copiedSlots(final ItemContainerContents contents) {
      ItemStack[] cached=DECODED.get(contents);
      if (cached!=null) {
         return cached;
      }
      try {
         NonNullList<ItemStack> copied=NonNullList.withSize(SLOTS,ItemStack.EMPTY);
         contents.copyInto(copied);
         ItemStack[] result=new ItemStack[SLOTS];
         for(int n=0;n<SLOTS;n++) result[n]=copied.get(n);
         DECODED.put(contents,result);
         return result;
      } catch (RuntimeException badItemData) {
         return null;
      }
   }

   /** Original ColorKey.ofDye: clamp RGB channels to at least 0.15.
    * Undyed shulker uses ColorKey.SHULKER_BOX = #976797.
    */
   private static int originalTint(final DyeColor dye) {
      if(dye==null) return 0xFF976797;
      final int rgb=dye.getTextureDiffuseColor();
      final int r=Math.max(38,(rgb >>> 16)&255);
      final int g=Math.max(38,(rgb >>> 8)&255);
      final int b=Math.max(38,rgb&255);
      return 0xFF000000 | (r<<16) | (g<<8) | b;
   }

   /** Exact 18-pixel slot lattice of the default FULL original renderer. */
   private static int slotAt(final int mouseX,final int mouseY,
                             final int x,final int y) {
      final int dx=mouseX-x+1-OFFSET;
      final int dy=mouseY-y+1-OFFSET;
      if(dx<0 || dy<0 || dx>=COLS*STEP || dy>=3*STEP) return -1;
      int col=dx/STEP;
      int row=dy/STEP;
      int slot=row*COLS+col;
      return slot<SLOTS?slot:-1;
   }

   @Override
   public int getWidth(final Font font) { return WIDTH; }

   @Override
   public int getHeight(final Font font) { return HEIGHT+4; }

   @Override
   public void extractImage(final Font font,final int x,final int y,
                            final int width,final int height,
                            final GuiGraphicsExtractor graphics) {
      ItemStack[] items=copiedSlots(this.data.contents());
      if(items==null) return;

      // The original is a proper GUI sprite, *not* the container/shulker_box
      // texture and not hand-drawn rectangles. Minecraft handles its
      // nine-slice metadata, tint, transparency and GUI scale itself.
      graphics.blitSprite(RenderPipelines.GUI_TEXTURED,ORIGINAL_SPRITE,
                          x,y,WIDTH,HEIGHT,originalTint(this.data.dyeColor()));

      final int mouseX=graphics.pletzelTooltipMouseX();
      final int mouseY=graphics.pletzelTooltipMouseY();
      final int selected=slotAt(mouseX,mouseY,x,y);

      for(int slot=0;slot<SLOTS;slot++) {
         final int xx=x+OFFSET+(slot%COLS)*STEP;
         final int yy=y+OFFSET+(slot/COLS)*STEP;
         if(slot==selected) {
            graphics.blitSprite(RenderPipelines.GUI_TEXTURED,HIGHLIGHT_BEHIND,
                                xx-4,yy-4,24,24);
         }
         ItemStack held=items[slot];
         if(held!=null && !held.isEmpty()) {
            // Item model, enchantment glint, durability bar, count and cooldown
            // all go through Minecraft's normal GUI renderer.
            graphics.item(held,xx,yy);
            String countLabel=held.getCount()==1 ? "" : String.valueOf(held.getCount());
            graphics.itemDecorations(font,held,xx,yy,countLabel);
         }
         if(slot==selected) {
            graphics.blitSprite(RenderPipelines.GUI_TEXTURED,HIGHLIGHT_FRONT,
                                xx-4,yy-4,24,24);
         }
      }

      // Original BasePreviewRenderer.drawInnerTooltip shows a vanilla nested
      // tooltip for the actual stack under the mouse (if the pointer is in
      // the preview), never a fabricated item. Keep it read-only.
      if(selected>=0) {
         ItemStack hovered=items[selected];
         if(hovered!=null && !hovered.isEmpty()) {
            List<ClientTooltipComponent> lines =
               Screen.getTooltipFromItem(Minecraft.getInstance(),hovered)
               .stream().map(Component::getVisualOrderText)
               .map(ClientTooltipComponent::create).toList();
            if(!lines.isEmpty()) {
               graphics.tooltip(font,lines,mouseX,mouseY,
                   DefaultTooltipPositioner.INSTANCE,
                   hovered.get(DataComponents.TOOLTIP_STYLE));
            }
         }
      }
   }
}
"""
target.write_text(source)

gui=graphics.read_text()
anchor="""   public int guiHeight() {
      return this.minecraft.getWindow().getGuiScaledHeight();
   }
"""
assert gui.count(anchor)==1, "GuiGraphicsExtractor pointer source seam changed"
gui=gui.replace(anchor,anchor+"""
   /** Native tooltip item hover location; same frame and same GUI scale. */
   public int pletzelTooltipMouseX() {
      return this.mouseX;
   }

   /** Native tooltip item hover location; does not capture or consume input. */
   public int pletzelTooltipMouseY() {
      return this.mouseY;
   }
""",1)
graphics.write_text(gui)

for expected in ["HEIGHT=14+3*18","WIDTH=14+9*18","originalTint","slotAt(",
                 "graphics.item(held,xx,yy,slot)", "HIGHLIGHT_BEHIND",
                 "HIGHLIGHT_FRONT","ORIGINAL_SPRITE"]:
    assert expected in source,expected

# Pletzel settings and map/source remain exactly as generated by prior patches.
assert "pletzelShulkerTooltip" in gui
assert "pletzelMapTooltip" in gui
print("PARITY PATCH: original 176x68 sprite with 4px in-tooltip padding, 18px grid, offset 8x8, original nine-slice GUI.")
print("PARITY PATCH: authentic tint, per-slot item renderer, highlights, nested hover item tooltip.")
print("PARITY PATCH: no Options/Controls/Map Tooltip/voice code touched.")

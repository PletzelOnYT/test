#!/usr/bin/env python3
"""Add a native Minecraft Screen gate before TitleScreen's Singleplayer action.

Source-only patch against the pinned Pletzel V4 26.2 Java engine. The entire
original Singleplayer startup handler is preserved in a dedicated method and
is called only after the player explicitly chooses Continue Anyway.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "engine")
screens = root / "game/src/main/java/net/minecraft/client/gui/screens"
title_path = screens / "TitleScreen.java"
target = screens / "PletzelSingleplayerWarningScreen.java"

src = title_path.read_text()
anchor = 'Button.builder(Component.translatable("menu.singleplayer"), var1 -> {'
assert src.count(anchor) == 1, "Singleplayer menu callback changed; refuse unreviewed patch"
start = src.index(anchor)
end = src.index('})\n            .bounds(', start)
old = src[start:end+2]
assert old.count('new SelectWorldScreen(this)') == 1, "Must preserve world-selection path"
assert old.count('prewarmServerWorker()') == 1, "Must preserve worker startup behavior"
assert old.count('EaglerIntegratedServerStartupScreen(this)') == 1, "Must preserve existing worker startup screen"
assert src.count('   private int createNormalMenuOptions(') == 1
original_body = old[len(anchor):-2].rstrip()
method = (
    "   /** Called ONLY when a player confirms the in-game Singleplayer warning. */\n"
    "   public void openSingleplayerAfterWarning() {" + original_body + "\n"
    "   }\n\n"
)
src = src[:start] + (
    'Button.builder(Component.translatable("menu.singleplayer"), '
    'var1 -> this.minecraft.gui.setScreen(new PletzelSingleplayerWarningScreen(this)))'
) + src[end+2:]
src = src.replace(
    '   private int createNormalMenuOptions(',
    method + '   private int createNormalMenuOptions(',
    1,
)
assert src.count('new PletzelSingleplayerWarningScreen(this)') == 1
assert src.count('new SelectWorldScreen(this)') == 1
assert src.count('openSingleplayerAfterWarning()') == 1
title_path.write_text(src)

warning = r'''package net.minecraft.client.gui.screens;

import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.FittingMultiLineTextWidget;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.util.FormattedCharSequence;

/**
 * Temporary native in-game warning for the known broken integrated server.
 * Uses the actual Screen, native menu background, Minecraft font,
 * buttons, focus and input dispatch. Never starts a world without consent.
 */
public final class PletzelSingleplayerWarningScreen extends Screen {
   private static final Component TITLE = Component.literal("⚠ SINGLEPLAYER WARNING ⚠")
      .withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD);
   private static final Component STATUS = Component.literal("Pletzel V4 — Singleplayer repairs in progress!")
      .withStyle(ChatFormatting.GREEN);
   private static final Component DESCRIPTION = createDescription();

   private final TitleScreen parent;
   private FittingMultiLineTextWidget messageWidget;
   private Button continueButton;
   private int panelLeft;
   private int panelWidth;
   private int titleY;
   private int messageY;
   private int messageHeight;
   private int statusY;

   public PletzelSingleplayerWarningScreen(final TitleScreen parent) {
      super(TITLE);
      this.parent = parent;
   }

   private static Component createDescription() {
      MutableComponent message = Component.literal(
         "Singleplayer is currently experiencing technical issues!")
         .withStyle(ChatFormatting.RED, ChatFormatting.BOLD);
      message.append(Component.literal(
         "\n\nSingleplayer is currently broken and may experience severe lag, "
         + "world-loading issues, missing chunks, or server stalls.")
         .withStyle(ChatFormatting.WHITE));
      message.append(Component.literal(
         "\n\nWe are actively working on fixing these problems.")
         .withStyle(ChatFormatting.YELLOW));
      message.append(Component.literal(
         "\n\nYou can still try Singleplayer, but gameplay may not work correctly.")
         .withStyle(ChatFormatting.WHITE));
      message.append(Component.literal(
         "\n\nThank you for your patience!")
         .withStyle(ChatFormatting.YELLOW));
      return message;
   }

   @Override
   public boolean isPauseScreen() {
      return false;
   }

   @Override
   public Component getNarrationMessage() {
      return TITLE.copy().append("\n").append(DESCRIPTION).append("\n").append(STATUS);
   }

   @Override
   protected void init() {
      this.panelWidth = Math.min(456, Math.max(140, this.width - 20));
      this.panelLeft = (this.width - this.panelWidth) / 2;
      int innerWidth = Math.max(120, this.panelWidth - 24);

      List<FormattedCharSequence> titleLines = this.font.split(TITLE, innerWidth);
      this.titleY = Math.max(12, Math.min(26, this.height / 10));
      int headerBottom = this.titleY + titleLines.size() * 10;
      int statusLines = this.font.split(STATUS, innerWidth).size();
      this.statusY = this.height - 9 - statusLines * 10;

      // Native Minecraft buttons remain fully accessible through tab, enter,
      // mouse click, hover and GUI focus at every supported GUI-scale setting.
      boolean stacked = this.width < 355;
      int buttonTop = this.statusY - (stacked ? 51 : 29);
      int availableWidth = Math.min(352, innerWidth);
      if (stacked) {
         int buttonWidth = Math.min(230, availableWidth);
         int buttonLeft = (this.width - buttonWidth) / 2;
         this.continueButton = this.addRenderableWidget(
            Button.builder(Component.literal("Continue Anyway"),
               button -> this.parent.openSingleplayerAfterWarning())
               .bounds(buttonLeft, buttonTop, buttonWidth, 20).build());
         this.addRenderableWidget(
            Button.builder(Component.literal("Back to Main Menu"), button -> this.onClose())
               .bounds(buttonLeft, buttonTop + 24, buttonWidth, 20).build());
      } else {
         int buttonWidth = (availableWidth - 8) / 2;
         int buttonLeft = (this.width - availableWidth) / 2;
         this.continueButton = this.addRenderableWidget(
            Button.builder(Component.literal("Continue Anyway"),
               button -> this.parent.openSingleplayerAfterWarning())
               .bounds(buttonLeft, buttonTop, buttonWidth, 20).build());
         this.addRenderableWidget(
            Button.builder(Component.literal("Back to Main Menu"), button -> this.onClose())
               .bounds(buttonLeft + buttonWidth + 8, buttonTop, buttonWidth, 20).build());
      }

      this.messageY = headerBottom + 7;
      this.messageHeight = Math.max(24, buttonTop - this.messageY - 8);
      this.messageWidget = this.addRenderableWidget(
         new FittingMultiLineTextWidget(
            this.panelLeft + 11, this.messageY,
            this.panelWidth - 22, this.messageHeight,
            DESCRIPTION, this.font)
      );
      this.messageWidget.minimizeHeight();
      this.setInitialFocus(this.continueButton);
   }

   @Override
   public void extractRenderState(
      final GuiGraphicsExtractor graphics, final int mouseX, final int mouseY, final float partialTick) {
      // The stock Screen extractor already paints vanilla's tiled dark menu
      // background. This restrained in-game panel provides readable contrast.
      int top = Math.max(5, this.titleY - 8);
      int bottom = this.height - 5;
      graphics.fill(this.panelLeft, top, this.panelLeft + this.panelWidth, bottom, 0xB71B1B1B);
      graphics.outline(this.panelLeft, top, this.panelWidth, bottom - top, 0xFF777777);
      graphics.fill(this.panelLeft + 1, top + 1, this.panelLeft + this.panelWidth - 1, top + 3, 0xFFFFAA00);

      int x = this.width / 2;
      int y = this.titleY;
      for (FormattedCharSequence line : this.font.split(TITLE, Math.max(120, this.panelWidth - 24))) {
         graphics.centeredText(this.font, line, x, y, 0xFFFFAA00);
         y += 10;
      }

      // Real Minecraft GUI widget rendering includes the standard button
      // textures, focus outlines, hover behavior and scrollable text on
      // compact Chromebook windows.
      super.extractRenderState(graphics, mouseX, mouseY, partialTick);

      y = this.statusY;
      for (FormattedCharSequence line : this.font.split(STATUS, Math.max(120, this.panelWidth - 24))) {
         graphics.centeredText(this.font, line, x, y, 0xFF55FF55);
         y += 10;
      }
   }

   @Override
   public void onClose() {
      this.minecraft.gui.setScreen(this.parent);
   }
}
'''
# The r''' wrapper above becomes literal Java content with correct escaped newlines.
target.write_text(warning)
assert warning.count("new FittingMultiLineTextWidget(") == 1
assert warning.count("openSingleplayerAfterWarning()") == 2
print("Patched TitleScreen: every Singleplayer click now opens the native warning")
print("Added PletzelSingleplayerWarningScreen.java with native GUI and ESC/back/continue behavior")

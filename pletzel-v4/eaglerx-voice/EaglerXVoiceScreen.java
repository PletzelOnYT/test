package net.lax1dude.eaglercraft.v1_8.voice;

import net.lax1dude.eaglercraft.v1_8.internal.PlatformEaglerVoice26;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractSliderButton;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.util.FormattedCharSequence;

/**
 * Native 26.2 Minecraft controls for official EaglerXServer voice support.
 * There is NO HTML overlay, PletzelVoice gateway or separate voice protocol.
 * This screen never requests microphone access without pressing Enable.
 */
public final class EaglerXVoiceScreen extends Screen {
   private final Screen parent;
   private final EaglerXVoiceClient26 voice;
   private int middle,top,menuWidth;

   public EaglerXVoiceScreen(final Screen parent,final EaglerXVoiceClient26 voice) {
      super(Component.literal("EaglercraftX Voice Chat"));
      this.parent=parent;
      this.voice=voice;
   }

   @Override
   public boolean isPauseScreen() {return false;}

   @Override
   protected void init() {
      this.middle=this.width/2;
      this.menuWidth=Math.min(326,Math.max(132,this.width-24));
      this.top=Math.max(34,(this.height-290)/2);
      int left=middle-menuWidth/2;
      int rowWidth=(menuWidth-6)/2;
      Button enable=this.addRenderableWidget(Button.builder(Component.literal(voice.userEnabled() ? "Disable Voice" : "Enable Voice"),
         button -> {voice.setEnabled(!voice.userEnabled());this.rebuildWidgets();})
         .bounds(left,top+20,menuWidth,20).build());
      enable.active=voice.userEnabled()||(voice.serverAllowed()&&voice.supported());

      this.addRenderableWidget(Button.builder(Component.literal(voice.muted()?"Unmute Microphone":"Mute Microphone"),
         b -> {voice.setMuted(!voice.muted());this.rebuildWidgets();})
         .bounds(left,top+44,rowWidth,20).build());
      this.addRenderableWidget(Button.builder(Component.literal(voice.voiceActivation()?"Voice Activation":"Push-to-Talk"),
         b -> {voice.setVoiceActivation(!voice.voiceActivation());this.rebuildWidgets();})
         .bounds(left+rowWidth+6,top+44,rowWidth,20).build());
      this.addRenderableWidget(Button.builder(Component.literal(voice.channel()==1?"Channel: Proximity":"Channel: Global"),
         b -> {voice.setChannel(voice.channel()==1?2:1);this.rebuildWidgets();})
         .bounds(left,top+68,menuWidth,20).build());
      this.addRenderableWidget(new AbstractSliderButton(left,top+93,menuWidth,20,
          Component.literal("Players Volume"),voice.volume()/1.5) {
         @Override protected void updateMessage() {
            this.setMessage(Component.literal("Players Volume: "+Math.round(this.value*150)+"%"));
         }
         @Override protected void applyValue() {voice.setVolume(this.value*1.5);this.updateMessage();}
      });
      this.addRenderableWidget(new AbstractSliderButton(left,top+117,menuWidth,20,
          Component.literal("Voice Sensitivity"),(voice.sensitivity()-0.01)/0.29) {
         @Override protected void updateMessage() {
            this.setMessage(Component.literal("Activation Sensitivity: "+Math.round((1-this.value)*100)+"%"));
         }
         @Override protected void applyValue() {voice.setSensitivity(0.01+this.value*0.29);this.updateMessage();}
      });
      this.addRenderableWidget(Button.builder(Component.literal("Done"),b -> this.onClose())
         .bounds(left,Math.min(this.height-28,top+204),menuWidth,20).build());
   }

   @Override
   public void extractRenderState(final GuiGraphicsExtractor graphics,final int mouseX,
                                   final int mouseY,final float partialTick) {
      int left=middle-menuWidth/2;
      graphics.fill(left-8,Math.max(4,top-20),left+menuWidth+8,
         Math.min(this.height-5,top+240),0xC6191919);
      graphics.outline(left-8,Math.max(4,top-20),menuWidth+16,
         Math.min(this.height-5,top+240)-Math.max(4,top-20),0xFF777777);
      graphics.centeredText(this.font,this.title,middle,top-13,0xFFFFAA00);
      super.extractRenderState(graphics,mouseX,mouseY,partialTick);
      Component status=Component.literal(voice.status());
      int yy=top+145;
      for(FormattedCharSequence line:this.font.split(status,menuWidth-10)) {
         graphics.centeredText(this.font,line,middle,yy,voice.serverAllowed()?0xFF55FF55:0xFFFF5555);
         yy+=10;
      }
      graphics.centeredText(this.font,"Peers: "+voice.peerCount()+" | Mic level: "+
         Math.round(PlatformEaglerVoice26.microphoneLevel()*100)+"%",middle,top+169,0xFFE0E0E0);
      graphics.centeredText(this.font,voice.transmitting()?"MIC TRANSMITTING":"Microphone idle / muted",
         middle,top+182,voice.transmitting()?0xFF55FF55:0xFFAAAAAA);
      graphics.centeredText(this.font,"WebRTC peers may learn your IP address",middle,
         Math.min(this.height-44,top+233),0xFFFFAA00);
      if(this.width>=210 && this.height>=310) {
         graphics.centeredText(this.font,"Configure voice keys under Options > Controls",
            middle,Math.min(this.height-34,top+245),0xFFAAAAAA);
      }
   }

   @Override public void onClose() {this.minecraft.gui.setScreen(parent);}
}

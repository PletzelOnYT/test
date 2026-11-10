#!/usr/bin/env python3
"""EXPERIMENTAL native Pletzel 26.2 voice GUI and browser adapter.

Run after the existing warning, input, map and shulker patches.
This DOES NOT implement Simple Voice Chat protocol or a server bridge.
It requires the companion PletzelVoice Paper plugin + signaling gateway.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'engine')
game=root/'game/src/main/java/net/minecraft/client'
base=root/'game/src/main/java/net/minecraft'
platforms={
    'teavm':root/'platform-teavm/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java',
    'lwjgl':root/'platform-lwjgl/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java',
    'shared':root/'platform/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java',
}

def swap(file, old, new, why):
    s=file.read_text()
    n=s.count(old)
    assert n==1,f'{why} expected 1 anchor, found {n}'
    file.write_text(s.replace(old,new,1))

def insert_before_final_brace(file,code):
    s=file.read_text()
    assert s.rstrip().endswith('}')
    file.write_text(s.rstrip()[:-1]+code+'\n}\n')

# Browser mic/WebRTC calls live behind an existing TeaVM platform adapter,
# with no org.teavm annotations in the shared/game code or local server class.
methods=[
 ('void','voiceConnect','String url, String token','"url", "token"','if(window.PletzelVoice)window.PletzelVoice.connect(url,token);',None),
 ('void','voiceDisconnect','','','if(window.PletzelVoice&&window.PletzelVoice.enabled())window.PletzelVoice.disconnect();',None),
 ('void','voiceSetPTT','boolean state','"state"','if(window.PletzelVoice)window.PletzelVoice.setPtt(state);',None),
 ('void','voiceYaw','float yaw','"yaw"','if(window.PletzelVoice)window.PletzelVoice.setYaw(yaw);',None),
 ('String','voiceStatus','','',"return window.PletzelVoice?window.PletzelVoice.status():'Browser voice unavailable';",'Voice unavailable on native desktop'),
 ('boolean','voiceEnabled','','','return !!(window.PletzelVoice&&window.PletzelVoice.enabled());',False),
 ('boolean','voiceMuted','','','return !window.PletzelVoice||window.PletzelVoice.muted();',True),
 ('boolean','voiceTransmitting','','','return !!(window.PletzelVoice&&window.PletzelVoice.transmitting());',False),
 ('boolean','voiceReady','','','return !!(window.PletzelVoice&&window.PletzelVoice.connected());',False),
 ('void','voiceMute','boolean state','"state"','if(window.PletzelVoice)(state?window.PletzelVoice.mute():window.PletzelVoice.unmute());',None),
 ('void','voiceMode','boolean vad','"vad"','if(window.PletzelVoice)window.PletzelVoice.setMode(vad?"voice":"ptt");',None),
 ('boolean','voiceIsVad','','','return !!(window.PletzelVoice&&window.PletzelVoice.mode()==="voice");',False),
 ('void','voiceCycleMic','','','if(window.PletzelVoice)window.PletzelVoice.cycleMic();',None),
 ('void','voiceCycleSpeaker','','','if(window.PletzelVoice)window.PletzelVoice.cycleSpeaker();',None),
 ('void','voiceTest','','','if(window.PletzelVoice)window.PletzelVoice.test();',None),
 ('float','voiceLevel','','','return window.PletzelVoice?window.PletzelVoice.microphoneLevel():0;',0),
 ('void','voiceSensitivity','float v','"v"','if(window.PletzelVoice)window.PletzelVoice.sensitivity(v);',None),
 ('void','voiceOthersVolume','float v','"v"','if(window.PletzelVoice)window.PletzelVoice.setOtherVolume(v);',None),
 ('void','voiceMicGain','float v','"v"','if(window.PletzelVoice)window.PletzelVoice.setMicrophoneGain(v);',None),
 ('void','voiceRange','int v','"v"','if(window.PletzelVoice)window.PletzelVoice.setMaxRange(v);',None),
 ('int','voiceServerRange','','','return window.PletzelVoice?window.PletzelVoice.range():48;',48),
]
for plat,file in platforms.items():
    if plat=='teavm':
        body='\n\t// Pletzel Voice (opt-in WebRTC transport; Java GUI, JS audio only).\n'
        for rt,name,args,jsargs,js,default in methods:
            body+='\t@JSBody('+('params = { '+jsargs+' }, ' if jsargs else '')+'script = '+repr(js).replace("'",'"')+')\n'
            # JSBody script string uses only single quotes inside most scripts.
            # Quote/escape correctly through standard JSON below.
            import json
            body=body[:body.rfind('\t@JSBody(')]+'\t@JSBody('+('params = { '+jsargs+' }, ' if jsargs else '')+'script = '+json.dumps(js)+')\n'
            body+=f'\tpublic static native {rt} {name}({args});\n\n'
    else:
        body='\n\t// Pletzel Voice: unavailable on non-browser runtimes.\n'
        for rt,name,args,jsargs,js,default in methods:
            if rt=='void': tail=''
            elif rt=='boolean':tail=f'return {str(default).lower()};'
            elif rt=='String':tail=f'return "{default}";'
            elif rt=='float':tail='return 0.0f;'
            else:tail=f'return {default};'
            body+=f'\tpublic static {rt} {name}({args}) {{ {tail} }}\n'
    insert_before_final_brace(file,body)

opts=game/'Options.java'
s=opts.read_text()
needle='   public final KeyMapping keyChat = new KeyMapping("key.chat", 84, KeyMapping.Category.MULTIPLAYER);'
assert s.count(needle)==1
s=s.replace(needle,'''   // Pletzel native browser voice. V opens menu, left Alt transmits in PTT mode.
   public final KeyMapping keyPletzelVoiceMenu = new KeyMapping("key.pletzelVoiceMenu", 86, KeyMapping.Category.MULTIPLAYER);
   public final KeyMapping keyPletzelVoicePTT = new KeyMapping("key.pletzelVoicePTT", 342, KeyMapping.Category.MULTIPLAYER);
'''+needle)
s=s.replace('            this.keyChat,','''            this.keyChat,
            this.keyPletzelVoiceMenu,
            this.keyPletzelVoicePTT,''',1)
assert s.count('this.keyPletzelVoiceMenu,')==1
opts.write_text(s)

mc=game/'Minecraft.java'
s=mc.read_text()
needle='''   private void handleKeybinds() {
      while (this.options.keyTogglePerspective.consumeClick()) {'''
replacement='''   private void handleKeybinds() {
      while (this.options.keyPletzelVoiceMenu.consumeClick()) {
         this.gui.setScreen(new net.pletzel.voice.PletzelVoiceScreen());
      }
      while (this.options.keyTogglePerspective.consumeClick()) {'''
assert s.count(needle)==1
s=s.replace(needle,replacement)
needle='''      this.clientTickCount++;
      if (this.level != null && !this.pause) {'''
replacement='''      this.clientTickCount++;
      if (net.lax1dude.eaglercraft.v1_8.minecraft.EaglerHosted.isActive()) {
         if (this.player == null || this.level == null || this.getCurrentServer() == null) {
            net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.voiceDisconnect();
         } else {
            net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.voiceSetPTT(this.options.keyPletzelVoicePTT.isDown());
            net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.voiceYaw(this.player.getYRot());
         }
      }
      if (this.level != null && !this.pause) {'''
assert s.count(needle)==1
s=s.replace(needle,replacement)
mc.write_text(s)

# Add native readable bindings in Minecraft key controls; do not replace Input Mode.
lang=root/'game/src/main/resources/assets/minecraft/lang/en_us.json'
s=lang.read_text();needle='  "key.chat": "Open Chat",'
assert s.count(needle)==1
s=s.replace(needle,'''  "key.pletzelVoiceMenu": "Pletzel Voice Menu",
  "key.pletzelVoicePTT": "Pletzel Push to Talk",
'''+needle)
lang.write_text(s)

screen=base/'client/gui/screens/PletzelVoiceScreen.java'
# Other custom screens in Pletzel live in the normal game source package.
voice=base/'../pletzel/voice/PletzelVoiceScreen.java'
# Correct class/package path under the same game java source root.
voice=root/'game/src/main/java/net/pletzel/voice/PletzelVoiceScreen.java'
voice.parent.mkdir(parents=True,exist_ok=True)
assert not voice.exists()
voice.write_text('''package net.pletzel.voice;

import net.lax1dude.eaglercraft.v1_8.internal.PlatformInput;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Native Minecraft 26.2 voice screen; actual audio stays in browser WebRTC. */
public final class PletzelVoiceScreen extends Screen {
   private static String lastUrl = "wss://voice.example.com/voice";
   private EditBox address;
   private EditBox token;
   private boolean voiceActivation;
   private float sensitivity = 0.055F;
   private float micGain = 1.0F;
   private float otherVolume = 1.0F;
   private int range = 48;

   public PletzelVoiceScreen() { super(Component.literal("Pletzel Voice Chat")); }

   @Override
   protected void init() {
      int x = this.width / 2;
      int left = x - 125;
      int top = Math.max(18, this.height / 2 - 145);
      this.address = this.addRenderableWidget(new EditBox(this.font,left,top+28,250,20,Component.literal("Voice gateway URL")));
      this.address.setMaxLength(180);
      this.address.setValue(lastUrl);
      this.token = this.addRenderableWidget(new EditBox(this.font,left,top+60,250,20,Component.literal("One-time token")));
      this.token.setMaxLength(100);
      this.token.setHint(Component.literal("Paste your in-game /pvoice token here"));
      this.addRenderableWidget(Button.builder(Component.literal("Enable + Connect"), b -> {
         lastUrl=this.address.getValue();
         PlatformInput.voiceConnect(lastUrl,this.token.getValue());
         this.token.setValue("");
      }).bounds(left,top+88,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Disconnect"), b -> PlatformInput.voiceDisconnect())
         .bounds(x+3,top+88,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Mute / Unmute"), b -> PlatformInput.voiceMute(!PlatformInput.voiceMuted()))
         .bounds(left,top+112,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("PTT / Voice Detect"), b -> {
         voiceActivation=!voiceActivation;
         PlatformInput.voiceMode(voiceActivation);
      }).bounds(x+3,top+112,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Cycle Microphone"), b -> PlatformInput.voiceCycleMic())
         .bounds(left,top+136,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Cycle Speaker"), b -> PlatformInput.voiceCycleSpeaker())
         .bounds(x+3,top+136,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Sensitivity -"), b -> {
         sensitivity=Math.max(0.01F,sensitivity-0.01F);PlatformInput.voiceSensitivity(sensitivity);
      }).bounds(left,top+160,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Sensitivity +"), b -> {
         sensitivity=Math.min(0.3F,sensitivity+0.01F);PlatformInput.voiceSensitivity(sensitivity);
      }).bounds(x+3,top+160,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Mic gain - / +"), b -> {
         micGain=micGain>=2.0F?0.5F:micGain+0.25F;
         PlatformInput.voiceMicGain(micGain);
      }).bounds(left,top+184,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Others volume - / +"), b -> {
         otherVolume=otherVolume>=2.0F?0.5F:otherVolume+0.25F;
         PlatformInput.voiceOthersVolume(otherVolume);
      }).bounds(x+3,top+184,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Range: Server limited"), b -> {
         range=range<=16?32:range<=32?48:16;
         PlatformInput.voiceRange(Math.min(range,PlatformInput.voiceServerRange()));
      }).bounds(left,top+208,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Test mic meter"), b -> PlatformInput.voiceTest())
         .bounds(x+3,top+208,122,20).build());
      this.addRenderableWidget(Button.builder(Component.literal("Done"), b -> this.onClose())
         .bounds(left,top+234,250,20).build());
   }

   @Override
   public boolean isPauseScreen() { return false; }

   @Override
   public boolean isInGameUi() { return true; }

   @Override
   public void extractRenderState(final GuiGraphicsExtractor graphics, final int mouseX, final int mouseY, final float partialTick) {
      super.extractRenderState(graphics,mouseX,mouseY,partialTick);
      int top=Math.max(18,this.height/2-145), left=this.width/2-125;
      graphics.centeredText(this.font,this.title,this.width/2,top-11,0xFFFFD44C);
      graphics.text(this.font,"Server URL (must be WSS):",left,top+15,0xFFEAEAEA);
      graphics.text(this.font,"One-time authorization token:",left,top+49,0xFFEAEAEA);
      String status=PlatformInput.voiceStatus();
      graphics.textWithWordWrap(this.font,Component.literal(status),left,top+263,250,0xFFDDDDDD);
      graphics.textWithWordWrap(this.font,Component.literal("Use /pvoice token on an authorized Pletzel server. Browser audio is opt-in. WebRTC peers can see IPs."),left,top+291,250,0xFFFFC27C);
      int x=Math.max(4,this.width/2-125),y=top+260;
      if(PlatformInput.voiceTransmitting())graphics.fill(x,y,x+6,y+6,0xFF55FF55);
      else if(PlatformInput.voiceMuted())graphics.fill(x,y,x+6,y+6,0xFFCC5555);
      int meter=(int)(Math.min(1.0f,PlatformInput.voiceLevel()*8.0f)*70.0f);
      graphics.fill(x+180,y,x+180+meter,y+4,0xFF55FF88);
   }
}
''')

assert 'PletzelSingleplayerWarningScreen.java' in {q.name for q in (base/'client/gui/screens').iterdir()}
assert 'MapTooltipClientComponent.java' in {q.name for q in (root/'game/src/main/java/net/pletzel/maptooltip').iterdir()}
assert 'ShulkerTooltipClientComponent.java' in {q.name for q in (root/'game/src/main/java/net/pletzel/shulkertooltip').iterdir()}
print('Native V key + PTT + Java voice menu added, existing warning/map/shulker retained')
print('Browser PletzelVoice runtime must be inserted into standalone HTML before </body>')
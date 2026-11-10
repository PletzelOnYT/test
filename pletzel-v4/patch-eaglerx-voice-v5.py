#!/usr/bin/env python3
"""Native official EaglerXServer V5 voice port for Pletzel V4 Minecraft 26.2.

Integrates with the ALREADY EXISTING Eagler v5 0xEE game-message transport
(also used for remote skins). EaglerXServer defines V5 voice packet IDs:
C: 06 request,07 connect,08 disconnect,09 peer-disconnect,0A ice,0B desc
S: 06 allowed,07 connect,08 announce,09 disconnect,0A ice,0B desc,0C roster.
No custom Pletzel server/plugin/gateway, external tokens or fabricated plugin
channels. Unrecognized/offline servers never start microphone capture.
"""
from pathlib import Path
import shutil
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
src=Path("pletzel-v4/eaglerx-voice")
game=root/"game/src/main/java"
skin=game/"net/lax1dude/eaglercraft/v1_8/profile/EaglerSkinCache26.java"
listener=game/"net/minecraft/client/multiplayer/ClientPacketListener.java"
minecraft=game/"net/minecraft/client/Minecraft.java"
options=game/"net/minecraft/client/Options.java"
language=root/"game/src/main/resources/assets/minecraft/lang/en_us.json"
platform=root/"platform-teavm/src/main/java/net/lax1dude/eaglercraft/v1_8/internal"

def replace(path,old,new,label):
    text=path.read_text()
    count=text.count(old)
    assert count==1, f"{label}: expected one original anchor, found {count}"
    path.write_text(text.replace(old,new,1))

for fname in ("EaglerXVoiceClient26.java","EaglerXVoiceScreen.java"):
    target=game/"net/lax1dude/eaglercraft/v1_8/voice"/fname
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists(), f"Refusing duplicate native voice source {target}"
    shutil.copyfile(src/fname,target)

platform.mkdir(parents=True,exist_ok=True)
target=platform/"PlatformEaglerVoice26.java"
assert not target.exists(), "Native browser voice adapter already present"
shutil.copyfile(src/"PlatformEaglerVoice26.java",target)

# Existing 26.2 remote-skin service is the verified v5 receiver of out-of-band
# 0xEE frames. Share its bundle decoder, routing only the EXACT official voice
# packet IDs to a separate client handler. Other texture packets unchanged.
replace(skin,
'''   private final Connection connection;
   private final Map<UUID, Entry> entries = new HashMap<>();''',
'''   private final Connection connection;
   private java.util.function.Consumer<byte[]> eaglerVoiceReceiver;
   private final Map<UUID, Entry> entries = new HashMap<>();''',
"share v5 receiver field")
replace(skin,
'''   public Supplier<PlayerSkin> createLookup(final UUID uuid) {''',
'''   public void setVoicePacketReceiver(final java.util.function.Consumer<byte[]> receiver) {
      this.eaglerVoiceReceiver=receiver;
   }

   public Supplier<PlayerSkin> createLookup(final UUID uuid) {''',
"client registration hook")
replace(skin,
'''         default -> {
            return; // voice, notifications, redirects, etc. are separate features
         }''',
'''         default -> {
            // Official EaglerXServer V5 voice IDs; skin packets handled above.
            // No Pletzel-specific message channel or authentication shortcut.
            if (packetId >= 0x06 && packetId <= 0x0C && this.eaglerVoiceReceiver != null) {
               this.eaglerVoiceReceiver.accept(payload);
            }
            return;
         }''',
"v5 official voice dispatch")
replace(skin,
'''   public void destroy() {
      this.connection.setEaglerMessageReceiver(null);''',
'''   public void destroy() {
      this.eaglerVoiceReceiver=null;
      this.connection.setEaglerMessageReceiver(null);''',
"cleanup voice dispatch")

# V5 capability negotiation is MANDATORY for existing servers to create a
# voice manager. EaglerXServer EnumCapabilityType.VOICE(1) = bit 0x02;
# version 0 follows the single standard capability mask varint, before the
# extended capability count. Advertising is not microphone permission.
handshake=game/"net/lax1dude/eaglercraft/v1_8/socket/EaglerXHandshake.java"
replace(handshake,
'''\t\t\t\tout.writeByte(0); // standard capability varint
\t\t\t\tout.writeByte(0); // extended capability count''',
'''\t\t\t\tout.writeByte(0x02); // official EaglerXServer V5 VOICE capability bit 1
\t\t\t\tout.writeByte(0); // VOICE_V0 capability version
\t\t\t\tout.writeByte(0); // extended capability count''',
"negotiate official voice capability V0")

# The voice client is attached only if the original handshake negotiated
# EaglerXServer V5, never for local worlds or generic vanilla connections.
replace(listener,
'''   private final @Nullable EaglerSkinCache26 eaglerSkinCache;
   private final @Nullable ParticleAdmissionController eaglerParticleAdmission;''',
'''   private final @Nullable EaglerSkinCache26 eaglerSkinCache;
   private final @Nullable net.lax1dude.eaglercraft.v1_8.voice.EaglerXVoiceClient26 eaglerVoiceClient;
   private final @Nullable ParticleAdmissionController eaglerParticleAdmission;''',
"voice client instance")
replace(listener,
'''      this.eaglerSkinCache = connection.getEaglerHandshakeVersion() >= 5 ? new EaglerSkinCache26(connection) : null;
      this.eaglerParticleAdmission = EagRuntime.getPlatformType() != EnumPlatformType.DESKTOP''',
'''      this.eaglerSkinCache = connection.getEaglerHandshakeVersion() >= 5 ? new EaglerSkinCache26(connection) : null;
      this.eaglerVoiceClient = this.eaglerSkinCache != null
         ? new net.lax1dude.eaglercraft.v1_8.voice.EaglerXVoiceClient26(minecraft,connection) : null;
      if (this.eaglerSkinCache != null && this.eaglerVoiceClient != null) {
         this.eaglerSkinCache.setVoicePacketReceiver(this.eaglerVoiceClient::handleServerVoiceFrame);
      }
      this.eaglerParticleAdmission = EagRuntime.getPlatformType() != EnumPlatformType.DESKTOP''',
"connect existing v5 transport")
replace(listener,
'''   public void close() {
      this.closed = true;
      if (this.eaglerSkinCache != null) {''',
'''   public void close() {
      this.closed = true;
      if (this.eaglerVoiceClient != null) {
         this.eaglerVoiceClient.destroy();
      }
      if (this.eaglerSkinCache != null) {''',
"microphone teardown")
replace(listener,
'''   public @Nullable Supplier<PlayerSkin> createEaglerSkinLookup(final GameProfile profile) {''',
'''   public @Nullable net.lax1dude.eaglercraft.v1_8.voice.EaglerXVoiceClient26 getEaglerVoiceClient() {
      return this.eaglerVoiceClient;
   }

   public @Nullable Supplier<PlayerSkin> createEaglerSkinLookup(final GameProfile profile) {''',
"voice client UI access")
replace(listener,
'''      if (this.eaglerSkinCache != null) {
         this.eaglerSkinCache.tick();
      }
      if (this.chatSession != null''',
'''      if (this.eaglerSkinCache != null) {
         this.eaglerSkinCache.tick();
      }
      if (this.eaglerVoiceClient != null) {
         this.eaglerVoiceClient.tick();
      }
      if (this.chatSession != null''',
"nonblocking voice events in client tick")

# Input mappings are standard Minecraft key mappings, visible/rebindable in
# Options->Controls->Key Binds and serialized in options.txt.
replace(options,
'''   public final KeyMapping keyQuickActions = new KeyMapping("key.quickActions", 71, KeyMapping.Category.MISC);''',
'''   public final KeyMapping keyQuickActions = new KeyMapping("key.quickActions", 71, KeyMapping.Category.MISC);
   public final KeyMapping keyEaglerVoiceMenu = new KeyMapping("key.pletzelEaglerVoiceMenu", 86, KeyMapping.Category.MULTIPLAYER);
   public final KeyMapping keyEaglerVoicePTT = new KeyMapping("key.pletzelEaglerVoicePTT", 82, KeyMapping.Category.MULTIPLAYER);''',
"voice key maps")
replace(options,
'''            this.keyAdvancements,
            this.keyQuickActions,
            this.keyDebugOverlay,''',
'''            this.keyAdvancements,
            this.keyQuickActions,
            this.keyEaglerVoiceMenu,
            this.keyEaglerVoicePTT,
            this.keyDebugOverlay,''',
"register key maps")
replace(minecraft,
'''   private void handleKeybinds() {
      while (this.options.keyTogglePerspective.consumeClick()) {''',
'''   private void handleKeybinds() {
      while (this.options.keyEaglerVoiceMenu.consumeClick()) {
         if (this.getConnection() != null && this.getConnection().getEaglerVoiceClient() != null) {
            this.gui.setScreen(new net.lax1dude.eaglercraft.v1_8.voice.EaglerXVoiceScreen(
               null, this.getConnection().getEaglerVoiceClient()));
         }
      }
      while (this.options.keyTogglePerspective.consumeClick()) {''',
"native V opens voice menu")

replace(language,
'''  "key.quickActions": "Quick Actions",''',
'''  "key.pletzelEaglerVoiceMenu": "EaglercraftX Voice Menu",
  "key.pletzelEaglerVoicePTT": "EaglercraftX Push-to-Talk",
  "key.quickActions": "Quick Actions",''',
"English voice key labels")

for name in ("EaglerXVoiceClient26.java","EaglerXVoiceScreen.java"):
    assert (game/"net/lax1dude/eaglercraft/v1_8/voice"/name).is_file()
assert 'PlatformEaglerVoice26' in (platform/"PlatformEaglerVoice26.java").read_text()
assert skin.read_text().count('setVoicePacketReceiver')==1
assert listener.read_text().count('this.eaglerVoiceClient.tick()')==1
assert 'PletzelSingleplayerWarningScreen' in (game/"net/minecraft/client/gui/screens/TitleScreen.java").read_text()
assert 'MapTooltipData' in (game/"net/minecraft/world/item/MapItem.java").read_text()
assert 'ShulkerTooltipData' in (game/"net/minecraft/world/item/ItemStack.java").read_text()
print("VOICE NATIVE SOURCE INTEGRATION PASS: official V5 signal path shares existing skin transport")
print("No custom Pletzel voice servers, token commands, plugin channels or HTML overlays")
print("Client GUI V and configurable PTT R installed; no microphone until Enable click")

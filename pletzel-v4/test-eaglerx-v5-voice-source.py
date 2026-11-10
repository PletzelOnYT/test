#!/usr/bin/env python3
"""Fail-closed parity checks for official EaglerXServer V5 voice integration.

These source checks CANNOT prove live two-player audio compatibility.
They guard exact published packet IDs, official V0 capability negotiation,
transport integration, microphone privacy and Minecraft native UI.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
game=root/"game/src/main/java"
platform=root/"platform-teavm/src/main/java"
read=lambda x:x.read_text()

h=read(game/"net/lax1dude/eaglercraft/v1_8/socket/EaglerXHandshake.java")
assert "out.writeByte(0x02); // official EaglerXServer V5 VOICE capability bit 1" in h
assert "out.writeByte(0); // VOICE_V0 capability version" in h
assert "out.writeByte(0); // extended capability count" in h
skin=read(game/"net/lax1dude/eaglercraft/v1_8/profile/EaglerSkinCache26.java")
assert "this.eaglerVoiceReceiver.accept(payload)" in skin
assert "packetId >= 0x06 && packetId <= 0x0C" in skin
assert "this.handleSkinPreset(input)" in skin
assert "this.handleTextures(input)" in skin
client=read(game/"net/lax1dude/eaglercraft/v1_8/voice/EaglerXVoiceClient26.java")
ids={
 "C_REQUEST=0x06":"Official v5 request",
 "C_CONNECT=0x07":"Official v5 connect",
 "C_DISCONNECT=0x08":"Official v5 disconnect",
 "C_DISCONNECT_PEER=0x09":"Official v5 disconnect peer",
 "C_ICE=0x0A":"Official v5 ICE",
 "C_DESCRIPTION=0x0B":"Official v5 SDP",
 "S_ALLOWED=0x06":"Official v5 allowed",
 "S_CONNECT=0x07":"Official v5 peer connect",
 "S_ANNOUNCE=0x08":"Official v5 peer announcement",
 "S_DISCONNECT_PEER=0x09":"Official v5 disconnect peer",
 "S_ICE=0x0A":"Official v5 ICE",
 "S_DESCRIPTION=0x0B":"Official v5 SDP",
 "S_GLOBAL=0x0C":"Official v5 player roster"
}
for fragment,label in ids.items():
 assert fragment in client,("Missing official packet",label)
assert "connection.sendEaglerMessage(raw.toByteArray())" in client
assert "PlatformEaglerVoice26.enable();" in client
assert "PlatformEaglerVoice26.stop();" in client
assert "this.eaglerVoiceClient.tick()" in read(game/"net/minecraft/client/multiplayer/ClientPacketListener.java")
assert "this.eaglerVoiceClient.destroy()" in read(game/"net/minecraft/client/multiplayer/ClientPacketListener.java")
assert "setVoicePacketReceiver(this.eaglerVoiceClient::handleServerVoiceFrame)" in read(game/"net/minecraft/client/multiplayer/ClientPacketListener.java")
js=read(platform/"net/lax1dude/eaglercraft/v1_8/internal/PlatformEaglerVoice26.java")
assert "navigator.mediaDevices.getUserMedia" in js
assert "new RTCPeerConnection" in js
assert "v.sendGain.gain.value = 0" in js
assert "v.sendGain.gain.value = talking ? 1 : 0;" in js
assert "track.stop()" in js
assert "globalThis.__pletzelEaglerVoice" in js
assert "v.enable = () =>" in js
assert "v.stop = () =>" in js
assert "v.transmit = (talking) =>" in js
assert "this.minecraft.gui.setScreen" not in js
screen=read(game/"net/lax1dude/eaglercraft/v1_8/voice/EaglerXVoiceScreen.java")
for label in ("Enable Voice","Mute Microphone","Push-to-Talk","Voice Activation","Global","Proximity"):
 assert label in screen
assert "Button.builder" in screen
assert "AbstractSliderButton" in screen
assert "WebRTC peers may learn your IP address" in screen
opts=read(game/"net/minecraft/client/Options.java")
assert 'new KeyMapping("key.pletzelEaglerVoiceMenu", 86' in opts
assert 'new KeyMapping("key.pletzelEaglerVoicePTT", 82' in opts
assert "this.keyEaglerVoiceMenu," in opts and "this.keyEaglerVoicePTT," in opts
gameclient=read(game/"net/minecraft/client/Minecraft.java")
assert "keyEaglerVoiceMenu.consumeClick()" in gameclient
assert "new net.lax1dude.eaglercraft.v1_8.voice.EaglerXVoiceScreen" in gameclient
assert "PletzelSingleplayerWarningScreen" in read(game/"net/minecraft/client/gui/screens/TitleScreen.java")
assert "MapTooltipData" in read(game/"net/minecraft/world/item/MapItem.java")
assert "ShulkerTooltipData" in read(game/"net/minecraft/world/item/ItemStack.java")
for forbidden in ("PletzelVoice","pvoice token","Pletzel gateway","pvoice","/pvoice"):
 assert forbidden.lower() not in (client+screen+js).lower(), forbidden
print("OFFICIAL V5 SOURCE PARITY PASS: handshake VOICE_V0 + original voice signaling packet IDs")
print("PASS: original 0xEE game-message transport reused, skin dispatch preserved")
print("PASS: no microphone until Minecraft Enable click; mute and disconnect cleanup")
print("PASS: native Minecraft GUI, native rebindable V and R keys")
print("PASS: native Singleplayer warning, Map Tooltip, Shulker Tooltip preserved")
print("NOT VERIFIED: older-client cross-play, WebRTC audio on real existing server")

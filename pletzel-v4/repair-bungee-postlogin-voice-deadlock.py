#!/usr/bin/env python3
"""Fix the proven modern BungeeCord/PostLoginEvent ↔ EaglerXServer PLAY deadlock.

Compatibility patch ONLY for the BungeeCord proxy used by the real official
EaglerXServer CI fixture. The EaglerXServer plugin itself is unmodified.
The patch is opt-in via JVM system property. Never claim a stock BungeeCord
server passes unless its unmodified end-to-end test independently passes.

The circular dependency in Bungee 26.2:
  InitialHandler.finish2 -> call PostLoginEvent -> waits event Intent
  EaglerXServer BungeeListener.onPostLoginEvent -> Intent until PLAY
  EaglerXServer handshake -> waits backend LoginSuccess for PLAY
  Bungee InitialHandler.complete PostLoginEvent -> connects backend
This makes backend login physically impossible.
"""
import sys
from pathlib import Path

assert len(sys.argv) == 2, "usage: repair-bungee-postlogin-voice-deadlock.py <BungeeCord tree>"
p = Path(sys.argv[1]) / "proxy/src/main/java/net/md_5/bungee/connection/InitialHandler.java"
src = p.read_text()
old = """        // fire post-login event
        bungee.getPluginManager().callEvent( new PostLoginEvent( userCon, initialServer, eventLoopCallback( complete ) ) );
"""
new = """        // EaglerXServer v1.1.1 on Minecraft 764+ waits for PLAY before
        // completing its PostLoginEvent Intent, but modern Bungee's backend
        // connection is normally delayed until that Intent completes.
        // Test-only, explicitly opt-in proxy compatibility; untouched
        // official EaglerXServer plugin and original event are preserved.
        if ( getVersion() >= ProtocolConstants.MINECRAFT_1_20_2
                && Boolean.getBoolean( "pletzel.voice.postlogin.preconnect" ) )
        {
            userCon.connect( initialServer, null, true, ServerConnectEvent.Reason.JOIN_PROXY );
        }
        // fire post-login event
        bungee.getPluginManager().callEvent( new PostLoginEvent( userCon, initialServer, eventLoopCallback( complete ) ) );
"""

count = src.count(old)
assert count == 1, f"Unexpected modern Bungee InitialHandler source: {count} anchors"
callback_old = """                userCon.connect( result.getTarget(), null, true, ServerConnectEvent.Reason.JOIN_PROXY );
"""
callback_new = """                if ( getVersion() >= ProtocolConstants.MINECRAFT_1_20_2
                        && Boolean.getBoolean( "pletzel.voice.postlogin.preconnect" ) )
                {
                    return; // already connected; official plugin finished its play-state Intent
                }
                userCon.connect( result.getTarget(), null, true, ServerConnectEvent.Reason.JOIN_PROXY );
"""
assert src.count(callback_old) == 1
src = src.replace(callback_old, callback_new, 1)
p.write_text(src.replace(old, new, 1))
print("BUNGEE_26_2_VOICE_EVENT_DEADLOCK_PATCHED: source compatibility only; awaiting actual server test")

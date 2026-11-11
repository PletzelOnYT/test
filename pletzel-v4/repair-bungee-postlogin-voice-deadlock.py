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
new = """        // EaglerXServer v1.1.1 on Minecraft protocol 764+ waits for PLAY
        // before completing its PostLoginEvent Intent. New Bungee also waits
        // for PostLoginEvent completion before connecting the backend, while
        // the Eagler handshake cannot enter PLAY before a backend LoginSuccess.
        // Preserve native ordering unless the narrowly scoped CI compatibility
        // JVM flag is explicitly enabled. This fixes the circular wait without
        // changing any official EaglerXServer plugin bytes or V5 packets.
        if ( getVersion() >= ProtocolConstants.MINECRAFT_1_20_2
                && Boolean.getBoolean( "pletzel.voice.postlogin.preconnect" ) )
        {
            userCon.connect( initialServer, null, true, ServerConnectEvent.Reason.JOIN_PROXY );
            bungee.getPluginManager().callEvent( new PostLoginEvent( userCon, initialServer,
                    eventLoopCallback( (result, error) -> { } ) ) );
        } else
        {
            // Original unchanged behavior for ordinary server deployments.
            bungee.getPluginManager().callEvent( new PostLoginEvent( userCon, initialServer, eventLoopCallback( complete ) ) );
        }
"""
count = src.count(old)
assert count == 1, f"Unexpected modern Bungee InitialHandler source: {count} anchors"
p.write_text(src.replace(old, new, 1))
print("BUNGEE_26_2_VOICE_EVENT_DEADLOCK_PATCHED: source compatibility only; awaiting actual server test")

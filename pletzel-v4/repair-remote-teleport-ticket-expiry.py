#!/usr/bin/env python3
"""Keep a genuine FULL destination chunk ticket alive for asynchronous browser /tp.

The pinned 26.2 source creates EAGLER_TELEPORT tickets with 40-tick lifetime.
The browser TeleportCommand schedules FULL asynchronously and does not actually
teleport the player until that future completes. A distant chunk can take
thousands of ticks under cooperative WasmGC worldgen. TicketStorage expires
a loading ticket once its holder's saveSync is done, which does NOT prove
FULL is ready. Expiry can starve the exact FULL future and leave the player
at the old position after the command has already printed "Teleported".

Only the browser-specific temporary ticket changes. All vanilla tickets,
chunk generation stages, the server-authoritative teleport, native movement
packets and client ACK requirements remain unchanged. A finite 12,000-tick
timeout prevents abandoned requests from retaining chunks indefinitely.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:
    raise SystemExit("usage: repair-remote-teleport-ticket-expiry.py <pinned-engine-root>")
p=Path(sys.argv[1])/"game/src/main/java/net/minecraft/server/level/TicketType.java"
s=p.read_text(encoding="utf-8")
old='public static final TicketType EAGLER_TELEPORT = register("eagler_teleport", 40L, FLAG_LOADING);'
new='public static final TicketType EAGLER_TELEPORT = register("eagler_teleport", 12000L, FLAG_LOADING);'
assert s.count(old)==1,(p,"unexpected remote teleport ticket implementation",s.count(old))
p.write_text(s.replace(old,new,1),encoding="utf-8")
assert p.read_text().count(new)==1
print("TELEPORT_TICKET_REPAIR: asynchronous FULL destination remains scheduled up to 12000 server ticks")
print("No fake worldgen completion, no bypassed collision, and vanilla chunk tickets unchanged")

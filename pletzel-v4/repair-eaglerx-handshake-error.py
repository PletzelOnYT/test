#!/usr/bin/env python3
"""Repair official EaglerXServer V3–V5 post-version rejection length decoding.

EaglerXServer WebSocketEaglerInitialHandler.sendErrorCode sends UTF-8
errors with a U16 length once canSendV3Kick becomes true after version
selection. The upstream donor Eaglercraft-26.2-source EaglerXHandshake
incorrectly used U8 for V4/V5 rejection messages, hiding the actual error
and leaving Pletzel clients saying 'rejected login (8): ' with no reason.

No server behavior or handshake packet IDs are altered by this patch.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
p=root/"game/src/main/java/net/lax1dude/eaglercraft/v1_8/socket/EaglerXHandshake.java"
s=p.read_text(encoding="utf-8")
old1='readServerError(allow, handshakeVersion == 3)'
old2='readServerError(finished, handshakeVersion == 3)'
assert s.count(old1)==1,(old1,s.count(old1))
assert s.count(old2)==1,(old2,s.count(old2))
s=s.replace(old1,'readServerError(allow, true)',1)
s=s.replace(old2,'readServerError(finished, true)',1)
old3='private static String readServerError(Reader reader, boolean v3) {\n\t\tint code = reader.u8();\n\t\tint length = v3 ? reader.u16() : reader.u8();'
new3='private static String readServerError(Reader reader, boolean postVersionNegotiation) {\n\t\tint code = reader.u8();\n\t\t// Official v3–v5 post-version packets use U16 UTF-8 lengths.\n\t\t// Pre-version errors still use the legacy U8 length.\n\t\tint length = postVersionNegotiation ? reader.u16() : reader.u8();'
assert s.count(old3)==1,"EaglerXHandshake error decoder format changed"
s=s.replace(old3,new3,1)
assert s.count('readServerError(version, false)')==1
assert s.count('readServerError(allow, true)')==1
assert s.count('readServerError(finished, true)')==1
assert 'out.writeByte(0x02); // official EaglerXServer V5 VOICE capability bit 1' in s, "Do not lose native voice capability advertisement"
p.write_text(s,encoding="utf-8")
print("Repaired real EaglerXServer V5 U16 login-error strings; voice v0 negotiation preserved",flush=True)

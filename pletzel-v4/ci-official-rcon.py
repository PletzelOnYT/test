#!/usr/bin/env python3
"""Real Paper 26.2 RCON evidence, no game state mocking.

Run inside the isolated official-server CI Docker container, on loopback only:
    python3 /tmp/pletzel-rcon.py 'data get entity PlayerName Pos'

The resulting coordinates originate from the authoritative Paper server.
This does not modify the world or grant client-side privileges.
"""
import json, os, socket, struct, sys
COMMAND = " ".join(sys.argv[1:]).strip()
assert COMMAND, "Supply a read-only server command"
assert COMMAND == "list" or COMMAND.startswith("data get entity "), "Read-only RCON queries only"
PASSWORD = os.environ.get("PLETZEL_CI_RCON_PASSWORD", "pletzel-ci-rcon-local-only")
def packet(req_id,typ,msg):
    body=struct.pack("<ii",req_id,typ)+msg.encode("utf-8")+b"\0\0"
    return struct.pack("<i",len(body))+body
def read_n(sock,n):
    b=bytearray()
    while len(b)<n:
        chunk=sock.recv(n-len(b))
        if not chunk:raise ConnectionError("Paper RCON socket disconnected")
        b.extend(chunk)
    return bytes(b)
def read_packet(sock):
    (n,)=struct.unpack("<i",read_n(sock,4))
    if not (10<=n<=65536):raise RuntimeError("Invalid RCON response length "+str(n))
    b=read_n(sock,n)
    req_id,typ=struct.unpack("<ii",b[:8])
    return req_id,typ,b[8:-2].decode("utf-8","replace")
with socket.create_connection(("127.0.0.1",25575),timeout=12) as s:
    s.settimeout(12)
    s.sendall(packet(100,3,PASSWORD))
    authenticated=False
    for _ in range(4):
        req_id,typ,msg=read_packet(s)
        if req_id==-1:raise PermissionError("Paper RCON authentication was rejected")
        if req_id==100 and typ==2:
            authenticated=True
            break
    assert authenticated,"Paper RCON did not confirm authentication"
    s.sendall(packet(200,2,COMMAND))
    result=None
    for _ in range(5):
        req_id,typ,msg=read_packet(s)
        if req_id==200:
            result=msg
            break
    assert result is not None,"No authoritative RCON response"
    print(json.dumps({"source":"real Paper 26.2 RCON","command":COMMAND,"response":result}),flush=True)

#!/usr/bin/env python3
"""Real official EaglerXServer V5 login preflight, no mocks or browser dependency.

This checks only that the server reaches SERVER_ALLOW_LOGIN after the V5
VOICE_V0-capable login request. It does NOT count as two-player voice acceptance.
"""
import base64
import os
import socket
import struct
import time
import subprocess
import threading

HOST = "127.0.0.1"
PORT = 5200
PROTO = 776  # Minecraft 26.2
USERNAME = "VoiceProbe262"


def read_exact(sock, count):
    parts = []
    while count:
        chunk = sock.recv(count)
        if not chunk:
            raise EOFError("WebSocket disconnected during real V5 login")
        count -= len(chunk)
        parts.append(chunk)
    return b"".join(parts)


def send_frame(sock, payload, opcode=2):
    mask = os.urandom(4)
    size = len(payload)
    prefix = bytes([0x80 | opcode])
    if size < 126:
        prefix += bytes([0x80 | size])
    elif size < 65536:
        prefix += bytes([0x80 | 126]) + struct.pack(">H", size)
    else:
        prefix += bytes([0x80 | 127]) + struct.pack(">Q", size)
    sock.sendall(prefix + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def recv_frame(sock):
    h = read_exact(sock, 2)
    opcode = h[0] & 0x0F
    n = h[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", read_exact(sock, 2))[0]
    elif n == 127:
        n = struct.unpack(">Q", read_exact(sock, 8))[0]
    if n > 65536:
        raise AssertionError("Unexpected oversized server handshake frame")
    mask = read_exact(sock, 4) if h[1] & 0x80 else None
    payload = read_exact(sock, n)
    if mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def recv_binary(sock, stage, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.2, deadline - time.monotonic()))
        opcode, payload = recv_frame(sock)
        if opcode == 2 and payload:
            return payload
        if opcode == 9:
            send_frame(sock, payload, 10)
        elif opcode == 8:
            raise AssertionError(f"Official server closed WebSocket before {stage}")
    raise TimeoutError(f"Official V5 server did not send {stage} in {timeout}s")


def ascii8(s):
    b = s.encode("ascii")
    assert len(b) < 256
    return bytes([len(b)]) + b


def version_response(payload):
    assert payload[0] == 0x02, f"Expected official V5 SERVER_VERSION 0x02, got {payload[:2].hex()}"
    selected, proto = struct.unpack_from(">HH", payload, 1)
    assert selected == 5 and proto == PROTO, f"Server selected Eagler V{selected}, Minecraft protocol {proto}"
    offset = 5
    for _ in range(2):
        count = payload[offset]
        offset += count + 1
    auth = payload[offset]
    offset += 1
    salt = struct.unpack_from(">H", payload, offset)[0]
    offset += salt + 2
    assert auth == 0, f"Official server requires authentication type {auth}"
    nickname_selection = bool(payload[offset]) if offset < len(payload) else False
    return nickname_selection


def capture_live_backend_state():
    """Observe the real in-container TCP backend connection while login waits."""
    for seconds in (6, 12, 18):
        time.sleep(6)
        proc = subprocess.run(
            ["docker", "exec", "pletzel-official-voice-ci", "sh", "-c",
             "cat /proc/net/tcp /proc/net/tcp6"],
            text=True, capture_output=True, timeout=8,
        )
        if proc.returncode:
            print("OFFICIAL_LOGIN_BACKEND_TCP_OBSERVE_FAILED",
                  proc.stderr[-120:], flush=True)
            return
        # TCP state 01 = established. Target Paper backend is :63DD (25565).
        rows = [line.split() for line in proc.stdout.splitlines()
                if len(line.split()) >= 4]
        paper = [row for row in rows if
                 (row[1].endswith(":63DD") or row[2].endswith(":63DD"))
                 and row[3] == "01"]
        print("OFFICIAL_LOGIN_BACKEND_TCP_AT", seconds, "seconds",
              "established_connections", len(paper), flush=True)


def main():
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.settimeout(12)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (f"GET / HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n"
               "Connection: Upgrade\r\nUpgrade: websocket\r\n"
               "Sec-WebSocket-Version: 13\r\n" + f"Sec-WebSocket-Key: {key}\r\n\r\n")
        sock.sendall(req.encode("ascii"))
        hdr = b""
        while b"\r\n\r\n" not in hdr and len(hdr) < 8192:
            hdr += read_exact(sock, 1)
        assert hdr.startswith(b"HTTP/1.1 101"), f"Official WebSocket upgrade failed: {hdr[:80]!r}"
        # Exactly mirrors the current native Minecraft 26.2 Java handshake.
        init = (b"\x01\x02" + struct.pack(">HHHHHH", 3, 3, 4, 5, 1, PROTO)
                + ascii8("Eaglercraft 26.2") + ascii8("26.2") + b"\x00"
                + ascii8(USERNAME))
        send_frame(sock, init)
        nickname = version_response(recv_binary(sock, "SERVER_VERSION", 12))
        print("OFFICIAL_V5_VERSION_NEGOTIATED", PROTO, "nickname_selection", nickname, flush=True)
        # Corrected V5 standard capability: voice mask=2, V0 versions bitmask=1.
        login = (b"\x04" + ascii8(USERNAME if nickname else "") + ascii8("default")
                 + b"\x00\x00\x00\x02\x01\x00")
        send_frame(sock, login)
        threading.Thread(target=capture_live_backend_state, daemon=True).start()
        response = recv_binary(sock, "SERVER_ALLOW_LOGIN", 35)
        print("OFFICIAL_V5_LOGIN_RESPONSE", "packet", hex(response[0]), "length", len(response), flush=True)
        if response[0] == 0x06:
            raise AssertionError("Official server denied V5 login (reason omitted from CI to avoid sensitive text)")
        if response[0] == 0xFF:
            # Upstream public kick message, never private credentials/SDP.
            code = response[1] if len(response) > 1 else -1
            msg = ""
            if len(response) >= 4:
                n = struct.unpack_from(">H", response, 2)[0]
                if n <= len(response) - 4:
                    msg = response[4:4+n].decode("utf-8", "replace")
            print("OFFICIAL_SERVER_V5_ERROR_CODE", code,
                  "message", msg[:180], flush=True)
            raise AssertionError("Official server sent V5 protocol error")
        assert response[0] == 0x05, "Official server did not complete actual proxy-to-Paper login handshake"
        print("OFFICIAL_V5_REAL_BACKEND_ALLOW_LOGIN_PASS: actual server returned 0x05", flush=True)
        # The socket intentionally closes before profile upload. Real playable
        # login, game movement, and decoded voice RTP require the browser test.


if __name__ == "__main__":
    main()

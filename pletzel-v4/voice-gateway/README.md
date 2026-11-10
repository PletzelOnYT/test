# Pletzel V4 — voice transport experiment (NOT A RELEASE)

This branch adds an **original, independently written server-side WebRTC
signaling prototype** and a repeatable security/proximity test. It does NOT
modify Minecraft 26.2 client binaries, capture microphone input, relay audio,
add a functioning V menu, or connect to a live Simple Voice Chat server.

It is **not** the finished user-requested voice chat system. The existing
Pletzel V4 standalone HTML remains unchanged and has no new voice feature.

## Verified upstream interfaces

- Simple Voice Chat's public Minecraft 26.2 code is at
  https://github.com/henkelmax/simple-voice-chat/tree/26.2
- The repository's `license` contains "Copyright (c) Max Henkel -
  All Rights Reserved"; this prototype does NOT copy its code or artwork.
- Minecraft 26.2 Simple Voice Chat normally uses UDP (24454 by default),
  Opus, encrypted and authenticated voice packets, and server-side hooks.
  The bridge here does NOT implement that binary protocol or authenticate
  with Simple Voice Chat. It is therefore **not compatible with a standard
  SVC server as built**.
- Older EaglercraftX 1.8 uses WebRTC and custom Eagler signaling
  `EAG|Voice-1.8` with Connect/ICE/Description packet families. Those are
  not automatically supported by Pletzel V4's native 26.2 packet handlers.
- The pinned 26.2 Eaglercraft engine contains `PlatformWebRTC.java`,
  but not the older native voice controller, microphone runtime or voice
  packet protocol. A dedicated 26.2 integration is necessary.

## Gateway prototype

`server.cjs` is a localhost-only HTTPS-reverse-proxy-ready WebSocket
signaling gate, NOT a voice media service.

Requirements: Node 22+, `npm install`; configure independent random
`VOICE_HMAC_SECRET` and `VOICE_POSITION_SECRET` with at least 32 bytes.
The game server must issue short-lived HMAC tickets with fields
`aud="pletzel-voice-v1", uuid, session, exp`. Never let a browser mint its own
ticket. The trusted game server must POST the **full** player snapshot to
`/authoritative-positions` with `Authorization: Bearer <VOICE_POSITION_SECRET>`.
Each player has `uuid,x,y,z,world,dimension`. Source these coordinates,
worlds, and UUIDs from server-side Minecraft sessions only, not client
packet claims. Default radius 32 blocks, snapshots expire after 8 seconds.

The WebSocket server accepts only `auth` with a valid signed ticket, then
relays `offer`, `answer`, and `ice` to authenticated and nearby players.
The server sends `near` and `far` as position snapshots change. All
connections must be served through HTTPS/WSS for actual deployment; the
localhost plain-socket listener is only for reverse-proxy development.

**Critical limitation:** Distance gates on *WebRTC signaling* do NOT prevent
malicious clients from continuing an established direct peer-media session.
Authoritative audio policy requires a server-routed media relay/SFU (or an
enforcing gateway), not merely WebRTC offers/answers. This is a signaling
foundation, not an anti-spoof complete voice solution.

## Missing before any native voice release

1. Actual user-supplied voice JAR version, assets and license inspection.
2. Minecraft 26.2 client transport and native V/Controls UI integration,
   with explicit microphone permission and live mute/PTT/VAD indicators.
3. A gameplay-server plugin/proxy hook issuing bound session tickets and
   publishing verified live positions/dimensions.
4. A secure audio transport with server-enforced proximity and privacy:
   Opus packet handling, playback jitter buffer, positioning, permissions,
   group and mute support. A P2P WebRTC design must disclose peer IP exposure.
5. Full disconnect cleanup, real multi-client media recording/monitoring of
   packet flow **without recording people's audio**, and real human or hardware
   microphone loopback acceptance.
6. Exact protocol-specific Simple Voice Chat interoperation tests where
   claimed; plus independent older Eagler voice protocol tests.
7. Compile the revised full Minecraft 26.2 Java / TeaVM Wasm-GC game and
   confirm multiplayer voice between two standalone HTML clients.

No broad compatibility or working voice claim should be made until those
tests pass. Other current Pletzel V4 features are deliberately untouched.

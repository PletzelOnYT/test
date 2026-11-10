# Pletzel V4 voice — experimental, not a finished release

This branch contains an **original browser WebRTC voice implementation**, a native
Minecraft Java V-key menu patch, a Node.js WebSocket signaling gateway, and a
Paper 26.2 authentication/position publisher. These parts must be deployed together.

**Current status:** source integration and protocol tests are in development.
Do not call this Simple Voice Chat compatible, EaglercraftX voice compatible,
or production ready until a genuinely connected 2-player server test passes.

## Compatibility and attribution

Reference: [Simple Voice Chat](https://github.com/henkelmax/simple-voice-chat)
26.2 branch, currently `2.7.0-pre1+26.2`. Its `license` states
`Copyright (c) Max Henkel - All Rights Reserved`.
No Simple Voice Chat source is copied or bundled; its native UDP transport,
Opus packet format, session protocol, and groups are **not** implemented.

Legacy EaglercraftX voice signaling is a different protocol and is **not**
enabled by this prototype. Its WebRTC stack cannot be used for a different
network's voice chat without compatibility work.

## Architecture

- `client/patch-voice-native.py`: adds a real Minecraft screen, V menu key,
  Left Alt PTT key, native input bindings, and disconnect lifecycle handling.
- `client/voice-runtime.js`: browser microphone permission, audio graph,
  WebRTC SDP/ICE signaling, PTT, volume, voice activity threshold, spatial
  HRTF panning, device cycling and cleanup. NO HTML overlay or browser popup.
- `gateway/server.mjs`: validates server-issued single-use bearer tokens,
  authorizes near peers using only server-submitted player positions/dimensions,
  relays WebRTC SDP/ICE but no audio payload, unpairs players out of range,
  and disconnects offline sessions.
- `paper/`: Paper plugin implementing `/pvoice token`, position updates,
  dimension separation, and signed-by-secret administrative communication.

**Security limitations:** WebRTC is peer-to-peer and may reveal player IP
addresses. Use a TURN-only/relay setup before deploying on a public server
if IP exposure is unacceptable. Signaling must be served through WSS/TLS,
with a secure-context HTML origin for microphone permission. The gateway
binds to 127.0.0.1 by default. Keep the administrative secret private.
The server controls who can connect and when pairs are connected.
Users who obtain an authorized SDP stream can potentially choose not to honor
client-side volume; do not mistake user-side gain attenuation for cryptographic
control of playback volume.

## Run gateway

On a server with Node 22 or newer:

```bash
cd pletzel-v4/voice/gateway
npm install
export VOICE_ADMIN_SECRET="$(openssl rand -hex 32)"
export VOICE_BIND=127.0.0.1
export VOICE_PORT=25580
export VOICE_RANGE=48
npm test
npm start
```

Provide public `wss://voice.example.com/voice` through a TLS reverse proxy,
forwarding websocket upgrades to `http://127.0.0.1:25580`.
Expose **neither** the plain gateway port nor `/admin/*` publicly.
If Paper and the gateway run on different hosts, use HTTPS between them too.

## Install Paper 26.2 plugin

```bash
cd pletzel-v4/voice/paper
gradle jar
```

Put the produced plugin JAR in the server's `plugins/` folder. Edit
`plugins/PletzelVoice/config.yml`:

- `admin_url`: internal gateway HTTP/HTTPS endpoint
- `admin_secret`: **the same strong value** as `VOICE_ADMIN_SECRET`
- `public_voice_url`: public secure `wss://.../voice` endpoint
- `server_id`: stable identifier for this Minecraft server

Restart the server and check the plugin logs. Each logged-in player executes
`/pvoice token`, then presses V in the Pletzel client, enters the public WSS
address, pastes the token and chooses **Enable + Connect**. The browser prompts
for microphone permission. Voice starts **muted** until explicitly unmuted;
PTT transmits only while the configured key is held. Keys can be rebound
in Minecraft's normal Controls settings.

This authorization step is manual for now. SVC server-side integration,
group chat, remote SVC audio, and older EaglercraftX voice compatibility
must not be claimed from this prototype.

## Native standalone client integration

Base: the same pinned Pletzel V4 build stack that includes the Singleplayer
warning, touch/mouse input mode, Schematica, Map Tooltip, Shulker Box Tooltip,
and the Steve/Alex selector.

Run `python3 pletzel-v4/voice/client/patch-voice-native.py engine` **after**
the existing source patch sequence and **before Java/TeaVM compilation**.
After linking and packaging the exact game HTML, embed
`client/voice-runtime.js` inside a script tag immediately before its
closing `</body>` tag. This is a background audio subsystem, **not** a
browser UI. Verify the native screen and keybindings are reachable in
WebAssembly rather than only in compiled Java bytecode.

## Required acceptance before release

- Paper plugin compiles against the exact server API.
- Signaling authentication, tampering, token reuse, distance and dimension
  filters pass tests.
- Two real authenticated Minecraft players join a Paper 26.2 server.
- Two distinct real browser microphone tracks produce audible bidirectional
  audio with spatial positioning and out-of-range disconnection.
- PTT/mute/disconnect do not transmit microphone speech or leave capture live.
- UI and transport work in an actual packaged Pletzel V4 WebAssembly game,
  including after the Singleplayer warning/other feature flows.
- SVC version-specific bridges are tested against actual SVC clients/servers
  before compatibility is advertised.

**Do not promote this to a finished voice release solely because CI links
the HTML or synthetic microphone sources generate WebRTC packets.**

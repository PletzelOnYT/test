package net.lax1dude.eaglercraft.v1_8.internal;

import org.teavm.jso.JSBody;

/**
 * Browser WebRTC media engine for official EaglerXServer v5 signaling.
 * User permission is requested ONLY by a real in-game Enable button.
 * No separate gateway or microphone upload endpoint is used.
 * In direct peer-to-peer WebRTC, participants may learn each other's IP.
 */
public final class PlatformEaglerVoice26 {
   private PlatformEaglerVoice26() {}
   @JSBody(script = "(function() {\n  if (globalThis.__pletzelEaglerVoice) return;\n  const v = {\n    state: 0, active: false, stream: null, sendStream: null, audio: null, analyser: null, sendGain: null,\n    peers: new Map(), queue: [], iceServers: [], volume: 0.65,\n    global: false, permissionGeneration: 0, maxEvents: 256\n  };\n  const push = (kind, id, data) => {\n    if (v.queue.length >= v.maxEvents) v.queue.shift();\n    v.queue.push(JSON.stringify({kind: kind, id: id || \"\", data: data || \"\"}));\n  };\n  const closePeer = (id, notify) => {\n    const p = v.peers.get(id);\n    if (!p) return;\n    v.peers.delete(id);\n    try { p.connection.close(); } catch (e) {}\n    try { p.source && p.source.disconnect(); } catch (e) {}\n    try { p.gain && p.gain.disconnect(); } catch (e) {}\n    try { p.panner && p.panner.disconnect(); } catch (e) {}\n    if (notify) push(\"closed\", id, \"\");\n  };\n  v.supported = () => typeof RTCPeerConnection !== \"undefined\"\n    && !!navigator.mediaDevices && !!navigator.mediaDevices.getUserMedia\n    && typeof (globalThis.AudioContext || globalThis.webkitAudioContext) !== \"undefined\";\n  v.configure = (json) => {\n    try {\n      const urls = JSON.parse(json);\n      if (!Array.isArray(urls) || urls.length > 64) return;\n      v.iceServers = urls.map((s) => {\n        const a = String(s).split(\";\");\n        return a.length === 3 ? {urls:a[0],username:a[1],credential:a[2]} : {urls:a[0]};\n      }).filter((s) => /^(stun|turn|turns):/i.test(s.urls));\n    } catch (e) {\n      v.iceServers = [];\n    }\n  };\n  v.enable = () => {\n    if (!v.supported()) { v.state = 4; return; }\n    if (v.active || v.state === 1) return;\n    const generation = ++v.permissionGeneration;\n    v.state = 1;\n    navigator.mediaDevices.getUserMedia({audio:{\n      echoCancellation:true, noiseSuppression:true, autoGainControl:true\n    }}).then((stream) => {\n      if (generation !== v.permissionGeneration) {\n        stream.getTracks().forEach((track) => track.stop()); return;\n      }\n      v.stream = stream;\n      const Context = globalThis.AudioContext || globalThis.webkitAudioContext;\n      v.audio = new Context();\n      const source = v.audio.createMediaStreamSource(stream);\n      v.analyser = v.audio.createAnalyser();\n      v.analyser.fftSize = 256;\n      source.connect(v.analyser);\n      // Keep microphone analysis live for voice activation while making\n      // outgoing WebRTC audio SILENT until explicit PTT/VAD transmission.\n      v.sendGain = v.audio.createGain();\n      v.sendGain.gain.value = 0;\n      const destination = v.audio.createMediaStreamDestination();\n      v.sendStream = destination.stream;\n      source.connect(v.sendGain);\n      v.sendGain.connect(destination);\n      v.active = true; v.state = 2;\n      v.audio.resume().catch(() => {});\n      push(\"ready\", \"\", \"\");\n    }).catch((e) => {\n      if (generation !== v.permissionGeneration) return;\n      v.active = false; v.state = 3;\n      push(\"permission\", \"\", String(e && e.name || \"Denied\"));\n    });\n  };\n  v.stop = () => {\n    ++v.permissionGeneration;\n    for (const id of Array.from(v.peers.keys())) closePeer(id, false);\n    if (v.stream) {\n      v.stream.getTracks().forEach((track) => track.stop());\n      v.stream = null;\n    }\n    if (v.sendStream) {\n      v.sendStream.getTracks().forEach((track) => track.stop());\n      v.sendStream = null;\n    }\n    if (v.sendGain) { try { v.sendGain.disconnect(); } catch (e) {} }\n    v.sendGain = null;\n    if (v.analyser) { try { v.analyser.disconnect(); } catch (e) {} }\n    v.analyser = null;\n    if (v.audio) { try { v.audio.close(); } catch (e) {} }\n    v.audio = null; v.active = false; v.state = 0;\n    v.queue.length = 0;\n  };\n  v.transmit = (talking) => {\n    if (v.sendGain && v.active) v.sendGain.gain.value = talking ? 1 : 0;\n  };\n  v.level = () => {\n    if (!v.analyser) return 0;\n    const a = new Uint8Array(v.analyser.fftSize);\n    v.analyser.getByteTimeDomainData(a);\n    let energy = 0;\n    for (const n of a) { const x = (n - 128) / 128; energy += x*x; }\n    return Math.sqrt(energy/a.length);\n  };\n  v.openPeer = (id, initiator) => {\n    if (!v.active || !v.sendStream || v.peers.has(id)) return;\n    let connection;\n    try {\n      connection = new RTCPeerConnection({iceServers:v.iceServers});\n    } catch (e) { push(\"closed\", id, \"create\"); return; }\n    const p = {connection:connection, source:null, gain:null, panner:null};\n    v.peers.set(id, p);\n    v.sendStream.getTracks().forEach((track) => connection.addTrack(track,v.sendStream));\n    connection.onicecandidate = (event) => {\n      if (!event.candidate || !v.peers.has(id)) return;\n      const c = event.candidate;\n      push(\"ice\", id, JSON.stringify({\n        candidate:c.candidate, sdpMLineIndex:String(c.sdpMLineIndex)\n      }));\n    };\n    connection.ontrack = (event) => {\n      if (!v.audio || !v.peers.has(id) || !event.streams.length) return;\n      try {\n        p.source = v.audio.createMediaStreamSource(event.streams[0]);\n        p.gain = v.audio.createGain();\n        p.panner = v.audio.createPanner();\n        p.panner.panningModel = \"HRTF\";\n        p.panner.distanceModel = \"linear\";\n        p.panner.refDistance = v.global ? 100000 : 1;\n        p.panner.maxDistance = v.global ? 100000 : 32;\n        p.panner.rolloffFactor = 1;\n        p.gain.gain.value = v.volume;\n        p.source.connect(p.gain);\n        p.gain.connect(p.panner);\n        p.panner.connect(v.audio.destination);\n        push(\"peeropen\", id, \"\");\n      } catch (e) { push(\"closed\", id, \"audio\"); }\n    };\n    connection.onconnectionstatechange = () => {\n      if (connection.connectionState === \"failed\" ||\n          connection.connectionState === \"closed\" ||\n          connection.connectionState === \"disconnected\") {\n        closePeer(id, true);\n      }\n    };\n    if (initiator) {\n      connection.createOffer().then((desc)=>connection.setLocalDescription(desc)\n        .then(()=>push(\"description\",id,JSON.stringify(desc))))\n        .catch(()=>closePeer(id,true));\n    }\n  };\n  v.description = (id, serialized) => {\n    const p = v.peers.get(id); if (!p) return;\n    let description;\n    try { description = JSON.parse(serialized); } catch(e) { closePeer(id,true); return; }\n    p.connection.setRemoteDescription(description).then(() => {\n      if (description.type === \"offer\") {\n        return p.connection.createAnswer().then((answer) =>\n          p.connection.setLocalDescription(answer).then(()=>\n            push(\"description\",id,JSON.stringify(answer))));\n      }\n    }).catch(()=>closePeer(id,true));\n  };\n  v.ice = (id, serialized) => {\n    const p = v.peers.get(id); if (!p) return;\n    try {\n      p.connection.addIceCandidate(new RTCIceCandidate(JSON.parse(serialized)))\n        .catch(()=>closePeer(id,true));\n    } catch(e) { closePeer(id,true); }\n  };\n  v.closePeer = (id) => closePeer(id,false);\n  v.position = (id,x,y,z) => {\n    const p = v.peers.get(id); if (!p || !p.panner) return;\n    if (p.panner.positionX) {\n      p.panner.positionX.value=x; p.panner.positionY.value=y;p.panner.positionZ.value=z;\n    } else { p.panner.setPosition(x,y,z); }\n  };\n  v.direction = (yaw) => {\n    if (!v.audio) return;\n    const r = yaw*Math.PI/180;\n    const listener=v.audio.listener;\n    const fx=-Math.sin(r),fz=Math.cos(r);\n    if (listener.forwardX) {\n      listener.forwardX.value=fx;\n      listener.forwardY.value=0;\n      listener.forwardZ.value=fz;\n    } else if (listener.setOrientation) {\n      listener.setOrientation(fx,0,fz,0,1,0);\n    }\n  };\n  v.setGlobal = (enabled) => {\n    v.global=!!enabled;\n    for (const p of v.peers.values()) {\n      if (p.panner) {\n        p.panner.refDistance=v.global ? 100000 : 1;\n        p.panner.maxDistance=v.global ? 100000 : 32;\n      }\n    }\n  };\n  v.setVolume = (volume) => {\n    v.volume=Math.max(0,Math.min(2,volume));\n    for (const p of v.peers.values()) if(p.gain)p.gain.gain.value=v.volume;\n  };\n  v.poll = () => v.queue.length ? v.queue.shift() : \"\";\n  globalThis.__pletzelEaglerVoice=v;\n})();")
   public static native void initialize();

   @JSBody(script = "return !!globalThis.__pletzelEaglerVoice && globalThis.__pletzelEaglerVoice.supported();")
   public static native boolean supported();

   @JSBody(params = {"servers"}, script = "globalThis.__pletzelEaglerVoice.configure(servers);")
   public static native void configure(String servers);

   @JSBody(script = "globalThis.__pletzelEaglerVoice.enable();")
   public static native void enable();

   @JSBody(script = "if(globalThis.__pletzelEaglerVoice)globalThis.__pletzelEaglerVoice.stop();")
   public static native void stop();

   @JSBody(script = "return globalThis.__pletzelEaglerVoice.state;")
   public static native int status();

   @JSBody(params = {"talk"}, script = "globalThis.__pletzelEaglerVoice.transmit(talk);")
   public static native void transmit(boolean talk);

   @JSBody(script = "return globalThis.__pletzelEaglerVoice.level();")
   public static native double microphoneLevel();

   @JSBody(params = {"id","offer"}, script = "globalThis.__pletzelEaglerVoice.openPeer(id,offer);")
   public static native void openPeer(String id, boolean offer);

   @JSBody(params = {"id","desc"}, script = "globalThis.__pletzelEaglerVoice.description(id,desc);")
   public static native void description(String id, String desc);

   @JSBody(params = {"id","candidate"}, script = "globalThis.__pletzelEaglerVoice.ice(id,candidate);")
   public static native void ice(String id, String candidate);

   @JSBody(params = {"id"}, script = "globalThis.__pletzelEaglerVoice.closePeer(id);")
   public static native void closePeer(String id);

   @JSBody(params = {"id","x","y","z"}, script = "globalThis.__pletzelEaglerVoice.position(id,x,y,z);")
   public static native void position(String id, double x, double y, double z);

   @JSBody(params = {"yaw"}, script = "globalThis.__pletzelEaglerVoice.direction(yaw);")
   public static native void direction(double yaw);

   @JSBody(params = {"global"}, script = "globalThis.__pletzelEaglerVoice.setGlobal(global);")
   public static native void globalChannel(boolean global);

   @JSBody(params = {"volume"}, script = "globalThis.__pletzelEaglerVoice.setVolume(volume);")
   public static native void volume(double volume);

   @JSBody(script = "return globalThis.__pletzelEaglerVoice.poll();")
   public static native String poll();
}

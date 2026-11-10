#!/usr/bin/env python3
"""Supplemental REAL Chromium WebRTC audio plumbing test.

Two independent Chromium pages, real RTCPeerConnection, real Web Audio
MediaStream graph, browser getUserMedia using Chrome's explicitly marked
SYNTHETIC TEST MICROPHONE. No Pletzel voice gateway; signaling is passed
in the exact EaglerX ICE/description JSON envelopes by the test runner.
THIS IS NOT TESTING AN EXISTING EAGLER SERVER OR AN OLDER EAGLER CLIENT.
"""
import re,json,time,traceback,http.server,threading,sys,math,wave,struct,random
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright

java=Path("pletzel-v4/eaglerx-voice/PlatformEaglerVoice26.java").read_text()
match=re.search(r'@JSBody\(script = ("(?:\\.|[^"\\])*")\)',java,re.S)
assert match, "Could not extract exact browser WebRTC implementation"
engine=json.loads(match.group(1))
assert "RTCPeerConnection" in engine and "getUserMedia" in engine
out=Path("eagler-voice-webrtc-browser-evidence");out.mkdir(exist_ok=True)
events=[];data={"note":"Controlled synthetic microphone only; NOT older-client compatibility","steps":[]}
with TemporaryDirectory() as tmp:
 # Feed a deterministic non-silent speech-like PCM waveform to Chrome's
 # FAKE microphone instead of its often-silent default test device.
 # This verifies actual RTP/audio transport without using a real voice recording.
 pcm=Path(tmp,"voice-test-input.wav")
 samplerate=48000
 rng=random.Random(1808)
 samples=[]
 for i in range(samplerate*4):
  t=i/samplerate
  envelope=(0.40+0.60*abs(math.sin(2*math.pi*3.4*t)))
  f0=145+85*math.sin(2*math.pi*1.8*t)
  wave_sample=(0.42*math.sin(2*math.pi*f0*t)
      +0.24*math.sin(2*math.pi*(f0*2.1)*t)
      +0.15*math.sin(2*math.pi*(f0*4.3)*t)
      +0.10*rng.uniform(-1,1))*envelope
  samples.append(struct.pack("<h",int(max(-1,min(1,wave_sample))*25000)))
 with wave.open(str(pcm),"wb") as wf:
  wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(samplerate)
  wf.writeframes(b"".join(samples))
 data["synthetic_input"]={"kind":"deterministic speech-like PCM","sampleRate":samplerate,
     "durationSeconds":4,"fileBytes":pcm.stat().st_size}
 Path(tmp,"index.html").write_text('<!doctype html><html><body><button id="enable" onclick="globalThis.__pletzelEaglerVoice.enable()">Enable microphone for controlled test</button></body></html>')
 class Handler(http.server.SimpleHTTPRequestHandler):
  def __init__(self,*args,**kwargs):super().__init__(*args,directory=tmp,**kwargs)
  def log_message(self,*args):pass
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 error=None
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,args=[
    "--no-sandbox","--disable-dev-shm-usage","--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream","--autoplay-policy=no-user-gesture-required",
    "--use-file-for-fake-audio-capture="+str(pcm),
    "--enable-unsafe-swiftshader"])
   contexts=[browser.new_context(),browser.new_context()]
   pages=[ctx.new_page() for ctx in contexts]
   for idx,page in enumerate(pages):
    page.on("pageerror",lambda ex,idx=idx:events.append({"page":idx,"error":str(ex)}))
    page.goto(f"http://127.0.0.1:{server.server_address[1]}/index.html",wait_until="domcontentloaded")
    page.evaluate(engine)
    page.evaluate("globalThis.__pletzelEaglerVoice.configure('[]')")
    assert page.evaluate("globalThis.__pletzelEaglerVoice.supported()"),"Browser media subsystem unavailable"
    assert page.evaluate("globalThis.__pletzelEaglerVoice.status ? globalThis.__pletzelEaglerVoice.status : globalThis.__pletzelEaglerVoice.state")==0
    page.locator("#enable").click()
   for p in pages:
    p.wait_for_function("globalThis.__pletzelEaglerVoice.state===2",timeout=30000)
    assert p.evaluate("globalThis.__pletzelEaglerVoice.stream.getAudioTracks()[0].readyState")== "live"
    assert p.evaluate("globalThis.__pletzelEaglerVoice.sendGain.gain.value")==0
   data["steps"].append("Both real browser microphone streams granted after test button; outgoing gain zero by default")
   a,b=pages
   a.evaluate("globalThis.__pletzelEaglerVoice.openPeer('B',true)")
   b.evaluate("globalThis.__pletzelEaglerVoice.openPeer('A',false)")
   connected=False
   deadline=time.monotonic()+40
   while time.monotonic()<deadline:
    for source,target,targetId in [(a,b,"A"),(b,a,"B")]:
     packets=source.evaluate("""() => {
      let arr=[];for(let n=0;n<80;n++) {
       let x=globalThis.__pletzelEaglerVoice.poll();
       if (!x)break;arr.push(JSON.parse(x));
      }
      return arr;
     }""")
     for packet in packets:
      if packet["kind"] in ("ice","description"):
       target.evaluate("""([kind,id,payload]) => {
        const v=globalThis.__pletzelEaglerVoice;
        if(kind==='ice')v.ice(id,payload);
        else v.description(id,payload);
       }""",[packet["kind"],targetId,packet["data"]])
    states=[p.evaluate("""() => {
     const v=globalThis.__pletzelEaglerVoice;
     const peer=Array.from(v.peers.values())[0];
     return peer?peer.connection.connectionState:"missing";
    }""") for p in pages]
    if states==["connected","connected"]:
     connected=True;break
    time.sleep(0.15)
   data["connection_states"]=states
   assert connected, "Real WebRTC peer connections failed to establish"
   data["steps"].append("Two independent Chromium RTCPeerConnections established using exact Eagler ICE/SDP strings")
   b.evaluate("""async () => {
      const p=Array.from(globalThis.__pletzelEaglerVoice.peers.values())[0];
      const track=p.connection.getReceivers().map(r=>r.track).find(t=>t.kind==='audio');
      if(!track)throw Error('Remote audio track missing');
      const ctx=new AudioContext();
      await ctx.resume();
      const source=ctx.createMediaStreamSource(new MediaStream([track]));
      const analyser=ctx.createAnalyser();analyser.fftSize=256;
      source.connect(analyser);
      globalThis.__voiceTestReceiver={ctx,source,analyser};
    }""")
   samplescript="""async () => {
       const analyser=globalThis.__voiceTestReceiver.analyser;
       const a=new Uint8Array(analyser.fftSize);
       const samples=[];
       for(let i=0;i<35;i++) {
        analyser.getByteTimeDomainData(a);
        let sum=0;for(let v of a){let x=(v-128)/128;sum+=x*x;}
        samples.push(Math.sqrt(sum/a.length));
        await new Promise(r=>setTimeout(r,30));
       }
       return samples.reduce((a,b)=>a+b,0)/samples.length;
   }"""
   def rtp_stats(page):
    return page.evaluate("""async () => {
      const peers=Array.from(globalThis.__pletzelEaglerVoice.peers.values());
      if(!peers.length)return {error:"no peer"};
      const conn=peers[0].connection;
      const stats=await conn.getStats();
      const ret={};
      stats.forEach(item=>{
        if((item.type==='inbound-rtp'||item.type==='outbound-rtp') &&
           (item.kind==='audio'||item.mediaType==='audio')) {
          ret[item.type]={bytesSent:item.bytesSent||0,bytesReceived:item.bytesReceived||0,
            packetsSent:item.packetsSent||0,packetsReceived:item.packetsReceived||0,
            audioLevel:item.audioLevel??null,totalAudioEnergy:item.totalAudioEnergy??null,
            trackIdentifier:item.trackIdentifier||null};
        }
      });
      ret.contextState=globalThis.__pletzelEaglerVoice.audio?.state||"none";
      ret.captureTracks=globalThis.__pletzelEaglerVoice.stream?.getAudioTracks().map(t=>({
        state:t.readyState,enabled:t.enabled,muted:t.muted}))||[];
      ret.transmissionGain=globalThis.__pletzelEaglerVoice.sendGain?.gain?.value;
      ret.remoteAudioEvents=globalThis.__pletzelEaglerVoice.queue.filter(q=>q.includes("peeropen")).length;
      return ret;
    }""")
   data["rtp_before"]={"sender":rtp_stats(a),"receiver":rtp_stats(b)}
   off=b.evaluate(samplescript)
   a.evaluate("globalThis.__pletzelEaglerVoice.transmit(true)")
   time.sleep(0.3)
   on=b.evaluate(samplescript)
   data["rtp_during"]={"sender":rtp_stats(a),"receiver":rtp_stats(b)}
   data["sender_audio_signal"] = a.evaluate("""async () => {
     const v=globalThis.__pletzelEaglerVoice;
     const analyser=v.audio.createAnalyser();
     analyser.fftSize=256;
     const source=v.audio.createMediaStreamSource(v.sendStream);
     source.connect(analyser);
     const a=new Uint8Array(analyser.fftSize);
     let fromMic=[],fromOutgoing=[];
     for(let i=0;i<35;i++) {
       fromMic.push(v.level());
       analyser.getByteTimeDomainData(a);
       let power=0;
       for(let x of a){const y=(x-128)/128;power+=y*y;}
       fromOutgoing.push(Math.sqrt(power/a.length));
       await new Promise(r=>setTimeout(r,30));
     }
     source.disconnect();
     analyser.disconnect();
     return {
       rawMicrophoneAverage:fromMic.reduce((sum,x)=>sum+x,0)/fromMic.length,
       gatedOutboundAverage:fromOutgoing.reduce((sum,x)=>sum+x,0)/fromOutgoing.length,
       microphoneTrackSettings:v.stream.getAudioTracks().map(t=>t.getSettings()),
       outgoingTracks:v.sendStream.getAudioTracks().map(t=>({
         enabled:t.enabled,muted:t.muted,readyState:t.readyState
       }))
     };
   }""")

   a.evaluate("globalThis.__pletzelEaglerVoice.transmit(false)")
   time.sleep(0.3)
   off_again=b.evaluate(samplescript)
   data["rtp_after"]={"sender":rtp_stats(a),"receiver":rtp_stats(b)}
   data["rms"]={"initial_silence":off,"transmitting_synthetic_audio":on,"muted_again":off_again}
   data["steps"].append("Measured received real-WebRTC audio RMS before, during and after push-to-talk")
   assert on>max(0.002,off*2),"No audio increase when transmitting"
   assert off_again<max(0.005,on*0.35),"Mute did not silence received audio"
   for p in pages:
    p.evaluate("globalThis.__pletzelEaglerVoice.stop()")
    assert p.evaluate("globalThis.__pletzelEaglerVoice.state")==0
    assert p.evaluate("globalThis.__pletzelEaglerVoice.peers.size")==0
   data["steps"].append("Both browser microphone tracks and peers closed on stop")
   assert not events,events
   for ctx in contexts:ctx.close()
   browser.close()
 except Exception:
  error=traceback.format_exc();data["error"]=error
 finally:server.shutdown()
(out/"result.json").write_text(json.dumps(data,indent=2))
print("WEBRTC_SYNTHETIC_INPUT_RESULT",json.dumps(data)[:7000],flush=True)
if data.get("error"):sys.exit(2)
print("PASS: two REAL WebRTC peers, mic/track and gain-gate lifecycle; NOT cross-client proof",flush=True)

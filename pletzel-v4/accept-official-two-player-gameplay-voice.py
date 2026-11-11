#!/usr/bin/env python3
"""Fail-closed real Paper 26.2 + official EaglerXServer V5 browser acceptance.

Tests the EXACT compiled Pletzel HTML, two independent real Chromium clients,
server-authoritative RCON positions and genuine decoded WebRTC audio. It does
not create Minecraft GUI overlays, synthesize login status or mock server data.
"""
import http.server,json,re,subprocess,threading,time,traceback,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

htmls=list(Path("candidate").rglob("*.html"))
assert len(htmls)==1,htmls
html=htmls[0].resolve()
out=Path("official-two-player-acceptance-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent),**kw)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic();events=[[],[]];shots=[];evidence={};fault=None
def snap(page,name):
 dest=out/(name+".png");page.screenshot(path=str(dest),timeout=60000)
 shots.append({"name":name,"seconds":round(time.monotonic()-start,2)})
 print("OFFICIAL_GAME_SCREENSHOT",name,flush=True)
def server_command(command):
 assert command=="list" or command.startswith("data get entity ")
 p=subprocess.run(["docker","exec","pletzel-official-voice-ci","python3",
    "/tmp/pletzel-rcon.py",command],capture_output=True,text=True,timeout=45)
 if p.returncode!=0:raise RuntimeError("Actual Paper RCON query failed: "+p.stderr[-600:])
 data=json.loads(p.stdout.strip().splitlines()[-1])
 assert data.get("source")=="real Paper 26.2 RCON",data
 return data.get("response","")
def server_position(username):
 ans=server_command("data get entity "+username+" Pos")
 nums=re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",ans.split("[")[-1])
 if len(nums)<3:raise AssertionError("No Paper authoritative coordinates for "+username+": "+ans)
 return [float(v) for v in nums[:3]]
def username(events_one):
 for e in events_one:
  m=re.search(r"Setting user:\s+([A-Za-z0-9_]{3,16})",e["text"])
  if m:return m.group(1)
 raise AssertionError("Actual Java player profile username not seen")
def verify_admitted(name):
 response=server_command("list")
 print("PAPER_REAL_PLAYER_LIST",response,flush=True)
 if name not in response:raise AssertionError(name+" not present in actual Paper multiplayer player list: "+response)
def audio_stats(page):
 return page.evaluate("""async () => {
  const v=globalThis.__pletzelEaglerVoice;
  if (!v) return {error:'no native voice platform'};
  const peers=[];
  for(const [id,peer] of v.peers){
    const stats=await peer.connection.getStats();
    let inboundEnergy=0,received=0,samples=0,outbound=0;
    for(const s of stats.values()){
      if(s.type==='inbound-rtp' && (s.kind==='audio'||s.mediaType==='audio')){
        received+=s.packetsReceived||0;
        inboundEnergy+=s.totalAudioEnergy||0;
        samples+=s.totalSamplesReceived||0;
      }
      if(s.type==='outbound-rtp' && (s.kind==='audio'||s.mediaType==='audio')){
        outbound+=s.packetsSent||0;
      }
    }
    peers.push({id,connectionState:peer.connection.connectionState,
      inboundEnergy,received,samples,outbound,hasPlayback:!!peer.playback});
  }
  return {state:v.state,active:v.active,transmitGain:v.sendGain?.gain.value||0,
          liveTracks:v.stream?.getTracks().filter(t=>t.readyState==='live').length||0,peers};
}""")
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage",
   "--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
   "--use-gl=desktop","--disable-features=Vulkan",
   "--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream",
   "--autoplay-policy=no-user-gesture-required"])
  pages=[]
  for idx in range(2):
   context=browser.new_context(viewport={"width":1280,"height":720},permissions=["microphone"])
   page=context.new_page();pages.append(page)
   # Observe the *actual* browser WebSocket handshake on a real official
   # server. Log only short protocol headers (first 8 bytes), never auth
   # strings, tokens, skin data, microphone packets, SDP or ICE secrets.
   def attach_websocket(ws,idx=idx):
    if not ws.url.startswith("ws://127.0.0.1:5200"):return
    def capture(direction,payload):
     if not isinstance(payload,bytes) or not payload:return
     if len(events[idx])>15000:return
     if payload[0] not in (0x01,0x02,0x03,0x04,0x05,0x06,0xff):return
     event={"at":round(time.monotonic()-start,2),"kind":"official-v5-wire-"+direction,
            "length":len(payload),"packet":payload[0],"header8":payload[:8].hex()}
     events[idx].append(event)
     print("V5_NATIVE_WIRE_HEADER",json.dumps({"page":idx,**event}),flush=True)
    ws.on("framesent",lambda buf:capture("sent",buf))
    ws.on("framereceived",lambda buf:capture("received",buf))
   page.on("websocket",attach_websocket)
   page.on("console",lambda m,idx=idx:events[idx].append({"at":round(time.monotonic()-start,2),
       "kind":m.type,"text":m.text[:1800]}))
   page.on("pageerror",lambda e,idx=idx:events[idx].append({"at":round(time.monotonic()-start,2),
       "kind":"pageerror","text":str(e)[:1800]}))
   page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{html.name}?perfdebug",
             wait_until="domcontentloaded",timeout=180000)
   page.wait_for_timeout(30000)
   page.mouse.click(638,618);page.wait_for_timeout(3200)
   page.mouse.click(638,572);page.wait_for_timeout(4300)
   snap(page,f"{idx}-actual-title")
   page.mouse.click(638,426);page.wait_for_timeout(4300)
   page.mouse.click(400,566);page.wait_for_timeout(8000)
   snap(page,f"{idx}-actual-multiplayer-list")
   page.mouse.click(638,593);page.wait_for_timeout(3000)
   page.keyboard.type("ws://127.0.0.1:5200",delay=45)
   page.keyboard.press("Enter")
   name=username(events[idx])
   for attempt in range(35):
    page.wait_for_timeout(4000)
    response=server_command("list")
    if name in response:break
    if any("Couldn't connect to server" in e["text"] or
           "Eagler server rejected login" in e["text"] for e in events[idx]):
      break
   snap(page,f"{idx}-actual-server-join")
   verify_admitted(name)
   pages[-1].wait_for_timeout(6000)
   evidence[f"player_{idx}"]={"username":name,"paper_join":"confirmed",
      "position":server_position(name)}
   print("PAPER_ACTUAL_LOGIN_CONFIRMED",idx,name,evidence[f"player_{idx}"],flush=True)
  # Deliberately exercise real movement and compare with Paper RCON's
  # post-movement authoritative coordinates, not local browser pixels.
  page=pages[0];name=evidence["player_0"]["username"]
  before=server_position(name)
  page.keyboard.down("w");page.wait_for_timeout(7200);page.keyboard.up("w")
  page.wait_for_timeout(4000)
  after=server_position(name)
  delta=sum((b-a)**2 for a,b in zip(before,after))**0.5
  evidence["actual_movement"]={"before":before,"after":after,"delta_blocks":delta}
  print("PAPER_SERVER_AUTHORITATIVE_MOVEMENT",json.dumps(evidence["actual_movement"]),flush=True)
  snap(page,"player0-after-authoritative-movement")
  assert delta>0.15,"RCON position unchanged despite native W movement"
  # Only the actual native Minecraft V menu may request microphone permission.
  # A WebSocket connection or custom browser JS calling enable() is not proof.
  for idx,page in enumerate(pages):
   page.keyboard.press("v");page.wait_for_timeout(3200)
   snap(page,f"{idx}-native-eaglerx-v5-voice-screen")
   page.mouse.click(640,245);page.wait_for_timeout(7500)
   s=audio_stats(page)
   evidence[f"voice_{idx}_enabled"]=s
   print("OFFICIAL_V5_NATIVE_VOICE_ENABLED",idx,json.dumps(s),flush=True)
   assert s.get("state")==2 and s.get("liveTracks",0)>0, \
     "Official server voice was not enabled via native V menu and real mic"
   page.mouse.click(640,420);page.wait_for_timeout(2100)
  # Official peer signaling can lag under software WebGL; require actual
  # RTCPeerConnection objects and connected or connecting state.
  for _ in range(20):
   page0,page1=(audio_stats(p) for p in pages)
   if page0.get("peers") and page1.get("peers"):break
   pages[0].wait_for_timeout(2500)
  evidence["peer0"]=page0;evidence["peer1"]=page1
  print("OFFICIAL_V5_PEER_SIGNALING",json.dumps({"a":page0,"b":page1}),flush=True)
  assert page0.get("peers") and page1.get("peers"), \
    "No official EaglerXServer V5 WebRTC peers after both native clients enabled"
  pages[0].wait_for_timeout(7000)
  baseline=audio_stats(pages[1])
  pages[0].keyboard.down("r")
  pages[0].wait_for_timeout(12000)
  transmitting=audio_stats(pages[0])
  on=audio_stats(pages[1])
  pages[0].keyboard.up("r")
  pages[0].wait_for_timeout(5000)
  offbase=audio_stats(pages[1])
  pages[0].wait_for_timeout(8000)
  off=audio_stats(pages[1])
  def sums(s,key):return sum(float(p.get(key,0)) for p in s.get("peers",[]))
  on_power=sums(on,"inboundEnergy")-sums(baseline,"inboundEnergy")
  off_power=sums(off,"inboundEnergy")-sums(offbase,"inboundEnergy")
  evidence["RTP_audio"]={"before":baseline,"duringPTT":on,"senderPTT":transmitting,
     "afterRelease":off,"on_energy_delta":on_power,"off_energy_delta":off_power}
  print("OFFICIAL_V5_REAL_AUDIO_RTP",json.dumps(evidence["RTP_audio"])[:8000],flush=True)
  assert transmitting["transmitGain"]>0.9,"Actual Minecraft PTT R did not enable mic track"
  assert sums(on,"received")>sums(baseline,"received"),"No inbound real WebRTC audio RTP"
  assert on_power>max(0.01,off_power*4),"No actual decoded voice audio rise with PTT"
  assert off_power<on_power*0.25,"Received audio not muted after PTT was released"
  snap(pages[0],"player0-voice-PTT-after-transmit")
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("OFFICIAL_V5_COMPLETE_ACCEPTANCE_FAIL",fault[-4800:],flush=True)
finally:srv.shutdown()
result={"hash_provenance":"workflow pins exact HTML sha256 independently",
 "elapsed_seconds":round(time.monotonic()-start,2),"evidence":evidence,
 "screenshots":shots,"fault":fault,
 "page_errors":[e for group in events for e in group if e["kind"]=="pageerror"],
 "limitations":["No older EaglerX client with protocol 776 available; cross-client interop remains BLOCKED",
                 "GitHub Ubuntu Chromium Xvfb is not the user's physical Mac"]}
(out/"result.json").write_text(json.dumps(result,indent=2))
for idx,group in enumerate(events):(out/f"client-{idx}-events.json").write_text(json.dumps(group,indent=2))
print("OFFICIAL_V5_COMPLETE_ACCEPTANCE_RESULT",json.dumps({"fault":fault,"evidence":list(evidence),"screens":len(shots)}),flush=True)
if fault or result["page_errors"]:sys.exit(2)
print("PASS: actual official v5 server + native two-client join + authoritative movement + received PTT audio",flush=True)

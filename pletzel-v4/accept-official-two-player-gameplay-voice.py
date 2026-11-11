#!/usr/bin/env python3
"""Fail-closed real Paper 26.2 + official EaglerXServer V5 browser acceptance.

Tests the EXACT compiled Pletzel HTML, two independent real Chromium clients,
server-authoritative RCON positions and genuine decoded WebRTC audio. It does
not create Minecraft GUI overlays, synthesize login status or mock server data.
"""
import http.server,json,re,subprocess,threading,time,traceback,sys,shutil,base64,io
from PIL import Image
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
def observed_profile_names(events_one):
 # The game may initialize and change its local profile more than once.
 # Do not confuse the first startup log with the name Paper admitted.
 names=[]
 for e in events_one:
  m=re.search(r"Setting user:\s+([A-Za-z0-9_]{3,16})",e.get("text", ""))
  if m and m.group(1) not in names:names.append(m.group(1))
 return names
def listed_players():
 response=server_command("list")
 m=re.search(r"players online:\s*(.*)$",response,re.I)
 assert m is not None,"Unexpected live Paper RCON player-list format: "+response
 names=[n.strip() for n in m.group(1).split(",") if n.strip()]
 assert all(re.fullmatch(r"[A-Za-z0-9_]{3,16}",n) for n in names),response
 return set(names)
def verify_admitted(name):
 players=listed_players()
 print("PAPER_REAL_PLAYER_LIST",sorted(players),flush=True)
 if name not in players:raise AssertionError(name+" not present in actual Paper multiplayer player list: "+str(sorted(players)))
def username_notice_visible(page):
 # Genuine first-run 'Default Username Detected' has TWO 600px-wide
 # gray controls at y=480 and y=575, spanning x=370..905.
 # Check actual screenshots, not mock GUI state or noisy startup logs.
 frame=page.screenshot(type="jpeg",quality=40,timeout=30000)
 img=Image.open(io.BytesIO(frame)).convert("RGB")
 return all(sum(img.getpixel(pt))>285 for pt in
            ((370,480),(905,480),(370,575),(905,575)))
def dismiss_username_notice(page,idx,stage):
 for attempt in range(12):
  if not username_notice_visible(page):break
  print("OFFICIAL_FIRST_RUN_NOTICE",idx,stage,attempt,flush=True)
  snap(page,f"{idx}-{stage}-username-dialog-{attempt}")
  page.mouse.click(640,575) # Actual 'Continue Anyway'
  page.wait_for_timeout(2800)
 assert not username_notice_visible(page), (
  f"Browser {idx} is still blocked by native username-onboarding during {stage}")
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
  # Prefer the actual preinstalled Ubuntu Chrome. Playwright falls back
  # to its downloaded Chromium only on a runner without system Chrome.
  chrome=shutil.which("google-chrome") or shutil.which("google-chrome-stable")
  browser=pw.chromium.launch(headless=False,executable_path=chrome,args=["--no-sandbox","--disable-dev-shm-usage",
   "--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
   "--use-gl=desktop","--disable-features=Vulkan",
   "--disable-background-timer-throttling","--disable-backgrounding-occluded-windows",
   "--disable-renderer-backgrounding",
   "--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream",
   "--autoplay-policy=no-user-gesture-required"])
  pages=[];connected_players=listed_players()
  assert not connected_players, ("The isolated Paper backend was not empty at test start",connected_players)
  for idx in range(2):
   context=browser.new_context(viewport={"width":1280,"height":720},permissions=["microphone"])
   page=context.new_page();pages.append(page);page.bring_to_front()
   # Observe the *actual* browser WebSocket handshake on a real official
   # server. Log only short protocol headers (first 8 bytes), never auth
   # strings, tokens, skin data, microphone packets, SDP or ICE secrets.
   def attach_websocket(ws,idx=idx):
    events[idx].append({"at":round(time.monotonic()-start,2),
       "kind":"websocket-open","text":ws.url[:180]})
    if not ws.url.startswith("ws://127.0.0.1:5200"):return
    def capture(direction,payload):
     if not isinstance(payload,bytes) or not payload:return
     if len(events[idx])>15000:return
     # After login, log native voice 0xEE without noisy gameplay traffic.
     admitted=any(e.get("server_assigned_username") for e in events[idx])
     if admitted and payload[0] not in (0xEE,0xff):return
     if payload[0] not in (0x01,0x02,0x03,0x04,0x05,0x06,0xEE,0xff):return
     event={"at":round(time.monotonic()-start,2),"kind":"official-v5-wire-"+direction,
            "length":len(payload),"packet":payload[0],"header8":payload[:8].hex()}
     # Official V3–V5 deny packets use U16 UTF-8 message length. Log only
     # the public server denial reason; never record handshake auth material.
     if direction=="received" and payload[0] in (0x06,0xff) and len(payload)>=4:
      off=1 if payload[0]==0x06 else 2
      if len(payload)>=off+2:
       n=int.from_bytes(payload[off:off+2],"big")
       if n<=len(payload)-off-2:
        event["server_denial"]=payload[off+2:off+2+min(n,200)].decode("utf-8","replace")
     # V5 ALLOW_LOGIN (0x05) contains the SERVER-ASSIGNED public name.
     # Correlate this native wire identity with the actual Paper RCON login.
     if direction=="received" and payload[0]==0x05 and len(payload)>2:
      n=payload[1]
      if n<128 and len(payload)>=2+n:
       assigned=payload[2:2+n].decode("ascii","replace")
       if re.fullmatch(r"[A-Za-z0-9_]{3,16}",assigned):
        event["server_assigned_username"]=assigned
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
   # First-run dialog sometimes paints AFTER the original blind clicks.
   # Wait for the real profile and dismiss the actual wide-button prompt.
   profile_ready=False
   for init in range(28):
    if username_notice_visible(page):
     dismiss_username_notice(page,idx,"startup")
     profile_ready=True
     page.wait_for_timeout(3500)
     break
    if observed_profile_names(events[idx]):
     profile_ready=True
     page.wait_for_timeout(3500)
     dismiss_username_notice(page,idx,"late-startup")
     break
    page.wait_for_timeout(2700)
   assert profile_ready, f"Browser {idx} never reached a real player profile"
   page.wait_for_timeout(3500)
   dismiss_username_notice(page,idx,"before-title")
   snap(page,f"{idx}-actual-title")
   reached_direct_connect=False
   for nav_attempt in range(4):
    dismiss_username_notice(page,idx,f"before-multiplayer-{nav_attempt}")
    page.mouse.click(638,426);page.wait_for_timeout(4500)
    if username_notice_visible(page):
     dismiss_username_notice(page,idx,f"multiplayer-interrupt-{nav_attempt}")
     continue
    page.mouse.click(400,566);page.wait_for_timeout(7000)
    if username_notice_visible(page):
     dismiss_username_notice(page,idx,f"list-interrupt-{nav_attempt}")
     continue
    snap(page,f"{idx}-actual-multiplayer-list")
    page.mouse.click(638,593);page.wait_for_timeout(3200)
    if username_notice_visible(page):
     dismiss_username_notice(page,idx,f"connect-interrupt-{nav_attempt}")
     continue
    page.keyboard.type("ws://127.0.0.1:5200",delay=45)
    page.keyboard.press("Enter")
    for observe in range(12):
     page.wait_for_timeout(2500)
     if any(e.get("kind")=="websocket-open" and "127.0.0.1:5200" in e.get("text","")
            for e in events[idx]):
      reached_direct_connect=True
      break
     if username_notice_visible(page):
      dismiss_username_notice(page,idx,f"login-interrupt-{nav_attempt}")
      break
    if reached_direct_connect:break
    print("OFFICIAL_GUI_NAVIGATION_RETRY",idx,nav_attempt,flush=True)
    page.keyboard.press("Escape");page.wait_for_timeout(1400)
    page.keyboard.press("Escape");page.wait_for_timeout(1400)
   assert reached_direct_connect, (
     f"Browser {idx} never opened its real WebSocket after native multiplayer UI")
   print("OFFICIAL_REAL_WEBSOCKET_FROM_GAME_GUI",idx,flush=True)
   # A startup 'Setting user:' log is NOT a trustworthy server identity:
   # prior runs selected the first bootstrap nickname and falsely rejected
   # an actual Paper admission under the final, regenerated profile name.
   # Require an exactly-one-player transition in the real RCON list, AND
   # keep all previously admitted players online during the transition.
   joined=set();players_before=set(connected_players)
   for attempt in range(35):
    page.wait_for_timeout(4000)
    now=listed_players()
    joined=now-players_before
    if len(joined)==1 and players_before.issubset(now):break
    if any("Couldn't connect to server" in e.get("text", "") or
           "Eagler server rejected login" in e.get("text", "") for e in events[idx]):
      break
   snap(page,f"{idx}-actual-server-join")
   if not joined:
    print("OFFICIAL_NO_NEW_PLAYER_BROWSER_EVENTS",json.dumps([
      e for e in events[idx] if e.get("kind") not in (
         "official-v5-wire-received","official-v5-wire-sent")][-100:])[:17000],flush=True)
    try:
     frame=page.screenshot(type="jpeg",quality=55,timeout=30000)
     print("OFFICIAL_FAILED_JOIN_SCREEN_JPEG_BASE64",
           base64.b64encode(frame).decode("ascii"),flush=True)
    except Exception as exc:
     print("OFFICIAL_FAILED_JOIN_SCREEN_ERROR",str(exc),flush=True)
   profiles=observed_profile_names(events[idx])
   print("PAPER_LOGIN_IDENTITY_TRACE",json.dumps({"page":idx,"profiles":profiles,
       "before":sorted(players_before),"new":sorted(joined),"now":sorted(now)}),flush=True)
   assert len(joined)==1 and now==players_before|joined, (
     f"Expected exactly one NEW Paper player for browser {idx}; "
     f"before={sorted(players_before)} after={sorted(now)} profiles={profiles}")
   assert any(e.get("kind")=="official-v5-wire-received" for e in events[idx]), (
     f"Browser {idx} did not receive native V5 WebSocket packets")
   name=next(iter(joined))
   assigned=[e.get("server_assigned_username") for e in events[idx]
             if e.get("server_assigned_username")]
   print("OFFICIAL_V5_SERVER_ASSIGNED_NAME",idx,assigned,flush=True)
   assert assigned and name==assigned[-1], (
      f"Actual Paper login {name} is not linked to browser {idx} V5 "
      f"ALLOW_LOGIN identity {assigned}")
   verify_admitted(name)
   connected_players.add(name)
   pages[-1].wait_for_timeout(6000)
   evidence[f"player_{idx}"]={"username":name,"paper_join":"confirmed",
      "browser_profile_names":profiles,"identity_verified_by":"unique live Paper RCON admission",
      "position":server_position(name)}
   print("PAPER_ACTUAL_LOGIN_CONFIRMED",idx,name,evidence[f"player_{idx}"],flush=True)
  # Deliberately exercise real movement and compare with Paper RCON's
  # post-movement authoritative coordinates, not local browser pixels.
  page=pages[0];name=evidence["player_0"]["username"]
  # Browser 1 was most recently brought to front for login. The two-player
  # headful Chrome test must first focus browser 0's real game canvas:
  # sending W into an occluded window is not evidence of Minecraft movement.
  before=server_position(name)
  movement_attempts=[]
  for movement_try in range(3):
   page.bring_to_front()
   page.mouse.click(640,360)
   page.wait_for_timeout(1500)
   page.keyboard.down("w")
   page.wait_for_timeout(5200)
   page.keyboard.up("w")
   page.wait_for_timeout(2500)
   after=server_position(name)
   delta=sum((b-a)**2 for a,b in zip(before,after))**0.5
   movement_attempts.append({"attempt":movement_try+1,"before":before,"after":after,"delta_blocks":delta})
   print("PAPER_MOVEMENT_FOCUSED_ATTEMPT",json.dumps(movement_attempts[-1]),flush=True)
   if delta>0.15:break
  evidence["actual_movement"]={"before":before,"after":after,"delta_blocks":delta,
     "attempts":movement_attempts}
  print("PAPER_SERVER_AUTHORITATIVE_MOVEMENT",json.dumps(evidence["actual_movement"]),flush=True)
  snap(page,"player0-after-authoritative-movement")
  assert delta>0.15,"RCON position unchanged despite foreground game-canvas W movement"
  # Only the actual native Minecraft V menu may request microphone permission.
  # A WebSocket connection or custom browser JS calling enable() is not proof.
  for idx,page in enumerate(pages):
   page.keyboard.press("v");page.wait_for_timeout(3200)
   snap(page,f"{idx}-native-eaglerx-v5-voice-screen")
   # Native EaglerXVoiceScreen: top=max(34,(guiHeight-290)/2), Enable
   # bounds top+20..top+40. Auto UI scale at 1280x720 is 3, so center
   # is (34+30)*3=192 physical pixels. 245 selected the mute row.
   # Global channel removes nondeterministic spawn-distance from the
   # first proof of real two-client WebRTC audio. Proximity is tested
   # separately after transport acceptance succeeds.
   page.mouse.click(640,336);page.wait_for_timeout(800)
   assert page.evaluate("!!globalThis.__pletzelEaglerVoice?.global"), "Native Channel: Global control did not select global voice"
   page.mouse.click(640,192);page.wait_for_timeout(7500)
   s=audio_stats(page)
   evidence[f"voice_{idx}_enabled"]=s
   print("OFFICIAL_V5_NATIVE_VOICE_ENABLED",idx,json.dumps(s),flush=True)
   assert s.get("state")==2 and s.get("liveTracks",0)>0, \
     "Official server voice was not enabled via native V menu and real mic"
   # Close via the REAL screen's onClose() rather than an ungrounded
   # physical Y=420 click (the Done button is lower at auto scale).
   page.keyboard.press("Escape");page.wait_for_timeout(2100)
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

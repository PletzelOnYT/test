#!/usr/bin/env python3
"""Real Pletzel V4 browser smoke: native warning/menu preserved, microphone
does not start when pressing V outside a voice-enabled multiplayer session.
This does NOT assert old-client interoperability or successful WebRTC audio.
"""
import http.server, threading, json, traceback, time, sys
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

files=list(Path("candidate").rglob("*.html"))
assert len(files)==1,files
html=files[0]
out=Path("eaglerx-v5-voice-browser-evidence")
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,directory=str(html.parent.resolve()),**kwargs)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[];screens=[];error=None
started=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=[
   "--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
   "--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop",
   "--disable-features=Vulkan"])
  context=browser.new_context(viewport={"width":1280,"height":720},device_scale_factor=1)
  context.add_init_script("""(() => {
   globalThis.__voiceTestMicRequests=0;
   if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia)return;
   const real=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
   navigator.mediaDevices.getUserMedia=(constraints)=>{
    globalThis.__voiceTestMicRequests++;
    return real(constraints);
   };
  })();""")
  page=context.new_page()
  page.on("console",lambda e:events.append({"kind":e.type,"message":e.text[:1200]}))
  page.on("pageerror",lambda e:events.append({"kind":"pageerror","message":str(e)[:2500]}))
  def snap(name,seconds=1):
   page.wait_for_timeout(int(seconds*1000))
   path=out/(name+".png")
   page.screenshot(path=str(path),timeout=30000)
   screens.append(name)
   print("NATIVE_EAGLER_VOICE_SMOKE",name,round(time.monotonic()-started,1),flush=True)
  page.goto(f"http://127.0.0.1:{server.server_address[1]}/{html.name}",
           wait_until="domcontentloaded",timeout=150000)
  snap("01-game-first-run",22)
  page.mouse.click(640,617);page.wait_for_timeout(800)
  page.mouse.click(640,666);page.wait_for_timeout(800)
  page.keyboard.press("Escape")
  snap("02-real-title-menu",2)
  page.keyboard.press("v");snap("03-voice-key-offline-safe",1)
  page.mouse.click(640,354);snap("04-native-singleplayer-warning",2)
  page.keyboard.press("Escape");snap("05-warning-back",1)
  page.mouse.click(640,425);snap("06-multiplayer-access",2)
  page.keyboard.press("v");snap("07-voice-key-without-session",1)
  mic_requests=page.evaluate("globalThis.__voiceTestMicRequests || 0")
  print("OFFLINE_MIC_PERMISSION_REQUESTS",mic_requests,flush=True)
  if mic_requests!=0:raise RuntimeError("Voice opened browser microphone without server/user consent")
  context.close();browser.close()
except Exception:
 error=traceback.format_exc();print("BROWSER_ERROR",error[-3000:],flush=True)
finally:server.shutdown()
summary={"screenshots":screens,"micRequestsWithoutServerOrConsent":mic_requests if "mic_requests" in globals() else None,
         "pageErrors":[e for e in events if e["kind"]=="pageerror"],
         "error":error,
         "limits":"No actual existing voice-enabled server or old Eaglercraft client joined; no audio interoperability claim"}
(out/"result.json").write_text(json.dumps(summary,indent=2))
(out/"browser-console.json").write_text(json.dumps(events,indent=2))
if error or summary["pageErrors"] or len(screens)!=7:sys.exit(2)
print("PASS: actual Pletzel HTML launched, native menu routes accessed, no microphone request before consent",flush=True)

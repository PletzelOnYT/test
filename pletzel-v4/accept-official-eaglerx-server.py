#!/usr/bin/env python3
"""Official EaglerXServer v1.1.1 direct gameplay compatibility investigation.

Two real Chromium instances load the *unmodified* exact compiled Pletzel HTML
and interact with Minecraft's NATIVE multiplayer UI. The server is a local,
isolated Docker official EaglerXServer release; not a Pletzel gateway or Paper
plugin. Do not mark live voice PASS unless two players actually connect, reach
the voice menu, signal, and exchange nonzero received audio.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server, threading, time, json, traceback, re, sys
files=list(Path("candidate").rglob("*.html"))
assert len(files)==1,files
html=files[0].resolve();out=Path("eaglerxserver-live-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(html.parent),**kwargs)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
events=[];screens=[];fault=None;started=time.monotonic()
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage",
    "--use-fake-device-for-media-stream","--use-fake-ui-for-media-stream",
    "--autoplay-policy=no-user-gesture-required","--enable-webgl",
    "--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop",
    "--disable-features=Vulkan"])
  pages=[b.new_context(viewport={"width":1280,"height":720}).new_page() for i in range(2)]
  for i,p in enumerate(pages):
   p.on("console",lambda m,i=i:events.append({"page":i,"at":round(time.monotonic()-started,1),"kind":m.type,"text":m.text[:1600]}))
   p.on("pageerror",lambda e,i=i:events.append({"page":i,"at":round(time.monotonic()-started,1),"kind":"pageerror","text":str(e)[:1600]}))
   p.goto(f"http://127.0.0.1:{srv.server_address[1]}/{html.name}?perfdebug",wait_until="domcontentloaded",timeout=150000)
   p.wait_for_timeout(42000)
   p.mouse.click(638,618);p.wait_for_timeout(2600)
   p.mouse.click(638,572);p.wait_for_timeout(3500)
   p.screenshot(path=str(out/f"{i}-title.png"),timeout=45000)
   p.mouse.click(638,426);p.wait_for_timeout(4000)
   p.screenshot(path=str(out/f"{i}-multiplayer-safety-warning.png"),timeout=45000)
   p.mouse.click(400,566);p.wait_for_timeout(7500)
   p.screenshot(path=str(out/f"{i}-native-server-list.png"),timeout=45000)
   screens+= [f"{i}-title",f"{i}-multiplayer-safety-warning",f"{i}-native-server-list"]
   if i==0:
    # Real Minecraft native Direct Connection UI to the official v5 proxy.
    p.mouse.click(638,593);p.wait_for_timeout(3300)
    p.screenshot(path=str(out/f"{i}-native-direct-connect.png"),timeout=45000)
    screens.append(f"{i}-native-direct-connect")
    p.keyboard.type("ws://127.0.0.1:5200",delay=55)
    p.keyboard.press("Enter");p.wait_for_timeout(23500)
    p.screenshot(path=str(out/f"{i}-native-server-join-result.png"),timeout=45000)
    screens.append(f"{i}-native-server-join-result")
   # Browser WebSocket probe only; this never claims a native Minecraft join.
   try:
    ws=p.evaluate("""async () => await new Promise(resolve => {
       const conn=new WebSocket('ws://127.0.0.1:5200/');
       const timer=setTimeout(()=>{try{conn.close()}catch(e){}resolve({state:'TIMEOUT'})},8000);
       conn.onopen=()=>{clearTimeout(timer);conn.close();resolve({state:'OPEN'})};
       conn.onerror=()=>{clearTimeout(timer);resolve({state:'ERROR'})};
       conn.onclose=e=>{clearTimeout(timer);resolve({state:'CLOSED',code:e.code})};
    })""")
    print("LIVE_OFFICIAL_WS_CLIENT_PROBE",i,ws,flush=True)
   except Exception as exc:
    print("LIVE_OFFICIAL_WS_CLIENT_PROBE",i,str(exc)[:250],flush=True)
  b.close()
except Exception:
 fault=traceback.format_exc();print("LIVE_SERVER_BROWSER_ERROR",fault[-4000:],flush=True)
finally:srv.shutdown()
result={"exact_binary":html.name,"screens":screens,"error":fault,
  "page_errors":[e for e in events if e["kind"]=="pageerror"],
  "server":"official EaglerXServer 1.1.1 (if Docker bootstrap succeeds)",
  "voice_result":"UNTESTED — only native multiplayer GUI inspection attempted",
  "multiplayer_authoritative_movement":"UNTESTED — no joined player movement proof",
  "cross_version_interoperability":"UNTESTED — no older-client voice peer"}
(out/"results.json").write_text(json.dumps(result,indent=2))
(out/"browser-events.json").write_text(json.dumps(events,indent=2))
print("LIVE_SERVER_BROWSER_PROBE",json.dumps(result),flush=True)
if fault:sys.exit(2)
# Deliberately not a release PASS until subsequent real join/voice assertions.
print("BLOCKED: native multiplayer GUI evidence collected; real server join, movement and voice not yet proven",flush=True)
sys.exit(2)

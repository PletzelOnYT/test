#!/usr/bin/env python3
"""Real WebGL2/IndexedDB in-world Schematica import/UI/renderer check.
The actual standalone HTML is never edited by this test.
Report screenshots and logs; success requires fixture import and live world samples.
"""
import gzip, struct, time, json, threading, http.server, traceback, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path("candidate").resolve()
html=list(root.rglob("*.html"))
assert len(html)==1,html
source=html[0].resolve()
out=Path("inworld-schematic-evidence");out.mkdir(exist_ok=True)
fixture=out/"test-stone-house-5x4x5.schematic"
W,H,L=5,4,5
blocks=[1 if y==0 or (y>0 and (x==0 or z==0 or x==W-1 or z==L-1)) else 0 for y in range(H) for z in range(L) for x in range(W)]
b=bytearray(b"\x0a\x00\x00")
def tag(name,t,v):
 n=name.encode();b.extend(bytes([t])+struct.pack(">H",len(n))+n+v)
for n,v in (("Width",W),("Height",H),("Length",L)):tag(n,2,struct.pack(">h",v))
for n,v in (("Blocks",blocks),("Data",[0]*len(blocks))):tag(n,7,struct.pack(">i",len(v))+bytes(v))
tag("Materials",8,struct.pack(">H",5)+b"Alpha")
b.append(0)
fixture.write_bytes(gzip.compress(b,mtime=0))
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(source.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic();events=[];screens=[];selected=[]; fatal=None
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("google-chrome-stable"),headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m: events.append({"at":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:1800]}))
  page.on("pageerror",lambda e: events.append({"at":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:3000]}))
  def choose(fc):
   try:fc.set_files(str(fixture.resolve()));selected.append("set classic schematic file")
   except Exception as e:selected.append("chooser error: "+str(e))
  page.on("filechooser",choose)
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=30000);screens.append(name)
   print("SNAP",name,flush=True)
  def click(x,y,name,delay=3):
   page.mouse.click(x,y);time.sleep(delay);snap(name)
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(srv.server_address[1],source.name),wait_until="domcontentloaded",timeout=140000)
  time.sleep(115);snap("01-live-world")
  page.keyboard.press("Escape");time.sleep(3);snap("02-pause")
  click(478,394,"03-options")
  click(875,579,"04-schematica-menu")
  click(410,183,"05-file-chooser",8)
  click(868,394,"06-move-to-player")
  snap("07-schematic-status")
  click(876,672,"08-exit-schematica")
  click(650,675,"09-exit-options")
  click(625,255,"10-resume-world",8)
  for n in range(3):
   time.sleep(9)
   snap(f"11-ghost-stability-{n}")
  page.keyboard.press("Escape");time.sleep(3)
  click(475,394,"12-reopen-options")
  click(880,578,"13-reopen-schematica")
  click(885,183,"14-unload",3)
  click(874,672,"15-unload-return-options")
  click(638,672,"16-unload-return-menu")
  click(638,255,"17-unloaded-world")
  browser.close()
except Exception:
 fatal=traceback.format_exc();print(fatal[-3000:],flush=True)
srv.shutdown()
heartbeats=[x["text"] for x in events if "[EagPerfHeartbeat]" in x["text"]]
result={"screens":screens,"fileSelection":selected,"heartbeatCount":len(heartbeats),"exception":fatal,"errors":[x for x in events if x["kind"] in ("error","pageerror")][-35:],"note":"Screenshots need visual verification, a file chooser event alone is not proof of loaded schematic hologram."}
(out/"results.json").write_text(json.dumps(result,indent=2))
(out/"full-console.json").write_text(json.dumps(events,indent=2))
print(json.dumps(result)[:7000],flush=True)
if fatal or len(screens)<17 or not selected:sys.exit(2)

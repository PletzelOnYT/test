#!/usr/bin/env python3
"""Browser gameplay smoke for multi-format import, big schematic processing, and invalid NBT.
This is not full hologram visual validation; compare screenshot evidence separately.
All chooser events must be observed, screenshots taken, and fatal exceptions absent.
"""
import gzip, struct, time, json, threading, http.server, traceback, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path("candidate").resolve()
html=list(root.rglob("*.html"))
assert len(html)==1,html
source=html[0].resolve()
out=Path("fourformat-browser-evidence");out.mkdir(exist_ok=True)
import runpy
fixture_dir=out/"fixtures"
runpy.run_path(str(Path(__file__).with_name("make-fourformat-fixtures.py")))["produce"](fixture_dir)
fixture_names=["basic.schematic","basic.schem","basic.nbt","basic.litematic",
  "stress-4000.schem","stress-10000.schem","stress-50000.schem",
  "stress-100000.schem","stress-500000.schem","stress-1000000.schem","bad.schem"]
current={"index":0}
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
   try:
    name=fixture_names[current["index"]]
    fc.set_files(str((fixture_dir/name).resolve()));selected.append(name)
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
  for idx,name in enumerate(fixture_names):
   current["index"]=idx
   click(410,183,f"import-{idx}-{name}",5 if idx<8 else 12)
   snap(f"after-import-{idx}")
  # Native Java reports only after the full NBT decode and session publish.
  # A chooser opening is NOT enough: every valid file must really load.
  decoded=[evt["text"] for evt in events if "[PletzelSchematicImport]" in evt["text"]]
  valid=fixture_names[:-1]
  missing=[name for name in valid if not any("[PletzelSchematicImport] LOADED "+name in line for line in decoded)]
  badRejected=any("[PletzelSchematicImport] FAILED " in line for line in decoded)
  if missing or not badRejected:
   raise AssertionError("Schematic importer failed native decode acceptance: missing="+repr(missing)+
     ", corrupt file rejected="+repr(badRejected)+", logs="+repr(decoded[-15:]))
  click(868,394,"move-schematic-to-player")
  click(876,672,"exit-schematica")
  click(650,675,"exit-options")
  click(625,255,"resume-world",8)
  snap("final-inworld-after-all-imports")
  # Explicitly reject our previous false green: the Done control had dropped
  # off-screen and a supposed "in-world" screenshot was still the mod menu.
  from PIL import Image
  im=Image.open(out/"final-inworld-after-all-imports.png").convert("RGB")
  samples=[im.getpixel((x,185)) for x in range(250,371,10)]
  gray=sum(1 for p in samples if max(p)-min(p)<8)/len(samples)
  if gray>0.8:
   raise AssertionError("Still in Schematica menu after Done; UI clipped or click navigation failed")
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
import_logs=[x["text"] for x in events if "[PletzelSchematicImport]" in x["text"]]
result={"screens":screens,"fileSelection":selected,"nativeImportLogs":import_logs,"heartbeatCount":len(heartbeats),"exception":fatal,"errors":[x for x in events if x["kind"] in ("error","pageerror")][-35:],"note":"Screenshots need visual verification, a file chooser event alone is not proof of loaded schematic hologram."}
(out/"results.json").write_text(json.dumps(result,indent=2))
(out/"full-console.json").write_text(json.dumps(events,indent=2))
print(json.dumps(result)[:7000],flush=True)
if fatal or len(screens)<18 or len(selected)!=len(fixture_names):sys.exit(2)

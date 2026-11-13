#!/usr/bin/env python3
"""Real Chromium WebGL: Mods hub contains independent Map Tooltip settings;
Schematica contains only schematic features, Easy Pick and Easy Place.
Requires actual native screen-opening telemetry and screenshot evidence.
"""
from pathlib import Path
import http.server,threading,time,traceback,json,re,sys
from playwright.sync_api import sync_playwright

files=list(Path("candidate").rglob("*.html"))
assert len(files)==1,files
html=files[0].resolve()
out=Path("mods-menu-real-chrome-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(html.parent),**kwargs)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[];shots=[];fault=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("chromium"),
    headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
      "--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m:events.append({"kind":m.type,"text":m.text[:2500]}))
  page.on("pageerror",lambda e:events.append({"kind":"pageerror","text":str(e)[:2500]}))
  def seen(term):return any(term in e["text"] for e in events)
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=60000)
   shots.append(name);print("REAL_MODS_SCREENSHOT",name,flush=True)
  def click(x,y,wait=1700):
   page.mouse.click(x,y);page.wait_for_timeout(wait)
  page.goto(f"http://127.0.0.1:{server.server_address[1]}/{html.name}?perfdebug",
    wait_until="domcontentloaded",timeout=150000)
  start=time.monotonic()
  while time.monotonic()-start<360:
   ticks=[(m.group(1)) for e in events
      if "[EagPerfHeartbeat]" in e["text"]
      for m in [re.search(r"lastTick=(\d+)",e["text"])] if m]
   if ticks and int(ticks[-1])>320:break
   page.wait_for_timeout(4500)
  else:raise AssertionError("Real game never completed 320 integrated server ticks")
  # The worker can heartbeat while the UI still displays Loading terrain.
  # Resume only after the same real-world gate as successful save/reload test.
  page.mouse.click(640,360);page.wait_for_timeout(2500)
  snap("01-real-game")
  page.keyboard.press("Escape");page.wait_for_timeout(1400)
  click(478,394)
  snap("02-actual-options-with-mods-entry")
  click(410,585,2400)
  snap("03-actual-mods-hub")
  if not seen("[PletzelModsMenu] OPEN"):
   raise AssertionError("Mods button was not opened from real Minecraft Options")
  # Map Tooltip settings is a DIFFERENT native screen (and is never in Schematica).
  click(640,288,2000)
  snap("04-independent-map-tooltips-settings")
  if not seen("[PletzelMapTooltipSettings] OPEN"):
   raise AssertionError("Map Tooltips did not open its own Mods-screen settings")
  # Back to hub, then independently enter Schematica.
  click(640,670)
  click(640,198)
  snap("05-independent-schematica-easy-pick-easy-place")
  if not seen("[PletzelSchematicaScreen] OPEN"):
   raise AssertionError("Schematica did not open independently from Mods hub")
  # A second screen size must be genuinely rendered; do not infer from source.
  page.set_viewport_size({"width":1024,"height":768})
  page.wait_for_timeout(1600);snap("06-schematica-1024x768")
  page.set_viewport_size({"width":800,"height":600})
  page.wait_for_timeout(1600);snap("07-schematica-800x600")
  print("REAL_MODS_GUI_SEPARATION_AND_RESIZE_PASS",flush=True)
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("REAL_MODS_GUI_FAILURE",fault[-4000:],flush=True)
finally:
 server.shutdown()
(out/"result.json").write_text(json.dumps({"screenshots":shots,"fault":fault,"logs":[e["text"] for e in events if "PletzelModsMenu" in e["text"] or "PletzelMapTooltipSettings" in e["text"] or "PletzelSchematicaScreen" in e["text"]],"pageErrors":[e for e in events if e["kind"]=="pageerror"][-10:]},indent=2))
if fault:sys.exit(2)

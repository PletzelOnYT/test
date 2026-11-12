#!/usr/bin/env python3
"""Actual 26.2 Minecraft Video Settings render-distance / hologram cache regression.

Uses the real slider captured from an independent Chrome scout, and verifies
the native Java [PletzelSchematicPerf] telemetry after leaving Options.
No mocked Minecraft world and no fabricated render-distance counters.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server,threading,json,re,time,sys,traceback,runpy

games=list(Path("candidate").rglob("*.html"));assert len(games)==1,games
game=games[0].resolve();out=Path("render-distance-inworld-evidence");out.mkdir(exist_ok=True)
fixtures=out/"fixtures";fixtures.mkdir(exist_ok=True)
make=runpy.run_path(str(Path(__file__).with_name("make-fourformat-fixtures.py")))
(fixture:=fixtures/"dense-1000000.schem").write_bytes(make["blocks_schem"](100,1,10000))
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(game.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
events=[];stages=[];fault=None;picked=[]
try:
 with sync_playwright() as w:
  b=w.chromium.launch(executable_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("google-chrome-stable"),
    headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=b.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m:events.append({"kind":m.type,"text":m.text[:2200]}))
  page.on("pageerror",lambda e:events.append({"kind":"pageerror","text":str(e)[:2200]}))
  def select(fc):
   fc.set_files(str(fixture.resolve()));picked.append("dense-1000000.schem")
  page.on("filechooser",select)
  def shot(label):
   page.screenshot(path=str(out/(label+".png")),timeout=60000)
   print("RD_REAL_SNAPSHOT",label,flush=True)
  def click(x,y,t=1200):
   page.mouse.click(x,y);page.wait_for_timeout(t)
  def pause():
   page.keyboard.press("Escape");page.wait_for_timeout(1200)
   click(478,394)
  def resume():
   click(635,673);click(635,673)
   page.mouse.move(635,250);page.wait_for_timeout(350)
   click(635,250,1800)
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(srv.server_address[1],game.name),
            wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(135000);shot("01-real-world")
  if not any("[EagPerfHeartbeat]" in e["text"] for e in events):
   raise AssertionError("Real integrated-server world heartbeat missing")
  pause();click(875,579)
  click(410,183,13000)
  if not any("[PletzelSchematicImport] LOADED dense-1000000.schem" in e["text"] for e in events):
   raise AssertionError("Real 1M schematic import did not finish")
  click(868,394);resume();shot("02-million-blocks-inworld")
  # RenderDistance is a real integer-slider with range [2,16].
  # Exact x/y calibrated from actual 1280x720 Options->Video screenshots.
  slider={2:677,4:735,8:851,16:1081}
  for number,rd in enumerate([2,4,8,16,8,4,2]):
   pause()
   click(397,362,1600)  # Options > Video Settings
   page.mouse.move(640,400)
   page.mouse.wheel(0,1150)
   page.wait_for_timeout(1200)
   shot(f"{number}-video-before-rd-{rd}")
   click(slider[rd],506,1200)
   shot(f"{number}-video-rd-{rd}")
   # Video Done -> Options Done -> Pause Back To Game.
   resume()
   begin=len(events)
   page.wait_for_timeout(15500)
   perf=[e["text"] for e in events[begin:] if "[PletzelSchematicPerf]" in e["text"]]
   exact=[s for s in perf if re.search(r"renderDistance="+str(rd)+r"(?:\D|$)",s)]
   if not exact:raise AssertionError(f"Render-distance slider did not apply rd={rd}; logs={perf[-6:]}")
   line=exact[-1]
   fields=dict((k,int(v)) for k,v in re.findall(r"(\w+)=(\d+)",line))
   if fields.get("cachedSections",0)>64 or fields.get("cachedCells",0)>65536:
    raise AssertionError("Unbounded schematic cache at rd="+str(rd)+": "+line)
   stages.append({"requested":rd,"observed":fields,"console":line,
      "heartbeatCount":sum("[EagPerfHeartbeat]" in e["text"] for e in events[begin:]),
      "jsHeap":page.evaluate("performance.memory?.usedJSHeapSize ?? null")})
   shot(f"{number}-inworld-rd-{rd}")
   print("RD_REAL_TELEMETRY",json.dumps(stages[-1])[:2600],flush=True)
  # Frustum and loaded world chunks can cap distant visibility. Preserve actual
  # observed counts, never claim strict increase if the world lacks those chunks.
  assert len(stages)==7
  b.close()
except Exception:
 fault=traceback.format_exc();print("RD_REAL_ERROR",fault[-4500:],flush=True)
finally:srv.shutdown()
report={"observations":stages,"fault":fault,"fileChooser":picked,
        "pageErrors":[e["text"] for e in events if e["kind"]=="pageerror"][-20:],
        "limitations":["Only already-loaded client world chunks can show holograms",
                       "Software WebGL and dynamic world generation can affect active-section counts",
                       "No persistent GPU VBO measurements are available"]}
(out/"report.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
if fault or len(stages)!=7:sys.exit(2)
print("PASS: 2/4/8/16 real Video Settings slider recorded matching native chunk-cache telemetry",flush=True)

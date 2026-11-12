#!/usr/bin/env python3
"""Real Chromium WebGL1/2 hologram timing comparison; no synthetic FPS claims.

Run with one exact standalone HTML under candidate/. The same scenario and
same fixture are run independently for baseline and optimized artifacts.
The metric is the browser's actual requestAnimationFrame presentation cadence,
which can be affected by software WebGL and CI host load. It is not a GPU timer.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import argparse, http.server, json, math, re, runpy, statistics, threading, time, traceback, sys

parser=argparse.ArgumentParser()
parser.add_argument("--flavor",choices=("baseline","optimized"),required=True)
args=parser.parse_args()
games=list(Path("candidate").rglob("*.html"))
assert len(games)==1,games
game=games[0].resolve()
out=Path("hologram-perf-evidence")/args.flavor
out.mkdir(parents=True,exist_ok=True)
fixture_dir=out/"fixtures"
fixture_dir.mkdir(parents=True,exist_ok=True)
make=runpy.run_path(str(Path(__file__).with_name("make-fourformat-fixtures.py")))
# Three exact workloads, all 26.2 real NBT schematic files.
for n,w,h,l in ((4000,100,1,40),(500000,100,1,5000),(1000000,100,1,10000)):
    (fixture_dir/f"dense-{n}.schem").write_bytes(make["blocks_schem"](w,h,l))
w,h,l=100,1,10000
# Every 16th block solid: same 1M-cell NBT envelope but sparse geometry.
palette=make["t_compound"]("Palette",make["t_int"]("minecraft:air",0),make["t_int"]("minecraft:stone",1))
payload=bytes(1 if i%16==0 else 0 for i in range(w*h*l))
(fixture_dir/"sparse-1000000.schem").write_bytes(make["compress"](make["root"](
    make["t_int"]("Version",2),make["t_short"]("Width",w),
    make["t_short"]("Height",h),make["t_short"]("Length",l),
    palette,make["t_bytearray"]("BlockData",payload))))
assert len(payload)==1000000

class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(game.parent),**kw)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
start=time.monotonic()
events=[];fault=None;selected=[];stages=[];current={"name":None}
RafScript="""() => {
  // Exactly one rAF sampler per page. Starting one per stage would duplicate
  // frame intervals and invalidate the before/after FPS comparison.
  if (window.__pletzelRafRunning) return;
  window.__pletzelRafRunning=true;
  window.__pletzelSample = {frames: [], prev: null, collecting: false};
  function track(ts) {
    const s=window.__pletzelSample;
    if(s) {
      if(s.collecting && s.prev!==null && ts>s.prev && ts-s.prev<15000)
         s.frames.push(ts-s.prev);
      s.prev=ts;
      if(s.frames.length>30000) s.frames.splice(0,1000);
    }
    requestAnimationFrame(track);
  }
  requestAnimationFrame(track);
}"""
def calculate(values):
 vals=sorted(float(x) for x in values if x>0)
 if not vals:return {"samples":0,"averageFps":None,"onePercentLowFps":None,"p99Ms":None,"maxMs":None}
 mean=statistics.mean(vals)
 p99=vals[max(0,min(len(vals)-1,math.ceil(0.99*len(vals))-1))]
 return {"samples":len(vals),"averageFps":round(1000.0/mean,2),
         "onePercentLowFps":round(1000.0/p99,2),
         "meanMs":round(mean,2),"p99Ms":round(p99,2),"maxMs":round(max(vals),2)}
def elapsed():return round(time.monotonic()-start,1)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("google-chrome-stable"),headless=False,
      args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan","--enable-precise-memory-info"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m: events.append({"t":elapsed(),"kind":m.type,"text":m.text[:2000]}))
  page.on("pageerror",lambda e:events.append({"t":elapsed(),"kind":"pageerror","text":str(e)[:2000]}))
  def choose(fc):
   name=current["name"]
   fc.set_files(str((fixture_dir/name).resolve()));selected.append(name)
  page.on("filechooser",choose)
  def shot(name):
   page.screenshot(path=str(out/(name+".png")),timeout=60000)
   print("PERF_SHOT",args.flavor,name,elapsed(),flush=True)
  def click(x,y,delay=1):
   page.mouse.click(x,y);page.wait_for_timeout(int(delay*1000))
  def collect(name,seconds=22):
   page.evaluate(RafScript)
   page.evaluate("window.__pletzelSample.collecting=true;window.__pletzelSample.frames=[];window.__pletzelSample.prev=null")
   before=len(events)
   page.wait_for_timeout(int(seconds*1000))
   values=page.evaluate("window.__pletzelSample.collecting=false;window.__pletzelSample.frames") or []
   metric=calculate(values)
   metric.update({"stage":name,"time":elapsed(),"webglInChrome":True,
      "javascriptHeapBytes":page.evaluate("performance.memory?.usedJSHeapSize ?? null"),
      "nativePerfLogLines":[e["text"] for e in events[before:] if "[PletzelSchematicPerf]" in e["text"]][-8:],
      "worldHeartbeatLines":len([e for e in events[before:] if "[EagPerfHeartbeat]" in e["text"]])})
   stages.append(metric)
   print("PERF_METRIC",json.dumps(metric)[:5000],flush=True)
   shot(name)
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(server.server_address[1],game.name),
            wait_until="domcontentloaded",timeout=150000)
  # Exact same wait and same world seed/config on both candidates.
  page.wait_for_timeout(135000)
  shot("01-ready-world")
  beats=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
  if not beats:raise AssertionError("No real singleplayer heartbeat")
  collect("unloaded-world",18)
  for name in ("dense-4000.schem","dense-500000.schem","dense-1000000.schem","sparse-1000000.schem"):
   page.keyboard.press("Escape");page.wait_for_timeout(1500)
   shot("pause-before-"+name)
   click(478,394,2)
   shot("options-before-"+name)
   click(875,579,2)
   shot("schematica-before-"+name)
   current["name"]=name
   click(410,183,12 if "1000000" in name else 5)
   shot("imported-"+name)
   print("FILE_CHOOSER_EVENTS",selected,flush=True)
   decoded=[e["text"] for e in events if "[PletzelSchematicImport] LOADED "+name in e["text"]]
   if not decoded:raise AssertionError("Real decoder never loaded "+name)
   click(868,394,2) # move schematic to player
   click(876,672,2) # Done schematic
   click(650,675,2) # Done options
   page.mouse.move(625,255);page.wait_for_timeout(400)
   click(625,255,2) # Resume
   page.wait_for_timeout(8000) # warmup and camera-index progress
   collect(name.replace(".schem",""),24)
   # Measure incremental re-entry while walking, not just standing still.
   page.keyboard.down("w");page.wait_for_timeout(2000);page.keyboard.up("w")
   page.keyboard.down("s");page.wait_for_timeout(2000);page.keyboard.up("s")
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("PERF_ERROR",fault[-4000:],flush=True)
finally:
 server.shutdown()
result={"flavor":args.flavor,"file":game.name,"created":elapsed(),"stages":stages,
        "selected":selected,"fatal":fault,
        "pageErrors":[e for e in events if e["kind"]=="pageerror"][-15:],
        "limits":["Chrome CI software WebGL is not physical Mac GPU","JS heap excludes some WebAssembly/VRAM",
                  "FPS samples are client frame pacing, not native GPU draw-call profiling",
                  "Only the available default render distance is benchmarked in this script"]}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
if fault or len(stages)<5:sys.exit(2)
print("REAL_CHROME_PERFORMANCE_PROBE_PASSED",args.flavor,flush=True)

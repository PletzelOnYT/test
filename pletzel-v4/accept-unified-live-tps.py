#!/usr/bin/env python3
"""Real standalone Minecraft integrated-server endurance smoke.

Playwright loads the EXACT compiled HTML and asks the actual game for a new
singleplayer world. No HTML editing, mocked tick counters, or fabricated world.
Requires genuine server heartbeat ticks over a measured 3-minute interval.
"""
import http.server,threading,time,json,re,sys,os,traceback,statistics
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageStat
files=list(Path("candidate").rglob("*.html"))
assert len(files)==1,files
html=files[0].resolve()
mode=os.environ.get("CPU_MODE","normal")
assert mode in ("normal","singlecpu")
out=Path("live-tps-"+mode+"-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(html.parent),**kwargs)
 def log_message(self,*args):pass
httpd=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
started=time.monotonic();events=[];screens=[];fault=None;begin=None;end=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage",
    "--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
    "--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720},device_scale_factor=1)
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m:events.append({"at":round(time.monotonic()-started,2),"kind":m.type,"text":m.text[:2000]}))
  page.on("pageerror",lambda e:events.append({"at":round(time.monotonic()-started,2),"kind":"pageerror","text":str(e)[:2000]}))
  def heartbeats():
   ans=[]
   for e in events:
    if "[EagPerfHeartbeat]" in e["text"]:
     m=re.search(r"lastTick=(\\d+)",e["text"])
     if m:ans.append((e["at"],int(m.group(1)),e["text"]))
   return ans
  def snap(name):
   path=out/(name+".png")
   page.screenshot(path=str(path),timeout=40000)
   im=Image.open(path).convert("L").crop((0,120,1280,700))
   stats=ImageStat.Stat(im)
   screens.append({"name":name,"at":round(time.monotonic()-started,2),
                   "lumaStdDev":round(stats.stddev[0],2)})
   print("LIVE_WORLD_SNAP",name,screens[-1],flush=True)
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(httpd.server_address[1],html.name),
            wait_until="domcontentloaded",timeout=150000)
  deadline=time.monotonic()+330
  while time.monotonic()<deadline:
   beats=heartbeats()
   if beats and beats[-1][1]>400:break
   page.wait_for_timeout(5000)
  else:raise AssertionError("Integrated server did not complete 400 real ticks")
  snap("01-initial-world-with-real-chunks")
  begin=(round(time.monotonic()-started,2),heartbeats()[-1][1])
  for n in range(18):
   page.wait_for_timeout(10000)
   if n in (5,11,17):snap("02-ongoing-actual-world-%02d"%(n+1))
  end=(round(time.monotonic()-started,2),heartbeats()[-1][1])
  browser.close()
except Exception:
 fault=traceback.format_exc();print("LIVE_TPS_FATAL",fault[-3000:],flush=True)
finally:httpd.shutdown()
beats=[]
for e in events:
 if "[EagPerfHeartbeat]" in e["text"]:
  m=re.search(r"lastTick=(\\d+)",e["text"])
  if m:beats.append((e["at"],int(m.group(1))))
elapsed=(end[0]-begin[0]) if begin and end else 0
ticks=(end[1]-begin[1]) if begin and end else 0
tps=(ticks/elapsed) if elapsed>0 else 0
intervals=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(beats,beats[1:]) if b[0]>a[0]]
max_gap=max((v[0] for v in intervals if begin and v[0]>0 and v[0]<=elapsed),default=None)
pages=[e for e in events if e["kind"]=="pageerror"]
result={"mode":mode,"browser":"Playwright Chromium Xvfb","elapsed_seconds":round(elapsed,2),
        "real_server_ticks":ticks,"mean_actual_tps":round(tps,2),
        "heartbeat_count":len(beats),"heartbeat_max_gap_seconds":max_gap,
        "screenshots":screens,"page_errors":pages,"fault":fault,
        "source":"Actual EagPerfHeartbeat console from unmodified compiled standalone HTML",
        "limitations":"Three-minute engine smoke on Ubuntu software GL, not Mac gameplay acceptance"}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"events.json").write_text(json.dumps(events,indent=2))
print("INTEGRATED_SERVER_LIVE_TPS_RESULT",json.dumps(result)[:6500],flush=True)
if fault or pages or elapsed<170 or len(screens)<4:sys.exit(2)
# Under Xvfb software OpenGL these are provisional minimum endurance
# thresholds, NOT user-acceptance claims of 20 TPS at all times.
threshold=15 if mode=="normal" else 10
if tps<threshold:raise SystemExit("Real integrated server mean TPS "+str(round(tps,2))+" below "+str(threshold))
if max_gap is None or max_gap>20:raise SystemExit("Real server heartbeat gap too large "+str(max_gap))
if any(x["lumaStdDev"]<12 for x in screens):
 raise SystemExit("World screenshot has implausibly low visual variation")
print("PASS: genuine singleplayer server ticks and stable browser frames across full endurance interval",flush=True)

#!/usr/bin/env python3
"""Chromium integrated-server TPS and chunk pressure characterization for exact frozen V4 HTML.
This baseline does not change JavaScript, sound assets, worldgen, or rendering.
"""
from pathlib import Path
import http.server,threading,time,json,re,sys,traceback,os
from playwright.sync_api import sync_playwright
root=Path("candidate")
htmls=list(root.rglob("*.html"))
assert len(htmls)==1, htmls
html=htmls[0].resolve()
out=Path("singleplayer-pressure-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent),**kw)
 def log_message(self,*a):pass
httpd=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
events=[];metrics=[];screens=[];started=time.monotonic();err=None
rate=float(os.getenv("CPU_SLOWDOWN","1"))
duration=int(os.getenv("GAMEPLAY_SECONDS","185"))
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("""window.__eaglerAutoTest='sp';window.__pletzelProbe={workers:0,messages:0,errors:0};
   (()=>{const W=window.Worker;window.Worker=class extends W{
    constructor(...a){super(...a);window.__pletzelProbe.workers++;this.addEventListener('message',()=>window.__pletzelProbe.messages++);this.addEventListener('error',()=>window.__pletzelProbe.errors++);}
   };})();""")
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-started,1),"kind":m.type,"text":m.text[:2500]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-started,1),"kind":"pageerror","text":str(e)[:2500]}))
  cdp=page.context.new_cdp_session(page)
  if rate>1:cdp.send("Emulation.setCPUThrottlingRate",{"rate":rate})
  url=f"http://127.0.0.1:{httpd.server_address[1]}/{html.name}?perfdebug"
  page.goto(url,wait_until="domcontentloaded",timeout=150000)
  first_time=None
  # A nonzero tick in EagPerfHeartbeat proves the integrated server has entered gameplay.
  while time.monotonic()-started < 325:
   beats=[x["text"] for x in events if "[EagPerfHeartbeat]" in x["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",b)) and int(m.group(1))>40 for b in beats):
    first_time=time.monotonic();break
   time.sleep(5)
  if first_time is None:raise RuntimeError("no completed gameplay ticks within 325 s")
  page.screenshot(path=str(out/"spawn.png"),timeout=25000);screens.append("spawn")
  print(f"SPAWN ready after {first_time-started:.1f}s at CPU_SLOWDOWN={rate}",flush=True)
  # Running and sprinting in an actual Survival world. The player may hit a block;
  # server diagnostics still observe chunk pressure and tick response during movement.
  page.keyboard.down("Control");page.keyboard.down("w")
  while time.monotonic()-first_time < duration:
   time.sleep(10)
   t=round(time.monotonic()-first_time,1)
   beats=[x for x in events if "[EagPerfHeartbeat]" in x["text"]]
   recent=beats[-1]["text"] if beats else ""
   def number(name):
    m=re.search(re.escape(name)+r"=(-?\d+)",recent)
    return int(m.group(1)) if m else None
   values={k:number(k) for k in ["lastTick","sinceCompleted","worldgenQueue","oldestQueueAge","activeWorldgen","claims","tasks","workerMessageBatches"]}
   values["elapsed"]=t
   values["browser"]=page.evaluate("() => ({worker:window.__pletzelProbe,webgl2:!!document.createElement('canvas').getContext('webgl2'),storage:!!indexedDB})")
   metrics.append(values)
   print("OBS",json.dumps(values),flush=True)
   if len(metrics)%6==0:
    page.screenshot(path=str(out/f"walking-{round(t):03d}s.png"),timeout=30000)
    screens.append(f"walking-{round(t):03d}s")
  page.keyboard.up("w");page.keyboard.up("Control")
  page.screenshot(path=str(out/"finish.png"),timeout=30000);screens.append("finish")
  browser.close()
except Exception:
 err=traceback.format_exc();print(err[-3200:],flush=True)
finally:
 httpd.shutdown()
hb=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
tot=[re.search(r"lastTick=(\d+)",e["text"]) for e in hb]
seq=[int(m.group(1)) for m in tot if m]
waits=[e for e in events if "[EagPerfChunkWait]" in e["text"]]
phases=[e for e in events if "[EagPerf] slow phase" in e["text"]]
result={"rate":rate,"first_world_tick_at_s":None if first_time is None else round(first_time-started,1),"tick_min":min(seq) if seq else None,"tick_max":max(seq) if seq else None,"tick_after_spawn":seq[-1]-seq[0] if len(seq)>=2 else None,"readings":metrics,"screenshots":screens,"long_chunk_waits":waits[-80:],"slow_phases":phases[-80:],"fatal":err,"errors":[e for e in events if e["kind"] in ("error","pageerror")][-40:]}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"events.json").write_text(json.dumps(events,indent=2))
assert not err and first_time is not None and len(metrics)>5, "failed to reach sustained gameplay"
print("BASELINE COMPLETE",json.dumps({"first_tick":result["first_world_tick_at_s"],"tick_max":result["tick_max"],"n_metrics":len(metrics),"max_stall":max((m["sinceCompleted"] or 0 for m in metrics),default=0)}),flush=True)

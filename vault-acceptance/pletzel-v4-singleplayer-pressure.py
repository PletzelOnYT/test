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
  # A dedicated-worker workload needs OS-wide throttling: CDP only throttles the tab.
  # Affinity is inherited by ALL Chromium processes including the Wasm-GC server worker.
  chromium_bin=p.chromium.executable_path
  browser_executable=None
  if os.getenv("PIN_ONE_CPU","0")=="1":
   cpus=sorted(os.sched_getaffinity(0))
   assert cpus,"no available CPU"
   wrapper=out/"chromium-affinity-wrapper.sh"
   wrapper.write_text('#!/bin/sh'+chr(10)+'exec taskset -c '+str(cpus[0])+' "'+chromium_bin+'" "$@"'+chr(10))
   wrapper.chmod(0o755)
   browser_executable=str(wrapper.resolve())
   print("CPU AFFINITY: pin all Chromium worker processes to CPU",cpus[0],flush=True)
  browser=p.chromium.launch(executable_path=browser_executable,headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("""window.__eaglerAutoTest='sp';window.__pletzelProbe={workers:0,messages:0,errors:0};
   (()=>{const W=window.Worker;window.Worker=class extends W{
    constructor(...a){super(...a);window.__pletzelProbe.workers++;this.addEventListener('message',()=>window.__pletzelProbe.messages++);this.addEventListener('error',()=>window.__pletzelProbe.errors++);}
   };})();""")
  # Independent real-browser scheduler probe: rAF cadence and main-thread
  # Long Tasks are measured separately from native frame render/present time.
  # The callback only accumulates numbers and never invokes WebGL.
  page.add_init_script("""(() => {
    const s={rafCallbacks:0,rafGapTotalMs:0,rafGapMaxMs:0,rafOver50Ms:0,rafOver250Ms:0,
             mainLongTasks:0,mainLongTaskMs:0,mainLongTaskMaxMs:0};
    window.__pletzelScheduler=s;
    let previous=0;
    function sample(now) {
      if(previous) {
        const dt=Math.max(0,now-previous);
        s.rafCallbacks++;s.rafGapTotalMs+=dt;
        s.rafGapMaxMs=Math.max(s.rafGapMaxMs,dt);
        if(dt>50)s.rafOver50Ms++;
        if(dt>250)s.rafOver250Ms++;
      }
      previous=now;
      requestAnimationFrame(sample);
    }
    requestAnimationFrame(sample);
    try {
      new PerformanceObserver(list => {
        for(const e of list.getEntries()) {
          s.mainLongTasks++;s.mainLongTaskMs+=e.duration;
          s.mainLongTaskMaxMs=Math.max(s.mainLongTaskMaxMs,e.duration);
        }
      }).observe({entryTypes:['longtask']});
    } catch(ignore) {}
  })();""")
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-started,1),"kind":m.type,"text":m.text[:2500]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-started,1),"kind":"pageerror","text":str(e)[:2500]}))
  cdp=page.context.new_cdp_session(page)
  if rate>1:cdp.send("Emulation.setCPUThrottlingRate",{"rate":rate})
  url=f"http://127.0.0.1:{httpd.server_address[1]}/{html.name}?perfdebug"
  page.goto(url,wait_until="domcontentloaded",timeout=150000)
  first_time=None
  next_load_screen_capture=18.0
  # Real native 26.2 loading UI: capture original chunk-status colored cells
  # at several timepoints before game starts. Do not fake progress or modify
  # the game. Capture only at most 5 frames to avoid burdening worldgen.
  # A nonzero tick in EagPerfHeartbeat proves the integrated server has entered gameplay.
  while time.monotonic()-started < 325:
   elapsed_loading=time.monotonic()-started
   if elapsed_loading >= next_load_screen_capture and next_load_screen_capture <= 90:
    try:
     page.screenshot(path=str(out/f"native-loading-{int(next_load_screen_capture):03d}s.png"),timeout=30000)
     screens.append(f"native-loading-{int(next_load_screen_capture):03d}s")
    except Exception as screenshot_error:
     print("LOADING SCREEN SNAPSHOT FAILED",repr(screenshot_error),flush=True)
    next_load_screen_capture+=18.0
   beats=[x["text"] for x in events if "[EagPerfHeartbeat]" in x["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",b)) and int(m.group(1))>40 for b in beats):
    first_time=time.monotonic();break
   page.wait_for_timeout(5000)
  if first_time is None:raise RuntimeError("no completed gameplay ticks within 325 s")
  page.screenshot(path=str(out/"spawn.png"),timeout=25000);screens.append("spawn")
  print(f"SPAWN ready after {first_time-started:.1f}s at CPU_SLOWDOWN={rate}",flush=True)
  # Running and sprinting in an actual Survival world. The player may hit a block;
  # server diagnostics still observe chunk pressure and tick response during movement.
  # Dismiss look-around tutorial and obtain focus/pointer-lock for actual traversal.
  page.mouse.click(640,355);page.wait_for_timeout(850)
  page.mouse.move(655,355);page.mouse.move(700,390,steps=5)
  # A quick second W press triggers vanilla sprint; use only normal gameplay input.
  page.keyboard.press("w");page.wait_for_timeout(150);page.keyboard.down("w")
  while time.monotonic()-first_time < duration:
   page.wait_for_timeout(10000)
   t=round(time.monotonic()-first_time,1)
   beats=[x for x in events if "[EagPerfHeartbeat]" in x["text"]]
   recent=beats[-1]["text"] if beats else ""
   def number(name):
    m=re.search(re.escape(name)+r"=(-?\d+)",recent)
    return int(m.group(1)) if m else None
   values={k:number(k) for k in ["lastTick","sinceCompleted","worldgenQueue","oldestQueueAge","activeWorldgen","claims","tasks","workerMessageBatches"]}
   values["elapsed"]=t
   values["browser"]=page.evaluate("() => ({worker:window.__pletzelProbe,scheduler:window.__pletzelScheduler,webgl2:!!document.createElement('canvas').getContext('webgl2'),storage:!!indexedDB})")
   metrics.append(values)
   print("OBS",json.dumps(values),flush=True)
   if len(metrics)%6==0:
    page.screenshot(path=str(out/f"walking-{round(t):03d}s.png"),timeout=30000)
    screens.append(f"walking-{round(t):03d}s")
  page.keyboard.up("w")
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
assert not err and first_time is not None and len(metrics)>=12, "failed to reach sustained gameplay"
assert all(m["browser"]["webgl2"] and m["browser"]["storage"] for m in metrics),"WebGL2 or IndexedDB unavailable"
assert all(m["browser"]["worker"]["errors"]==0 for m in metrics),"worker errors"
live=[m for m in metrics if m["lastTick"] is not None]
assert len(live)>10,"server tick telemetry missing"
rate=(live[-1]["lastTick"]-live[0]["lastTick"])/(live[-1]["elapsed"]-live[0]["elapsed"])
result["actual_tick_rate"]=round(rate,2)
result["max_since_completed_ms"]=max(m["sinceCompleted"] or 0 for m in metrics)
(out/"result.json").write_text(json.dumps(result,indent=2))
min_rate=3.0 if os.getenv("PIN_ONE_CPU","0")=="1" else 12.0
assert rate>=min_rate,f"server progressed at only {rate:.2f} TPS (minimum {min_rate})"
assert result["max_since_completed_ms"]<15000,"persistent server stalled >15s"
print("BASELINE COMPLETE",json.dumps({"first_tick":result["first_world_tick_at_s"],"tick_max":result["tick_max"],"n_metrics":len(metrics),"max_stall":max((m["sinceCompleted"] or 0 for m in metrics),default=0)}),flush=True)

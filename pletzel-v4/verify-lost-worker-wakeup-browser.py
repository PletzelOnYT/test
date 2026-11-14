#!/usr/bin/env python3
"""Actual Chromium dedicated-Wasm-worker forced lost tick wake test.
Only the test Worker wrapper is modified. The immutable game HTML is not.
"""
import http.server,threading,time,json,re,traceback,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
files=list(Path("candidate").rglob("*.html"));assert len(files)==1
html=files[0].resolve()
out=Path("wakeup-loss-evidence");out.mkdir(exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(html.parent),**kw)
 def log_message(self,*args):pass
httpd=http.server.ThreadingHTTPServer(("127.0.0.1",0),H)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
start=time.monotonic();events=[];screens=[];fatal=None;count=0
bootstrap=r"""(() => {
const NativeWorker=window.Worker;
window.__eaglerAutoTest='sp';
window.__pletzelTestWorkerCount=0;
function workerSetup() {
 const realTimeout=self.setTimeout.bind(self);
 const realPost=(self.scheduler && typeof self.scheduler.postTask==='function')
   ? self.scheduler.postTask.bind(self.scheduler) : null;
 let server=false,armed=false,dropped=null;
 self.addEventListener('message',event=>{
   const boot=event.data && event.data.eaglerWasmBoot;
   if(boot && boot.args && boot.args.includes('_worker_process_')) {
     server=true;
     realTimeout(()=>{armed=true;console.warn('[PletzelTest] armed single lost server wake after 60s');},60000);
   }
 });
 self.setTimeout=function(fn,ms,...rest){
   if(server && armed && !dropped && typeof fn==='function' && typeof fn.__pletzelDueAt==='number'){
     armed=false;dropped=fn;
     console.warn('[PletzelTest] DROPPED server fallback setTimeout callback');
     return 1234567;
   }
   return realTimeout(fn,ms,...rest);
 };
 if(realPost) {
   try{
     self.scheduler.postTask=function(fn,opts){
       if(server && dropped===fn){
         console.warn('[PletzelTest] DROPPED matching scheduler.postTask callback');
         return new Promise(()=>{});
       }
       return realPost(fn,opts);
     };
   }catch(e){console.error('[PletzelTest] cannot override scheduler: '+String(e));}
 }
}
window.Worker=class extends NativeWorker {
 constructor(url,options) {
   window.__pletzelTestWorkerCount++;
   const wrapped = '('+workerSetup.toString()+')();\nimportScripts('+JSON.stringify(String(url))+');';
   const virtualURL=URL.createObjectURL(new Blob([wrapped],{type:'text/javascript'}));
   super(virtualURL,options);
 }
};
})();"""
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script(bootstrap)
  page.on("console",lambda m:events.append({"at":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:2200]}))
  page.on("pageerror",lambda e:events.append({"at":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:3000]}))
  page.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{html.name}?perfdebug&workerlog",wait_until="domcontentloaded",timeout=150000)
  for n in range(38):
   page.wait_for_timeout(10000)
   if n in (9,20,37):
    name=f"simulation-{(n+1)*10:03d}s"
    page.screenshot(path=str(out/(name+".png")),timeout=30000);screens.append(name)
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if beats:print("REAL_TICK_LIVENESS",beats[-1][:450],flush=True)
   markers=[e["text"] for e in events if "[PletzelTest]" in e["text"] or "[PletzelWakeRescue26]" in e["text"]]
   if markers:print("WORKER_LOSS_MARKER",markers[-4:],flush=True)
   if any("DROPPED matching scheduler.postTask" in m for m in markers) and any("[PletzelWakeRescue26]" in m for m in markers):
    page.wait_for_timeout(30000)
    page.screenshot(path=str(out/"resumed-real-ticks-after-loss.png"),timeout=30000)
    screens.append("resumed-real-ticks-after-loss")
    break
  count=page.evaluate("window.__pletzelTestWorkerCount||0")
  browser.close()
except Exception:
 fatal=traceback.format_exc();print("FAILURE",fatal[-4000:],flush=True)
finally:httpd.shutdown()
def hits(pat):return [e for e in events if pat in e["text"]]
loss=hits("DROPPED matching scheduler.postTask")
rescue=hits("[PletzelWakeRescue26]")
ticks=[]
for e in events:
 m=re.search(r"\[EagPerfHeartbeat\].*?\blastTick=(\d+)",e["text"])
 if m:ticks.append((e["at"],int(m.group(1))))
after=[x for x in ticks if rescue and x[0]>rescue[0]["at"]]
results={"worker_constructors":count,"loss_injected":len(loss),"supervisor_rescue_markers":len(rescue),
 "ticks_after_recovery":after[-1][1]-after[0][1] if len(after)>1 else None,
 "real_tick_start":ticks[0] if ticks else None,"real_tick_end":ticks[-1] if ticks else None,
 "screenshots":screens,"pageerrors":hits("pageerror"),"exception":fatal,
 "test_code_only":"No compiled game source or HTML modified. Browser intercepts ONE tick callback."}
(out/"result.json").write_text(json.dumps(results,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("LOSS_TEST_RESULTS",json.dumps(results),flush=True)
if fatal or count<1 or not loss or not rescue or (results["ticks_after_recovery"] or 0)<30:
 sys.exit(2)

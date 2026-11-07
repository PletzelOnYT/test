#!/usr/bin/env python3
"""In-world singleplayer regression probe on the unchanged compiled HTML.
Native engine __eaglerAutoTest='sp' creates normal, non-flat worlds automatically.
Exit != 0 unless real ticks and chunk transfer are proven.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import json,threading,http.server,time,re,traceback,sys
out=Path('singleplayer-inworld-evidence');out.mkdir(exist_ok=True)
html=list(Path('candidate').rglob('*.html'));assert len(html)==1,html
source=html[0].resolve()
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(source.parent),**kwargs)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[];snapshots=[];samples=[]
start=time.monotonic(); failure=None
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720})
  page.add_init_script("""window.__eaglerAutoTest='sp';
   (function() {
     window.__pletzelWorkerStats={created:0,messages:0,errors:0};
     const OriginalWorker=window.Worker;
     window.Worker=class extends OriginalWorker {
       constructor(...args) {
         super(...args);window.__pletzelWorkerStats.created++;
         this.addEventListener('message',()=>window.__pletzelWorkerStats.messages++);
         this.addEventListener('error',()=>window.__pletzelWorkerStats.errors++);
       }
     };
   })();""")
  page.on('console',lambda m:events.append({'at':round(time.monotonic()-start,2),'kind':m.type,'text':m.text[:3500]}))
  page.on('pageerror',lambda e:events.append({'at':round(time.monotonic()-start,2),'kind':'pageerror','text':str(e)[:3500]}))
  page.on('crash',lambda:events.append({'at':round(time.monotonic()-start,2),'kind':'crash','text':'crash'}))
  page.goto('http://127.0.0.1:%d/%s?perfdebug'%(server.server_address[1],source.name),wait_until='domcontentloaded',timeout=150000)
  for i in range(13):
   time.sleep(18)
   name=f'world-t+{18*(i+1):03d}s'
   try:
    page.screenshot(path=str(out/(name+'.png')),timeout=25000)
    diag=page.evaluate("""() => ({webgl2:!!document.createElement('canvas').getContext('webgl2'),indexedDB:!!indexedDB,workers:window.__pletzelWorkerStats,millis:performance.now()})""")
    snapshots.append(name);samples.append({'label':name,**diag})
    print('SNAP',name,diag,flush=True)
   except Exception as e:events.append({'kind':'screenshot_error','text':str(e)})
   hb=[x['text'] for x in events if '[EagPerfHeartbeat]' in x['text']]
   if hb:print('HEARTBEAT',hb[-1][:600],flush=True)
  browser.close()
except Exception as e:
 failure=str(e);events.append({'kind':'testException','text':traceback.format_exc()[-2500:]})
finally:
 server.shutdown()
heartbeats=[x['text'] for x in events if '[EagPerfHeartbeat]' in x['text']]
ticks=[int(z.group(1)) for x in heartbeats if (z:=re.search(r'lastTick=(\d+)',x))]
chks=[int(z.group(1)) for x in events if '[EagPerf]' in x['text'] if (z:=re.search(r'chunksSent=(\d+)',x['text']))]
problems=[x for x in events if x['kind'] in ['pageerror','crash','testException']]
result={'pass':False,'lastTicks':ticks[-20:],'maxTick':max(ticks,default=0),'chunksSent':chks[-10:],'maxChunksSent':max(chks,default=0),'snapshots':snapshots,'samples':samples,'fatal':problems,'exception':failure,'recentServerLogs':[x for x in events if 'IntegratedServerWorker' in x['text']][-90:],'consoleErrors':[x for x in events if x['kind']=='error'][-30:]}
result['pass']=len(ticks)>=3 and max(ticks)>20 and ticks[-1]>ticks[0]+15 and max(chks,default=0)>3 and not problems and len(samples)>=4
(out/'results.json').write_text(json.dumps(result,indent=2))
(out/'events.json').write_text(json.dumps(events,indent=2))
print('FINAL',json.dumps({k:v for k,v in result.items() if k not in ('samples','recentServerLogs','consoleErrors')})[:5000],flush=True)
sys.exit(0 if result['pass'] else 2)

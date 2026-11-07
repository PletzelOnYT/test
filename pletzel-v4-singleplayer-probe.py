#!/usr/bin/env python3
"""Actual unmodified V4 candidate singleplayer reproduction probe, not a release test."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import http.server, threading, time, json, traceback, re

candidate=list(Path("candidate").rglob("*Schematica*CANDIDATE.html"))
assert len(candidate)==1,candidate
source=candidate[0].resolve()
out=Path("singleplayer-evidence")
out.mkdir(parents=True,exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(source.parent),**kwargs)
    def log_message(self,*args): pass

server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[]; steps=[]; stats=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=False,args=[
        "--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
        "--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
        "--use-gl=desktop","--disable-features=Vulkan"])
    page=browser.new_page(viewport={"width":1280,"height":720})
    page.on("console",lambda m:events.append({"t":time.monotonic(),"kind":"console-"+m.type,"text":m.text[:3000]}))
    page.on("pageerror",lambda e:events.append({"t":time.monotonic(),"kind":"pageerror","text":str(e)[:3000]}))
    page.on("crash",lambda:events.append({"t":time.monotonic(),"kind":"pagecrash","text":"crash"}))
    page.on("worker",lambda w:events.append({"t":time.monotonic(),"kind":"worker-created","text":w.url}))
    page.add_init_script("""(() => {
        window.__pletzelProbe={started:performance.now(), workers:0, workerMessages:0, workerErrors:0, workerDetails:[]};
        const W=window.Worker;
        window.Worker=class extends W {
            constructor(...args){
                super(...args);
                const p=window.__pletzelProbe;p.workers++;
                p.workerDetails.push({url:String(args[0]).slice(0,200),start:performance.now(),messages:0});
                const detail=p.workerDetails[p.workerDetails.length-1];
                this.addEventListener('message',()=>{p.workerMessages++;detail.messages++});
                this.addEventListener('error',e=>{p.workerErrors++;console.error('[PLETZEL-PROBE] worker error '+e.message)});
                this.addEventListener('messageerror',e=>{p.workerErrors++;console.error('[PLETZEL-PROBE] worker messageerror')});
            }
        };
    })();""")
    def capture(label):
        try:
            page.screenshot(path=str(out/(label+".png")),timeout=20000)
            js=page.evaluate("""() => ({
                url:location.href,documentState:document.readyState,
                webgl2:!!document.createElement('canvas').getContext('webgl2'),
                hasIndexedDB:!!window.indexedDB,workers:window.__pletzelProbe,
                canvasCount:document.querySelectorAll('canvas').length,
                runtime:Math.round(performance.now())
            })""")
            stats.append({"label":label,"sample":js})
        except Exception as e: events.append({"kind":"capture-exception","text":str(e)})
        steps.append(label)
    def click(label,x,y,wait=5):
        page.mouse.click(x,y)
        time.sleep(wait)
        capture(label)
    try:
        url=f"http://127.0.0.1:{server.server_address[1]}/{source.name}"
        page.goto(url,wait_until="domcontentloaded",timeout=120000)
        time.sleep(25);capture("01-boot")
        click("02-profile",638,618,8)
        click("03-continue",638,572,8)
        click("04-singleplayer-world-list",640,353,12)
        click("05-create-new-world",642,575,8)
        click("06-create-world-start",642,635,20)
        for i in range(1,7):
            time.sleep(20)
            capture(f"07-world-progress-{i}")
    except Exception as e:
        events.append({"kind":"test-exception","text":str(e)+"\n"+traceback.format_exc()[-1500:]})
    (out/"probe.json").write_text(json.dumps({"steps":steps,"stats":stats,"events":events,"note":"UNMODIFIED original artifact; screenshot snapshots require validation, the probe itself is not a pass"},indent=2))
    print(json.dumps({"steps":steps,"last_stats":stats[-3:],"last_events":events[-35:]},indent=2)[:13000],flush=True)
    browser.close()
server.shutdown()

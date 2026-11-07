#!/usr/bin/env python3
"""Inspect unmodified exact root-fixed candidate's real Create World UI for creative block-placement test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time,threading,http.server,json,traceback
candidate=list(Path("candidate").rglob("*.html"));assert len(candidate)==1,candidate
source=candidate[0].resolve()
out=Path("comparison-navigation");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(source.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
screens=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
 page=browser.new_page(viewport={"width":1280,"height":720})
 page.on("console",lambda m: errors.append(m.text[:1200]) if m.type=="error" else None)
 def snap(name):
  try:page.screenshot(path=str(out/(name+".png")),timeout=18000);screens.append(name);print("SNAP",name,flush=True)
  except Exception as e:print("SCREEN FAIL",e,flush=True)
 try:
  page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{source.name}",wait_until="domcontentloaded",timeout=150000)
  time.sleep(25);snap("01-boot")
  for name,x,y,delay in [("02-profile",638,618,6),("03-main-menu",638,572,6),("04-singleplayer-menu",638,353,7),("05-create-world-choice",638,282,7)]:
   page.mouse.click(x,y);time.sleep(delay);snap(name)
 except Exception:print(traceback.format_exc()[-2000:],flush=True)
 browser.close()
srv.shutdown()
(out/"summary.json").write_text(json.dumps({"screens":screens,"errors":errors[-20:]},indent=2))

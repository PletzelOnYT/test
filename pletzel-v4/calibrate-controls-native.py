#!/usr/bin/env python3
"""Inspect actual vanilla Options->Controls click coordinates in native game."""
import http.server,threading,time,traceback,json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path("candidate");htmls=list(root.rglob("*.html"));assert len(htmls)==1
html=htmls[0];out=Path("controls-ui-calibration");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(html.parent.resolve()),**kw)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
frames=[];error=None;started=time.monotonic()
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl',
      '--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=b.new_page(viewport={'width':1280,'height':720},device_scale_factor=1)
  def shot(name):
   page.wait_for_timeout(1300)
   page.screenshot(path=str(out/(name+".png")))
   frames.append(name)
   print('CALIBRATE',name,round(time.monotonic()-started,1),flush=True)
  page.goto(f'http://127.0.0.1:{srv.server_address[1]}/{html.name}',wait_until='domcontentloaded',timeout=150000)
  page.wait_for_timeout(23000)
  page.mouse.click(640,617);page.wait_for_timeout(700)
  page.mouse.click(640,666);page.wait_for_timeout(700)
  page.keyboard.press("Escape");shot('01-title-main')
  page.mouse.click(480,570);shot('02-options-screen')
  page.mouse.click(825,363);shot('03-native-controls-screen')
  page.mouse.click(400,350);shot('04-input-mode-first-cycle')
  page.mouse.click(400,350);shot('05-input-mode-second-cycle')
  b.close()
except Exception:
 error=traceback.format_exc()
 print(error[-4500:],flush=True)
finally:
 srv.shutdown()
(out/'result.json').write_text(json.dumps({'frames':frames,'error':error},indent=2))
if error:raise SystemExit(2)

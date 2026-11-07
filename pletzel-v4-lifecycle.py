#!/usr/bin/env python3
"""Singleplayer world move, save/quit, reopening exploration. Screen evidence required."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import time,threading,http.server,json,re,traceback
out=Path('lifecycle-evidence');out.mkdir(exist_ok=True)
files=list(Path('candidate').rglob('*.html'));assert len(files)==1,files
src=files[0].resolve();records=[];screens=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(src.parent),**kw)
 def log_message(self,*a): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
t=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on('console',lambda m:records.append({'t':round(time.monotonic()-t,1),'type':m.type,'text':m.text[:1500]}))
  page.on('pageerror',lambda e:records.append({'t':round(time.monotonic()-t,1),'type':'pageerror','text':str(e)}))
  def snap(name):
   page.screenshot(path=str(out/(name+'.png')),timeout=25000);screens.append(name);print('SNAP',name,flush=True)
  page.goto(f'http://127.0.0.1:{server.server_address[1]}/{src.name}?perfdebug',wait_until='domcontentloaded',timeout=150000)
  time.sleep(105);snap('01-world-before-movement')
  page.keyboard.down('w');page.keyboard.down('space');time.sleep(35)
  page.keyboard.up('space');page.keyboard.up('w');snap('02-world-after-movement')
  page.keyboard.press('Escape');time.sleep(3);snap('03-pause-menu')
  page.mouse.click(638,454);time.sleep(10);snap('04-after-save-and-quit-attempt')
  page.mouse.click(640,353);time.sleep(8);snap('05-reopen-world-selector')
  page.mouse.click(638,320);time.sleep(7);snap('06-select-existing-world-attempt')
  page.mouse.click(640,633);time.sleep(40);snap('07-reopen-terrain-attempt')
  browser.close()
except Exception:
 records.append({'type':'test-exception','text':traceback.format_exc()[-2000:]})
server.shutdown()
(out/'records.json').write_text(json.dumps({'screens':screens,'events':records},indent=2))
print('screens',screens,'errors',[x for x in records if x['type'] in ('error','pageerror','test-exception')][-15:],flush=True)

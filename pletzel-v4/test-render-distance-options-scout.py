#!/usr/bin/env python3
"""Read-only real Chrome scout to locate Minecraft 26.2 render-distance slider."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server,threading,time,json,traceback,sys
files=list(Path('candidate').rglob('*.html'));assert len(files)==1
game=files[0].resolve();out=Path('video-options-scout');out.mkdir(exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(game.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
events=[];fault=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=__import__('shutil').which('google-chrome') or __import__('shutil').which('google-chrome-stable'),
    headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on('console',lambda m:events.append(m.text[:1000]))
  page.goto('http://127.0.0.1:%d/%s?perfdebug'%(srv.server_address[1],game.name),wait_until='domcontentloaded',timeout=150000)
  page.wait_for_timeout(135000)
  def snap(name):
   page.screenshot(path=str(out/(name+'.png')),timeout=60000)
   print('VIDEO_SCOUT_SNAPSHOT',name,flush=True)
  snap('01-world')
  page.keyboard.press('Escape');page.wait_for_timeout(2000);snap('02-pause')
  page.mouse.click(478,394);page.wait_for_timeout(2000);snap('03-options')
  page.mouse.click(408,362);page.wait_for_timeout(2000);snap('04-video-top')
  for n,step in enumerate([150,200,200,200,200,200],1):
   page.mouse.move(640,400);page.mouse.wheel(0,step)
   page.wait_for_timeout(1100);snap('05-video-scroll-'+str(n))
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print('VIDEO_SCOUT_FAILURE',fault[-4000:],flush=True)
finally:srv.shutdown()
(out/'report.json').write_text(json.dumps({'fault':fault,'errorCount':len(events)},indent=2))
if fault:sys.exit(2)

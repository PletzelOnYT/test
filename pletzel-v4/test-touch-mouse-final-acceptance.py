#!/usr/bin/env python3
"""Real Minecraft 26.2 Controls Input Mode, override, and persistence acceptance.

Chromium CDP produces real PointerEvent mouse and TouchEvent touch streams.
All status is observed via screenshots of the actual WebGL game canvas.
No fake DOM button injection or artificial game client settings.
"""
import http.server,threading,traceback,json,sys,time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
htmls=list(Path('candidate').rglob('*.html'))
assert len(htmls)==1,htmls
html=htmls[0]
out=Path('input-mode-override-evidence')
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(html.parent.resolve()),**kw)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[];records=[];fault=None
start=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage',
      '--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader',
      '--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720},
                        device_scale_factor=1,has_touch=True,is_mobile=False)
  page.on('pageerror',lambda e:events.append({'type':'pageerror','value':str(e)[:2000]}))
  page.on('console',lambda e:events.append({'type':e.type,'value':e.text[:2000]}))
  def score(png):
   im=Image.open(png).convert('RGB')
   w,h=im.size
   # Real Minecraft touch toolbar: upper-right 'FS' tile.
   x0=int(w*.925); y0=int(h*.013);x1=int(w*.998);y1=int(h*.13)
   return sum(1 for r,g,b in im.crop((x0,y0,x1,y1)).getdata()
              if min(r,g,b)>165 and max(r,g,b)-min(r,g,b)<45)
  def screenshot(name,expected=None,delay=0.6):
   page.wait_for_timeout(int(delay*1000))
   path=out/(name+'.png');page.screenshot(path=str(path),timeout=30000)
   count=score(path)
   record={'name':name,'elapsed':round(time.monotonic()-start,2),
           'toolbar_bright_pixels':count,'expected':expected}
   records.append(record)
   print('REAL_INPUT_OVERRIDE',json.dumps(record),flush=True)
   if expected=='on' and count<300:
    raise AssertionError('Touchscreen controls not active on '+name)
   if expected=='off' and count>100:
    raise AssertionError('Mouse controls not restored on '+name)
  def menu():
   # Profile may appear only on the first clean install.
   page.mouse.click(640,617);page.wait_for_timeout(500)
   page.mouse.click(640,666);page.wait_for_timeout(500)
   page.keyboard.press('Escape')
   screenshot('00-initial-main-menu',None,0.8)
  def open_controls():
   page.mouse.click(480,570);page.wait_for_timeout(800)
   page.mouse.click(825,363);page.wait_for_timeout(800)
  def cycle_mode():
   page.mouse.click(400,364);page.wait_for_timeout(500)
  page.goto(f'http://127.0.0.1:{server.server_address[1]}/{html.name}',
      wait_until='domcontentloaded',timeout=150000)
  page.wait_for_timeout(22000)
  menu()
  page.mouse.move(300,485)
  open_controls()
  screenshot('01-controls-auto', 'off')
  # Auto -> Mouse & Keyboard: physical mouse forced while touch events flow.
  cycle_mode()
  screenshot('02-force-mouse', 'off')
  page.touchscreen.tap(1150,240)
  screenshot('03-force-mouse-ignores-real-touch','off')
  page.keyboard.press('Tab')
  screenshot('04-force-mouse-keyboard-stable','off')
  # Mouse -> Touchscreen: mouse and mouse clicks may not suppress touch controls.
  cycle_mode()
  screenshot('05-force-touchscreen', 'on')
  page.mouse.move(250,510)
  page.mouse.click(250,510)
  screenshot('06-force-touchscreen-ignores-real-mouse','on')
  page.keyboard.press('Tab')
  screenshot('07-force-touchscreen-keyboard-stable','on')
  # Reset page: prefer/reload actual saved options, still forced touchscreen.
  page.reload(wait_until='domcontentloaded',timeout=150000)
  page.wait_for_timeout(21000)
  screenshot('08-after-reload-forced-touchscreen','on')
  # Navigate main -> Options -> Controls in real game and prove state visually.
  open_controls()
  screenshot('09-controls-saved-touchscreen','on')
  # Touchscreen -> Auto
  cycle_mode()
  page.mouse.move(250,512)
  screenshot('10-restored-auto-mouse','off')
  page.touchscreen.tap(1160,250)
  screenshot('11-auto-touch-again','on')
  page.keyboard.press('ArrowUp')
  screenshot('12-keyboard-does-not-leave-touch','on')
  page.mouse.move(240,485)
  screenshot('13-mouse-movement-alone-leaves-touch','off')
  page.touchscreen.tap(1180,260)
  screenshot('14-auto-touch-second','on')
  page.mouse.click(220,490)
  screenshot('15-mouse-click-leaves-touch','off')
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print('REAL_OVERRIDE_FAILURE',fault[-5000:],flush=True)
finally:
 server.shutdown()
summary={'filename':html.name,'records':records,'page_errors':[e for e in events if e['type']=='pageerror'],'error':fault}
(out/'result.json').write_text(json.dumps(summary,indent=2))
(out/'console.json').write_text(json.dumps(events,indent=2))
if fault or summary['page_errors']:sys.exit(2)
if len(records)<15:sys.exit(3)
print('PASS: real in-game Controls forced mouse, forced touchscreen, saved mode reload, Auto mouse and touch movement/click',flush=True)

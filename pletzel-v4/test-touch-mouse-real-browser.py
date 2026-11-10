#!/usr/bin/env python3
"""Real Chromium Eaglercraft 26.2 hybrid-pointer input regression.

Uses actual Playwright CDP mouse.move/click and touchscreen.tap events on the
compiled WebGL/Wasm-GC canvas. No DOM facade, no fake mouse compatibility
events, no JS injection into the game and no HTML overlays.
"""
import http.server, json, sys, time, threading, traceback
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

root=Path('candidate')
htmls=list(root.rglob('*.html'))
assert len(htmls)==1,htmls
html=htmls[0]
out=Path('touch-mouse-evidence')
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(html.parent.resolve()),**kw)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
started=time.monotonic()
events=[];frames=[];failure=None

def touch_ui_score(path):
 im=Image.open(path).convert('RGB')
 w,h=im.size
 # Native touch FS control is top right, 4px in from the game GUI edge.
 # GUI scales to 3 at this viewport, approximately x=1185:1269 y=12:84.
 box=(round(w*.925), round(h*.013),round(w*.998),round(h*.13))
 crop=im.crop(box)
 pixels=list(crop.getdata())
 whites=sum(1 for r,g,b in pixels if min(r,g,b)>165 and max(r,g,b)-min(r,g,b)<45)
 return {'bright_neutral_pixels':whites,'bounding_box':box}

try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=[
   '--no-sandbox','--disable-dev-shm-usage','--enable-webgl',
   '--ignore-gpu-blocklist','--enable-unsafe-swiftshader',
   '--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720},
      device_scale_factor=1,has_touch=True,is_mobile=False)
  page.on('pageerror',lambda e:events.append({'type':'pageerror','text':str(e)[:2000]}))
  page.on('console',lambda m:events.append({'type':m.type,'text':m.text[:2000]}))
  def shot(name,delay=0.5):
   page.wait_for_timeout(int(delay*1000))
   file=out/(name+'.png')
   page.screenshot(path=str(file),timeout=30000)
   data={'name':name,'seconds':round(time.monotonic()-started,1),
         'touch_ui':touch_ui_score(file)}
   frames.append(data)
   print('INPUT_SCREEN',json.dumps(data),flush=True)
  page.goto(f'http://127.0.0.1:{server.server_address[1]}/{html.name}',wait_until='domcontentloaded',timeout=150000)
  shot('01-initial-game',24)
  # Accept the original game's optional first-run Eagler profile and username gate.
  page.mouse.click(640,617);shot('02-profile-optional',1)
  page.mouse.click(640,666);shot('03-username-optional',1)
  page.keyboard.press('Escape');shot('04-main-before-device-test',1)
  # Real physical mouse events put the automatic mode into desktop mode.
  page.mouse.move(250,285)
  page.mouse.click(250,285)
  shot('05-real-mouse-initial')
  for i in range(1,5):
   # Actual Chromium touchstart/touchend and compatibility mouse traffic.
   page.touchscreen.tap(1120,270+i*15)
   shot(f'{i:02d}-touch-stays-on-through-compat-events',0.65)
   # A genuine pointerType=mouse movement and click must defeat the touch latch
   # immediately; no reload, keyboard shortcut, timeout or manual preference.
   page.mouse.move(230,270+i*17)
   page.mouse.click(230,270+i*17)
   shot(f'{i:02d}-real-mouse-switches-back',0.5)
  # Re-enter touch mode, then validate native warning GUI still responds.
  page.touchscreen.tap(1120,275)
  shot('14-final-touch-active',0.65)
  page.mouse.move(250,290)
  page.mouse.click(250,290)
  shot('15-returned-to-desktop',0.5)
  page.mouse.click(640,354)
  shot('16-native-singleplayer-warning',1.5)
  page.keyboard.press('Escape')
  shot('17-warning-esc-native-menu',1.5)
  # Verify interface redraws after viewport resize in either input mode.
  page.touchscreen.tap(1080,320)
  shot('18-touch-before-resize')
  page.set_viewport_size({'width':1024,'height':768})
  shot('19-touch-after-resize',1.5)
  page.mouse.move(250,290)
  page.mouse.click(250,290)
  shot('20-mouse-after-resize')
  browser.close()
except Exception:
 failure=traceback.format_exc()
 print('ERROR',failure[-4000:],flush=True)
finally:
 server.shutdown()
result={'binary':html.name,'frames':frames,'page_errors':[v for v in events if v['type']=='pageerror'],
        'error':failure,'actual_browser_pointer_and_touch_events':True}
(out/'result.json').write_text(json.dumps(result,indent=2))
(out/'console.json').write_text(json.dumps(events,indent=2))
if failure or len(frames)!=20 or result['page_errors']:
 print('FAILED_BROWSER_EVENT_REGRESSION',flush=True);sys.exit(2)
# Require the same native toolbar to reappear consistently for real touch and
# disappear for real mouse. Golden images are preserved for human inspection.
pairs=[(f'{i:02d}-touch-stays-on-through-compat-events',
         f'{i:02d}-real-mouse-switches-back') for i in range(1,5)]
by_name={f['name']:f for f in frames}
for touch,mouse in pairs:
 touch_pixels=by_name[touch]['touch_ui']['bright_neutral_pixels']
 mouse_pixels=by_name[mouse]['touch_ui']['bright_neutral_pixels']
 print('TOUCH_MOUSE_NATIVE_TOOLBAR',touch,touch_pixels,mouse,mouse_pixels,flush=True)
 if touch_pixels <= mouse_pixels+20:
  raise SystemExit('Native touch toolbar did not visibly switch off on real mouse: '+touch)
print('PASS: four real touchscreen/mouse switch cycles with native GUI screenshots',flush=True)

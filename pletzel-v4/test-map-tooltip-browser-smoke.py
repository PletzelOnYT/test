#!/usr/bin/env python3
"""Real Chromium/WebGL smoke evidence for native Pletzel V4 Singleplayer warning.
Screenshots are real game canvas pixels, not generated HTML overlays.
"""
import http.server, threading, time, json, traceback, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

root=Path('candidate')
htmls=list(root.rglob('*.html'))
assert len(htmls)==1, htmls
html=htmls[0]
out=Path('map-tooltip-ui-browser-evidence')
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(html.parent.resolve()),**kwargs)
 def log_message(self,*args): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
shots=[];events=[];failure=None
started=time.monotonic()

def score(path):
 image=Image.open(path).convert('RGB')
 width,height=image.size
 points=image.load()
 regions={'gold':(0,int(height*.04),width,int(height*.27)),
          'red':(0,int(height*.08),width,int(height*.78)),
          'green':(0,int(height*.79),width,height)}
 result={}
 for name,(x0,y0,x1,y1) in regions.items():
  count=0
  for y in range(y0,y1,2):
   for x in range(x0,x1,2):
    r,g,b=points[x,y]
    if name=='gold': match=r>135 and g>75 and b<125 and r>g*1.25
    elif name=='red': match=r>135 and g<125 and b<140 and r>g*1.5
    else: match=g>125 and r<155 and b<165 and g>r*1.35
    if match: count+=1
  result[name]=count
 return result

try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=[
   '--no-sandbox','--disable-dev-shm-usage','--enable-webgl',
   '--ignore-gpu-blocklist','--enable-unsafe-swiftshader',
   '--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720},device_scale_factor=1)
  page.on('console',lambda m:events.append({'time':round(time.monotonic()-started,2),
      'kind':m.type,'text':m.text[:1000]}))
  page.on('pageerror',lambda m:events.append({'time':round(time.monotonic()-started,2),
      'kind':'pageerror','text':str(m)[:1000]}))
  def shot(name,seconds=2):
   page.wait_for_timeout(int(seconds*1000))
   file=out/(name+'.png')
   page.screenshot(path=str(file),timeout=30000)
   result={'name':name,'elapsed_s':round(time.monotonic()-started,1),
           'colors':score(file)}
   shots.append(result)
   print('NATIVE_MAPTOOLTIP_UI_SCREEN',json.dumps(result),flush=True)
  def click(x,y):
   page.mouse.click(x,y)
   page.wait_for_timeout(400)
  page.goto(f'http://127.0.0.1:{srv.server_address[1]}/{html.name}',
            wait_until='domcontentloaded',timeout=150000)
  shot('01-startup-initial',20)
  # First-run Eagler profile sometimes precedes the title screen. The following
  # are native profile buttons at 1280x720, GUI scale 3.
  click(640,617);shot('02-after-optional-profile-done',1)
  click(640,666);shot('03-after-optional-username-warning',1)
  page.keyboard.press('Escape');shot('04-before-singleplayer',1)
  # The vanilla Singleplayer button is centered at GUI y=108, x=213.
  click(640,354);shot('05-singleplayer-warning',2)
  # Native Screen.setInitialFocus(continueButton) enables Enter.
  page.keyboard.press('Enter');shot('06-continue-world-selection',14)
  for _ in range(3):
   page.keyboard.press('Escape');page.wait_for_timeout(800)
  shot('07-world-selection-escape-to-main',1)
  click(640,354);shot('08-warning-back-test',1)
  # Second vanilla native button is in the bottom row on a 1280x720 viewport.
  click(900,604);shot('09-back-to-main',1)
  click(640,354);shot('10-warning-esc-test',1)
  page.keyboard.press('Escape');shot('11-escape-to-main',1)
  # Multiplayer must not use Singleplayer warning.
  click(640,426);shot('12-multiplayer',2)
  page.keyboard.press('Escape')
  page.keyboard.press('Escape')
  shot('13-return-menu',1)
  click(640,354);shot('14-responsive-before-resize',1)
  page.set_viewport_size({'width':1024,'height':768})
  shot('15-responsive-after-resize',3)
  page.keyboard.press('Escape');shot('16-responsive-esc',1)
  browser.close()
except Exception:
 failure=traceback.format_exc()
 print('BROWSER_EXCEPTION',failure[-5000:],flush=True)
finally:
 srv.shutdown()
result={'html':html.name,'screens':shots,'page_errors':[x for x in events if x['kind']=='pageerror'],
        'error':failure,'manual_screenshot_review_required':True,
        'notes':'Native warning regression only. Map tooltip two-real-maps pixel test requires an actual map-bearing save or gameplay provisioning; this smoke alone does not verify map previews.'}
(out/'result.json').write_text(json.dumps(result,indent=2))
(out/'console.json').write_text(json.dumps(events,indent=2))
if failure: sys.exit(2)
if len(shots)!=16:sys.exit(3)
expected_warning=['05-singleplayer-warning','08-warning-back-test','10-warning-esc-test',
                  '14-responsive-before-resize','15-responsive-after-resize']
by_name={x['name']:x for x in shots}
for name in expected_warning:
 if name not in by_name:
  raise SystemExit('Missing real in-game warning canvas: '+name)
 colors=by_name[name]['colors']
 for channel,min_count in [('gold',20),('red',20),('green',20)]:
  if colors.get(channel,0)<min_count:
   raise SystemExit(f'Missing native {channel} warning text in {name}: {colors}')
print('PASS: real Minecraft canvas warning colors visible before Continue, before Back, '
      'before ESC, and after viewport resize',flush=True)

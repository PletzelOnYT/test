#!/usr/bin/env python3
"""Genuine 26.2 WebGL canvas checks of original Steve/Alex player model chooser.
No game HTML modifications, CDP DOM fakery, fake button injection or replaced UI.
Open first-run Profile, click model for a BUILT-IN PRESET, choose Alex, then Steve.
"""
import http.server,threading,time,json,sys,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image,ImageChops,ImageStat

root=Path("candidate")
html=list(root.rglob("*.html"));assert len(html)==1,html
out=Path("profile-model-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(html[0].parent.resolve()),**kwargs)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
events=[];screens=[];fault=None;started=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720},device_scale_factor=1)
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-started,2),"kind":m.type,"text":m.text[:2200]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-started,2),"kind":"pageerror","text":str(e)[:2200]}))
  def snap(name):
   path=out/(name+".png")
   page.screenshot(path=str(path),timeout=30000)
   screens.append(name);print("PROFILE_SNAP",name,round(time.monotonic()-started,1),flush=True)
  page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{html[0].name}?perfdebug",wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(22000)
  snap("01-original-profile-and-selected-preset")
  # Game GUI scale is 3 at 1280x720; model button is x579..999 y258..312
  # and was hidden before this source repair for non-custom skins.
  page.mouse.click(710,283);page.wait_for_timeout(3200)
  snap("02-model-chooser-open-on-preset")
  # Native chooser buttons y552..612; right is Alex (Slim) and left Steve.
  page.mouse.click(791,582);page.wait_for_timeout(3600)
  snap("03-native-alex-model-selected")
  page.mouse.click(710,283);page.wait_for_timeout(3200)
  snap("04-native-model-chooser-reopened")
  page.mouse.click(457,582);page.wait_for_timeout(3200)
  snap("05-native-steve-model-selected")
  page.mouse.click(710,283);page.wait_for_timeout(2800)
  snap("06-native-chooser-still-accessible")
  page.keyboard.press("Escape");page.wait_for_timeout(2300)
  snap("07-chooser-exit-preserves-selection")
  browser.close()
except Exception:
 fault=traceback.format_exc();print(fault[-3500:],flush=True)
finally:srv.shutdown()
def measure(a,b,xyxy):
 x1,y1,x2,y2=xyxy
 a=Image.open(out/(a+".png")).convert("RGB").crop(xyxy)
 b=Image.open(out/(b+".png")).convert("RGB").crop(xyxy)
 return {"changed_pixels":sum(1 for pixel in ImageChops.difference(a,b).getdata() if pixel!=(0,0,0)),"pixels":(x2-x1)*(y2-y1)}
metrics={}
if len(screens)>=5:
 metrics["model_button_visible_vs_chooser"]=measure(screens[0],screens[1],(565,245,1010,330))
 metrics["alex_selected_vs_steve_selected"]=measure(screens[2],screens[4],(565,245,1010,330))
# Human screenshot review still essential: model silhouettes and names must be visible.
result={"screens":screens,"model_widget_pixel_differences":metrics,"page_errors":[e for e in events if e["kind"]=="pageerror"],"error":fault,
        "manual_review_required":"Verify native Steve/Alex chooser, real slim vs wide arms, preset dropdown pairing, reload persistence and multiplayer profile semantics"}
(out/"results.json").write_text(json.dumps(result,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("PROFILE_EVIDENCE",json.dumps(result),flush=True)
if fault or len(screens)!=7 or result["page_errors"]:sys.exit(2)
for name,m in metrics.items():
 if m["changed_pixels"]<100:
  raise SystemExit("No visible button or model change in region: "+name)

#!/usr/bin/env python3
"""Actual WebGL Minecraft Controls UI ON/OFF persistence browser acceptance.

No DOM controls or direct option setters: all interaction is by the real
Minecraft GUI and pointer clicks. Requires the pinned compiled dual-tooltip
standalone HTML; it never alters the HTML or binary.
"""
import http.server, threading, time, json, traceback, sys
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

htmls=list(Path("candidate").rglob("*.html"))
assert len(htmls)==1,htmls
html=htmls[0]
out=Path("map-shulker-settings-evidence")
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent.resolve()),**kw)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
events=[];screens=[];problem=None
start=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage",
       "--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
       "--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720},device_scale_factor=1)
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-start,1),"kind":m.type,"message":m.text[:1200]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-start,1),"kind":"pageerror","message":str(e)[:1600]}))
  def shot(name):
   page.mouse.move(1200,680)
   page.wait_for_timeout(900)
   file=out/(name+".png")
   page.screenshot(path=str(file),timeout=30000)
   screens.append(name)
   print("NATIVE_TOOLTIP_OPTIONS_SCREEN",name,round(time.monotonic()-start,1),flush=True)
  def click(x,y):
   page.mouse.click(x,y)
   page.wait_for_timeout(1000)
  def controls():
   click(480,570)
   click(825,363)
  page.goto(f"http://127.0.0.1:{server.server_address[1]}/{html.name}",wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(21000)
  # First run Profile -> default username note -> main menu.
  click(640,617)
  click(640,666)
  page.keyboard.press("Escape")
  shot("01-real-main-menu")
  controls()
  shot("02-both-default-on")
  # First row after Input Mode: Map Tooltip is right side. Next row:
  # Shulker Box Tooltip is left side. Based on actual vanilla Controls layout.
  click(840,364)
  shot("03-map-tooltip-off")
  click(400,438)
  shot("04-shulker-tooltip-off")
  # Settings must save through native Options and survive a reload.
  click(640,670)
  click(640,670)
  shot("05-closed-settings")
  page.reload(wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(22000)
  # Pletzel V4 opens Edit Profile after a full browser reload. Complete this
  # REAL first-run game GUI flow before attempting Options -> Controls.
  click(640,617)
  click(640,666)
  page.keyboard.press("Escape")
  shot("06-reloaded-main-menu")
  controls()
  shot("07-saved-off-after-reload")
  click(840,364)
  click(400,438)
  shot("08-both-restored-on")
  click(640,670)
  click(640,670)
  shot("09-back-at-main")
  browser.close()
except Exception:
 problem=traceback.format_exc()
 print("TOOLTIP_SETTINGS_ERROR",problem[-3800:],flush=True)
finally:
 server.shutdown()

def different(a,b,crop):
 f=out/(a+".png")
 g=out/(b+".png")
 if not f.exists() or not g.exists():return None
 x=Image.open(f).convert("RGB").crop(crop)
 y=Image.open(g).convert("RGB").crop(crop)
 return sum(1 for pixel in ImageChops.difference(x,y).getdata() if pixel!=(0,0,0))

metrics={
 "map_button_toggle_changed_pixels":different("02-both-default-on","03-map-tooltip-off",(658,338,1105,395)),
 "shulker_button_toggle_changed_pixels":different("03-map-tooltip-off","04-shulker-tooltip-off",(173,411,624,470)),
 "map_button_reloaded_off_changed_pixels":different("04-shulker-tooltip-off","07-saved-off-after-reload",(658,338,1105,395)),
 "shulker_button_reloaded_off_changed_pixels":different("04-shulker-tooltip-off","07-saved-off-after-reload",(173,411,624,470)),
 "map_button_restored_changed_pixels":different("07-saved-off-after-reload","08-both-restored-on",(658,338,1105,395)),
 "shulker_button_restored_changed_pixels":different("07-saved-off-after-reload","08-both-restored-on",(173,411,624,470))
}
result={"screenshots":screens,"metrics":metrics,
        "pageErrors":[x for x in events if x["kind"]=="pageerror"],
        "fault":problem,
        "note":"Button images require human verification of labels and ON/OFF states; pixels alone cannot prove setting persistence"}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("REAL_NATIVE_SETTINGS_RESULT",json.dumps(result)[:3400],flush=True)
if problem or len(screens)!=9 or result["pageErrors"]:sys.exit(2)
if any(metrics[k] is None or metrics[k]<70 for k in [
 "map_button_toggle_changed_pixels","shulker_button_toggle_changed_pixels",
 "map_button_restored_changed_pixels","shulker_button_restored_changed_pixels"
]):sys.exit(3)
print("PASS: actual in-game Controls buttons visibly change; review persisted screenshots",flush=True)

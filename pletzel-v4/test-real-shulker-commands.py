#!/usr/bin/env python3
"""Real game verification: no PASS without an actual Shulker Box hotbar item.

Runs the exact previous native GUI geometry build in Chromium, sends commands
using Playwright's real keyboard input (not DOM-dispatched fake key events),
and captures unmodified game-canvas screenshots. All conclusions are
grounded in visible inventory data; no fabricated items or overlays.
"""
from pathlib import Path
import http.server, threading, time, json, traceback, re, hashlib, sys
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
htmls=list(Path("candidate").rglob("*.html"))
assert len(htmls)==1,htmls
html=htmls[0].resolve()
out=Path("real-shulker-command-evidence")
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic(); events=[];shots=[];error=None
try:
 with sync_playwright() as p:
  b=p.chromium.launch(headless=False,args=[
    "--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
    "--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
    "--use-gl=desktop","--disable-features=Vulkan"])
  page=b.new_page(viewport={"width":1280,"height":720},device_scale_factor=1)
  page.on("console",lambda m:events.append({
    "t":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:2000]}))
  page.on("pageerror",lambda e:events.append({
    "t":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:1800]}))
  def shot(name):
   f=out/(name+".png");page.screenshot(path=str(f),timeout=40000)
   shots.append({"name":name,"elapsed_s":round(time.monotonic()-start,1)})
   print("CANVAS",name,shots[-1]["elapsed_s"],flush=True)
  def click(x,y,ms=1200):page.mouse.click(x,y);page.wait_for_timeout(ms)
  def command(text):
   # Slash opens Minecraft's COMMAND input, with / already populated.
   # Unlike previous scripted 't' plus synthetic key events, no leading '/'
   # can silently disappear in the event queue.
   page.keyboard.press("Slash")
   page.wait_for_timeout(1250)
   shot("command_open_"+text.split(" ")[0])
   page.keyboard.type(text,delay=45)
   page.wait_for_timeout(1250)
   shot("command_typed_"+text.split(" ")[0])
   page.keyboard.press("Enter")
   page.wait_for_timeout(2700)
   shot("command_result_"+text.split(" ")[0])
  page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{html.name}?perfdebug",
    wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(24000);shot("01-profile")
  click(638,618,2600);click(638,572,2500);shot("02-title")
  click(638,353,1500);shot("03-singleplayer-warning")
  page.keyboard.press("Enter");page.wait_for_timeout(12000);shot("04-world-chooser")
  click(638,282,12500);shot("05-create-world")
  click(638,257,650);click(638,257,650)
  click(638,426,950);shot("06-creative-cheats-on")
  click(405,672,5500);shot("07-creating-world")
  t0=time.monotonic();world_ready=False
  while time.monotonic()-t0<330:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",e)) and int(m.group(1))>300 for e in beats):
    world_ready=True;break
   page.wait_for_timeout(2700)
  shot("08-real-world")
  if not world_ready:raise RuntimeError("World never finished >300 integrated-server ticks")
  click(638,360,950)
  shot("09-before-give-hotbar")
  command("give @p minecraft:shulker_box 1")
  shot("10-after-give-hotbar")
  command("give @p minecraft:red_shulker_box 1")
  shot("11-after-red-give")
  command('give @p minecraft:green_shulker_box[minecraft:container=[{slot:0,item:{id:"minecraft:diamond",count:42}},{slot:8,item:{id:"minecraft:golden_apple",count:5}}]] 1')
  shot("12-after-populated-give")
  page.keyboard.press("e");page.wait_for_timeout(4900);shot("13-creative-inventory-with-genuine-items")
  # The creative hotbar is the actual bottom row, y≈682 at GUI scale 3.
  for name,x in [("14-undyed-box-preview",397),
                 ("15-red-box-preview",456),
                 ("16-green-filled-box-preview",514)]:
   page.mouse.move(x,680)
   page.wait_for_timeout(3300)
   shot(name)
  page.keyboard.press("Escape");page.wait_for_timeout(1600)
  page.set_viewport_size({"width":1024,"height":768})
  page.keyboard.press("e");page.wait_for_timeout(3800)
  shot("17-resized-inventory")
  b.close()
except Exception:
 error=traceback.format_exc()
 print("BROWSER_ERROR",error[-5000:],flush=True)
finally:
 srv.shutdown()

def difference(a,b,rect):
 p=out/(a+".png");q=out/(b+".png")
 if not (p.exists() and q.exists()):return None
 first=Image.open(p).convert("RGB").crop(rect)
 second=Image.open(q).convert("RGB").crop(rect)
 return sum(1 for pix in ImageChops.difference(first,second).getdata() if pix!=(0,0,0))
metrics={
 "hotbar_first_give_changed":difference("09-before-give-hotbar","10-after-give-hotbar",(365,651,914,717)),
 "hotbar_second_give_changed":difference("10-after-give-hotbar","11-after-red-give",(365,651,914,717)),
 "hotbar_populated_give_changed":difference("11-after-red-give","12-after-populated-give",(365,651,914,717)),
 "red_vs_undyed_hover_changed":difference("14-undyed-box-preview","15-red-box-preview",(350,130,1200,715)),
 "populated_vs_red_hover_changed":difference("15-red-box-preview","16-green-filled-box-preview",(350,130,1200,715))
}
result={"html":html.name,"html_sha256":hashlib.sha256(html.read_bytes()).hexdigest(),
 "screens":shots,"metrics":metrics,"error":error,
 "pageErrors":[e for e in events if e["kind"]=="pageerror"],
 "manualRequirements":[
  "Confirm slash command chat includes leading / in command_open screenshots",
  "Confirm accepted server /give output, actual shulker item in hotbar, no red errors",
  "Confirm GUI backgrounds and 9x3 slots visible in hover screenshots",
  "Confirm filled box contains REAL diamond count 42 and golden apple count 5 in positions 0 and 8",
  "Do not accept pixel changes alone as proof of populated item contents"
 ]}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("REAL_SHULKER_RESULTS",json.dumps({"screens":len(shots),"metrics":metrics,"error":error})[:2500],flush=True)
if error or result["pageErrors"]:sys.exit(2)
if metrics["hotbar_first_give_changed"] is None or metrics["hotbar_first_give_changed"]<150:
 print("FAIL: /give produced no meaningful change to actual hotbar; cannot claim shulker tooltip passed")
 sys.exit(3)
if len(shots)<17:sys.exit(4)
print("BROWSER INPUT AND ITEM CREATION APPEAR VALID; inspect actual screenshots for visual acceptance",flush=True)

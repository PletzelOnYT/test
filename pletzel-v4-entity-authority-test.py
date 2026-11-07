#!/usr/bin/env python3
"""Non-mutating runtime verification of ORIGINAL compiled HTML, using only vanilla in-game commands.
UI commands/scoreboard are observed via screenshots; successful script exit is NOT proof of AI.
Screenshots plus server heartbeat and entity type tick counts must be reviewed.
"""
from pathlib import Path
import http.server, threading, time, json, traceback, re, os
from playwright.sync_api import sync_playwright

html_files=list(Path("candidate").rglob("*.html"))
assert len(html_files)==1, html_files
html=html_files[0].resolve()
out=Path("entity-authority-evidence")
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic(); events=[]; shots=[]; cmds=[]; fault=None
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:1800]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:1800]}))
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=45000)
   shots.append({"name":name,"elapsed":round(time.monotonic()-start,1)})
   print("SCREENSHOT",name,shots[-1]["elapsed"],flush=True)
  def send(command,delay=1):
   page.keyboard.press("t")
   page.wait_for_timeout(400)
   page.keyboard.type(command,delay=25)
   page.keyboard.press("Enter")
   page.wait_for_timeout(int(delay*1000))
   cmds.append(command)
   print("SENT",command,flush=True)
  page.goto("http://127.0.0.1:%s/%s?perfdebug"%(srv.server_address[1],html.name),wait_until="domcontentloaded",timeout=150000)
  # Heartbeat with >300 ticks is necessary but NOT enough. Commands must run while player is present.
  while time.monotonic()-start < 270:
   beats=[x["text"] for x in events if "[EagPerfHeartbeat]" in x["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",b)) and int(m.group(1))>320 for b in beats):break
   page.wait_for_timeout(4000)
  page.wait_for_timeout(15000)
  snap("00-inworld-before-command")
  page.mouse.click(640,354)
  page.wait_for_timeout(1100)
  # Command checks: if permission is unavailable, screenshot will show rejection.
  send("/time query gametime")
  snap("01-time-query")
  send("/scoreboard objectives add pletzelLive dummy")
  send("/scoreboard objectives setdisplay sidebar pletzelLive")
  send('/summon minecraft:chicken ~2 ~ ~2 {Tags:["PletzelProbe"],NoAI:0b}')
  snap("02-summon-chicken")
  send("/execute store result score worldTime pletzelLive run time query gametime")
  send("/execute store result score chickenX pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[0] 100")
  send("/execute store result score chickenZ pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[2] 100")
  send("/execute store result score chickenHP pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Health 100")
  snap("03-state-t0")
  page.wait_for_timeout(20000)
  send("/execute store result score worldTime pletzelLive run time query gametime")
  send("/execute store result score chickenX pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[0] 100")
  send("/execute store result score chickenZ pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[2] 100")
  send("/execute store result score chickenHP pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Health 100")
  snap("04-state-t20")
  send("/damage @e[tag=PletzelProbe,limit=1] 1")
  send("/execute store result score chickenHP pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Health 100")
  snap("05-damage-result")
  page.wait_for_timeout(18000)
  send("/execute store result score worldTime pletzelLive run time query gametime")
  send("/execute store result score chickenX pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[0] 100")
  send("/execute store result score chickenZ pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Pos[2] 100")
  send("/execute store result score chickenHP pletzelLive run data get entity @e[tag=PletzelProbe,limit=1] Health 100")
  snap("06-state-t40")
  send("/damage @e[tag=PletzelProbe,limit=1] 99")
  snap("07-kill-drop")
  page.wait_for_timeout(3000)
  send("/time query daytime")
  snap("08-time-final")
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("ERROR",fault[-4000:],flush=True)
finally:
 srv.shutdown()
beats=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
chicken=[e for e in events if "entity type=minecraft:chicken" in e["text"]]
result={"screenshots":shots,"commandsSent":cmds,"heartbeatCount":len(beats),
 "chickenTickReports":len(chicken),"recentChickenReports":chicken[-5:],
 "recentHeartbeat":beats[-3:],"fatal":fault,
 "pageErrors":[e for e in events if e["kind"]=="pageerror"][-20:],
 "disclaimer":"Screenshots require manual interpretation. Commands sent != commands accepted. No entity pass is asserted."}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"all-events.json").write_text(json.dumps(events,indent=2))
print("RESULT",json.dumps({"screens":len(shots),"commands":len(cmds),"chickenReports":len(chicken),"heartbeatCount":len(beats),"fault":fault})[:3000],flush=True)
if fault or len(shots)<8:raise SystemExit(2)

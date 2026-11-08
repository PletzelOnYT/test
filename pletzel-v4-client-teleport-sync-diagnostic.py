#!/usr/bin/env python3
"""Client vs server teleport F3 position diagnostic on exact compiled game; original compiled HTML unchanged.
UI commands/scoreboard are observed via screenshots; successful script exit is NOT proof of AI.
Screenshots plus server heartbeat and entity type tick counts must be reviewed.
"""
from pathlib import Path
import http.server, threading, time, json, traceback, re, os
from playwright.sync_api import sync_playwright

html_files=list(Path("candidate").rglob("*.html"))
assert len(html_files)==1, html_files
html=html_files[0].resolve()
out=Path("cheats-entity-evidence")
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
  # No auto-create: navigate world creation UI and enable real server commands.
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:1800]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:1800]}))
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=45000)
   shots.append({"name":name,"elapsed":round(time.monotonic()-start,1)})
   print("SCREENSHOT",name,shots[-1]["elapsed"],flush=True)
  def send(command,delay=1):
   page.keyboard.press("t")
   page.wait_for_timeout(1500)
   # Browser's real keyboard listener accepts the DOM keydown/up pair; dispatch
   # batched events so 1-3 FPS software Chromium does not require ~1 second/character.
   # Avoid inserting text via CDP: this game consumes key event queues, not a textarea.
   for off in range(0,len(command),42):
    chunk=command[off:off+42]
    page.evaluate("""(s) => {
      function info(c) {
        if(/^[A-Za-z]$/.test(c)) return ['Key'+c.toUpperCase(),c.toUpperCase().charCodeAt(0),c!==c.toLowerCase()];
        if(/^[0-9]$/.test(c)) return ['Digit'+c,c.charCodeAt(0),false];
        const special={' ':['Space',32,false],'/':['Slash',191,false],'~':['Backquote',192,true],
          '[':['BracketLeft',219,false],']':['BracketRight',221,false],
          '{':['BracketLeft',219,true],'}':['BracketRight',221,true],
          ':':['Semicolon',186,true],';':['Semicolon',186,false],
          '"':['Quote',222,true],"'":['Quote',222,false],
          '@':['Digit2',50,true],',':['Comma',188,false],
          '.':['Period',190,false],'-':['Minus',189,false],
          '_':['Minus',189,true],'=':['Equal',187,false],
          '^':['Digit6',54,true],'(':['Digit9',57,true],')':['Digit0',48,true]};
        return special[c]||['Unidentified',0,false];
      }
      for(const ch of s) {
        const [code,which,shiftKey]=info(ch);
        const opt={key:ch,code,shiftKey,bubbles:true,cancelable:true,composed:true};
        for(const kind of ['keydown','keyup']) {
          const ev=new KeyboardEvent(kind,opt);
          Object.defineProperty(ev,'which',{value:which});
          Object.defineProperty(ev,'keyCode',{value:which});
          window.dispatchEvent(ev);
        }
      }
    }""",chunk)
    page.wait_for_timeout(1250)
   page.keyboard.press("Enter")
   page.wait_for_timeout(int(max(delay,1)*1000))
   cmds.append(command)
   print("SENT",command,flush=True)
  page.goto("http://127.0.0.1:%s/%s?perfdebug"%(srv.server_address[1],html.name),wait_until="domcontentloaded",timeout=150000)
  # Fresh NORMAL Survival world, without __eaglerAutoTest shortcuts. Only cheats are enabled.
  page.wait_for_timeout(28000)
  snap("ui-01-profile")
  page.mouse.click(638,618);page.wait_for_timeout(7000);snap("ui-02-profile-warning")
  page.mouse.click(638,572);page.wait_for_timeout(7000);snap("ui-03-main-menu")
  page.mouse.click(638,353);page.wait_for_timeout(16000);snap("ui-04-select-world")
  page.mouse.click(638,282);page.wait_for_timeout(27000);snap("ui-05-create-world-options")
  # The first click ALREADY enters Create World. A second click at y=282 toggled
  # game mode to Hardcore in a previous run, silently disabling cheats.
  page.wait_for_timeout(1500);snap("ui-06-confirm-survival-before-cheats")
  # Explicitly set a reproducible world seed using the real World tab, not game code.
  # Screenshots preserve verification if the UI widget moves in future source versions.
  page.mouse.click(640,34);page.wait_for_timeout(2000);snap("ui-06a-world-tab")
  page.mouse.click(620,256);page.keyboard.press("Control+A");page.keyboard.type("246813579",delay=110)
  page.wait_for_timeout(2000);snap("ui-06b-seed-field-attempt")
  page.mouse.click(267,34);page.wait_for_timeout(2000);snap("ui-06c-game-tab-return")
  # The game settings screen from an existing artifact (not guessed) has Allow Cheats at (640,426).
  page.mouse.click(640,426);page.wait_for_timeout(1800);snap("ui-07-enable-cheats")
  page.mouse.click(404,672);page.wait_for_timeout(7000);snap("ui-08-creating-world")
  # A heartbeat does not prove world simulation; the following server-side state checks do.
  world_creation_at=time.monotonic()
  while time.monotonic()-world_creation_at < 280:
   beats=[x["text"] for x in events if "[EagPerfHeartbeat]" in x["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",b)) and int(m.group(1))>320 for b in beats):break
   page.wait_for_timeout(4000)
  page.wait_for_timeout(15000)
  snap("00-inworld-before-command")
  page.mouse.click(640,354)
  page.wait_for_timeout(1100)
  # Command checks: if permission is unavailable, screenshot will show rejection.
  send("/gamemode creative",2)
  send("/time set day",1)
  send("/time query gametime",1)
  snap("explore-00-creative-world")
  # Server scoreboard position readback and client F3 coordinate overlay isolate
  # whether authoritative /tp changes are delivered to the client camera.
  send("/scoreboard objectives add pletzelPos dummy")
  send("/scoreboard objectives setdisplay sidebar pletzelPos")
  send("/execute store result score playerX pletzelPos run data get entity @p Pos[0] 100")
  send("/execute store result score playerZ pletzelPos run data get entity @p Pos[2] 100")
  page.keyboard.press("F3");page.wait_for_timeout(6500)
  snap("client-f3-before-teleport")
  for leg in range(1,3):
   # Same seed, open sky vantage and fixed downward pitch.
   dest=f"/tp @p {96*leg} 190 {96*leg} 0 80"
   send(dest,2)
   page.wait_for_timeout(25000)
   send("/execute store result score playerX pletzelPos run data get entity @p Pos[0] 100")
   send("/execute store result score playerZ pletzelPos run data get entity @p Pos[2] 100")
   send("/time query gametime")
   page.wait_for_timeout(6500)
   snap(f"client-f3-after-teleport-{leg}")
  snap("client-f3-final")
  send("/seed",1)
  snap("client-f3-seed-confirmation")
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
 "disclaimer":"The script sends vanilla creative-mode and remote teleport commands to force new chunk generation, but command send != command success. Validate actual [CHAT] teleport acceptance, world seed screenshot, terrain screenshots and chunk telemetry before claiming exploration success."}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"all-events.json").write_text(json.dumps(events,indent=2))
print("RESULT",json.dumps({"screens":len(shots),"commands":len(cmds),"chickenReports":len(chicken),"heartbeatCount":len(beats),"fault":fault})[:3000],flush=True)
if fault or len(shots)<8:raise SystemExit(2)

#!/usr/bin/env python3
"""Real Pletzel WebGL shulker tooltip GUI parity test: real inventory and server commands.
All actual client pixels are captured unmodified; no tooltip overlays are injected.
A command submission is NOT evidence it succeeded. Manually review item and count screenshots.
"""
from pathlib import Path
import http.server, threading, time, json, traceback, re, os
from playwright.sync_api import sync_playwright

html_files=list(Path("candidate").rglob("*.html"))
assert len(html_files)==1, html_files
html=html_files[0].resolve()
out=Path("original-shulker-gui-gameplay-evidence")
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
  page.goto("http://127.0.0.1:%s/%s?perfdebug"%(srv.server_address[1],html.name),
      wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(26000);snap("01-first-boot-profile")
  page.mouse.click(638,618);page.wait_for_timeout(3000)
  page.mouse.click(638,572);page.wait_for_timeout(2500);snap("02-main-menu")
  page.mouse.click(638,353);page.wait_for_timeout(1700);snap("03-native-warning")
  page.keyboard.press("Enter");page.wait_for_timeout(12000);snap("04-world-chooser")
  page.mouse.click(638,282);page.wait_for_timeout(13000);snap("05-create-world")
  # The *real Minecraft GUI* rotates SURVIVAL -> HARDCORE -> CREATIVE.
  # Creative is essential here: prior survival tests drowned in water and
  # incorrectly claimed to have completed shulker screenshots.
  # Exact original 26.2 source order: SURVIVAL -> HARDCORE -> CREATIVE.
  # Two clicks are required; the previous rapid second click was missed
  # while software Chromium ran ~3 FPS. Give each native button time.
  page.mouse.click(638,257);page.wait_for_timeout(3500);snap("06a-hardcore-intermediate")
  page.mouse.click(638,257);page.wait_for_timeout(3500);snap("06-creative-chosen")
  # Do not toggle Allow Cheats blindly: Creative world default is ON.
  snap("07-creative-cheats-state")
  page.mouse.click(405,672);page.wait_for_timeout(7000);snap("08-world-creation")
  begin=time.monotonic()
  ready=False
  while time.monotonic()-begin<330:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",beat)) and int(m.group(1))>300 for beat in beats):
    ready=True
    break
   page.wait_for_timeout(4200)
  snap("09-world-loaded-checkpoint")
  if not ready:
   raise RuntimeError("No verified completed server ticks, cannot validate genuine inventory items")
  # Probe genuine Creative inventory search to avoid any cheat-permission,
  # command-length, or game-mode click ambiguity. The vanilla game provides
  # these shulker item stacks, rather than synthetic textures or item data.
  page.keyboard.press("e")
  page.wait_for_timeout(3000);snap("10-creative-inventory")
  # Compass icon is the vanilla Search Items tab in this Minecraft GUI.
  page.mouse.click(885,110)
  page.wait_for_timeout(1800);snap("11-search-items-tab")
  page.keyboard.type("shulker",delay=80)
  page.wait_for_timeout(2400);snap("12-search-shulker-results")
  # Search results in native inventory grid; inspect screenshot to confirm
  # the actual items under these slots before interpreting tooltip images.
  for name,x,y in [
     ("13-first-shulker-hover",400,234),
     ("14-second-shulker-hover",455,234),
     ("15-third-shulker-hover",508,234),
     ("16-fourth-shulker-hover",563,234),
     ("17-fifth-shulker-hover",616,234)
  ]:
    page.mouse.move(x,y)
    page.wait_for_timeout(1900);snap(name)
  page.mouse.move(885,110)
  page.wait_for_timeout(1500);snap("18-tooltip-away")
  page.set_viewport_size({"width":1024,"height":768})
  page.wait_for_timeout(2500);snap("19-resize-inventory")
  page.mouse.move(400,235)
  page.wait_for_timeout(2100);snap("20-resize-preview")
  page.keyboard.press("Escape")
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("ERROR",fault[-4000:],flush=True)
finally:
 srv.shutdown()
from hashlib import sha256
heartbeat=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
names=["13-first-shulker-hover","14-second-shulker-hover",
       "15-third-shulker-hover","16-fourth-shulker-hover",
       "17-fifth-shulker-hover"]
paths=[out/(name+".png") for name in names]
hashes=[sha256(path.read_bytes()).hexdigest() for path in paths if path.exists()]
report={"screenshots":shots,"heartbeatCount":len(heartbeat),
 "errors":[e for e in events if e["kind"]=="pageerror"],"fault":fault,
 "allFiveHoverScreenshotsIdentical":len(set(hashes))==1,
 "status":"BLOCKED" if fault or len(hashes)!=5 else "REVIEW_REQUIRED",
 "notes":[
 "These are genuine mouse hovers on vanilla Creative Search Items results",
 "Inspect 06a-hardcore-intermediate then 06-creative-chosen: Game Mode CREATIVE before world creation",
 "Inspect 12-search-shulker-results to confirm item stacks",
 "Inspect 13-17 to verify 176x68 pixel nine-slice panels and dye tints",
 "Different screenshot hashes alone do NOT prove shulker previews",
 "Populated 27-slot box needs independent real inventory test",
 "No mocked item contents and no client overlay"
 ]}
(out/"results.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("CREATIVE_SEARCH_SHULKER_RESULT",json.dumps({
 "snapshots":len(shots),"heartbeatCount":len(heartbeat),"status":report["status"],
 "allFiveHoverScreenshotsIdentical":report["allFiveHoverScreenshotsIdentical"],
 "fault":fault}),flush=True)
if fault or len(shots)<20 or len(hashes)!=5 or report["errors"]:
 raise SystemExit(2)
if len(set(hashes))==1:
 print("FAIL: all hovered shulker screenshot bytes identical",flush=True)
 raise SystemExit(5)
print("CAPTURE COMPLETE — genuine Shulker Tooltip visuals require screenshot inspection.",flush=True)

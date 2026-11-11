#!/usr/bin/env python3
"""Exact-HTML world save/reopen gameplay regression.

Exercise a genuine Survival world and server command, quit through the native
Pause UI, reopen the SAME saved world, and require the server to confirm the
diamond block persisted at the saved player position. No IndexedDB patching,
no fabricated world state, no mocked renderer.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server, threading, json, time, re, traceback, sys
htmls=list(Path("candidate").rglob("*.html"))
assert len(htmls)==1, htmls
html=htmls[0].resolve()
out=Path("world-save-reload-evidence");out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(html.parent),**kw)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
started=time.monotonic();events=[];screens=[];command_log=[];fault=None
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=False,args=[
    "--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
    "--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
    "--use-gl=desktop","--disable-features=Vulkan"])
  page=b.new_page(viewport={"width":1280,"height":720})
  page.on("console",lambda m:events.append({"at":round(time.monotonic()-started,1),"kind":m.type,"text":m.text[:2400]}))
  page.on("pageerror",lambda e:events.append({"at":round(time.monotonic()-started,1),"kind":"pageerror","text":str(e)[:2400]}))
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=45000)
   screens.append(name)
   print("SAVE_SCREEN",name,round(time.monotonic()-started,1),flush=True)
  def send(command):
   page.keyboard.press("t")
   page.wait_for_timeout(1700)
   for i in range(0,len(command),38):
    part=command[i:i+38]
    page.evaluate("""(s) => {
      function info(c) {
        if(/^[A-Za-z]$/.test(c))return ['Key'+c.toUpperCase(),c.toUpperCase().charCodeAt(0),c!==c.toLowerCase()];
        if(/^[0-9]$/.test(c))return ['Digit'+c,c.charCodeAt(0),false];
        const d={' ':['Space',32,false],'/':['Slash',191,false],'~':['Backquote',192,true],
        ':':['Semicolon',186,true],'@':['Digit2',50,true],'-':['Minus',189,false],'_':['Minus',189,true],
        '.':['Period',190,false]};
        return d[c]||['Unidentified',0,false];
      }
      for(const c of s){
        const [code,keyCode,shiftKey]=info(c);
        for(const type of ['keydown','keyup']){
          const ev=new KeyboardEvent(type,{key:c,code,shiftKey,bubbles:true,cancelable:true});
          Object.defineProperty(ev,'which',{value:keyCode});
          Object.defineProperty(ev,'keyCode',{value:keyCode});
          window.dispatchEvent(ev);
        }
      }
    }""",part)
    page.wait_for_timeout(1100)
   page.keyboard.press("Enter")
   page.wait_for_timeout(2500)
   command_log.append(command)
   print("SAVE_COMMAND",command,flush=True)
  url="http://127.0.0.1:%d/%s?perfdebug"%(srv.server_address[1],html.name)
  page.goto(url,wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(26000);snap("01-initial-profile")
  page.mouse.click(638,618);page.wait_for_timeout(3500)
  page.mouse.click(638,572);page.wait_for_timeout(3500);snap("02-title")
  page.mouse.click(638,353);page.wait_for_timeout(2000);snap("03-native-warning")
  page.keyboard.press("Enter");page.wait_for_timeout(18000)
  page.mouse.click(638,282);page.wait_for_timeout(25000);snap("04-create-world")
  page.mouse.click(640,426);page.wait_for_timeout(2000)
  page.mouse.click(404,672);page.wait_for_timeout(6000)
  begun=time.monotonic()
  while time.monotonic()-begun<360:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",t)) and int(m.group(1))>320 for t in beats):break
   page.wait_for_timeout(4000)
  else:raise AssertionError("World failed to complete 320 genuine integrated-server ticks")
  page.mouse.click(640,360);page.wait_for_timeout(1200);snap("05-first-playable-world")
  send("/gamemode creative")
  send("/setblock ~ ~-1 ~ minecraft:diamond_block")
  send("/execute if block ~ ~-1 ~ minecraft:diamond_block run say PLETZEL_SAVE_PROBE")
  snap("06-real-block-before-save")
  before=sum("PLETZEL_SAVE_PROBE" in e["text"] and "CHAT" in e["text"] for e in events)
  if before==0:raise AssertionError("Before save the real server did not confirm probe block")
  page.keyboard.press("Escape");page.wait_for_timeout(2000)
  snap("07-genuine-pause-menu")
  page.mouse.click(625,470);page.wait_for_timeout(19000)
  snap("08-return-to-saved-world-list")
  # On the 26.2 Select World screen, select the first newly created world
  # and attempt the native double-click-to-play action.
  page.mouse.dblclick(632,200,delay=180);page.wait_for_timeout(4000)
  snap("09-world-reopen-request")
  began=time.monotonic()
  while time.monotonic()-began<360:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",t)) and int(m.group(1))>360 for t in beats[-20:]):
    # This only indicates ticks in some world. Server block query below
    # independently asserts persisted world identity/contents.
    break
   page.wait_for_timeout(4500)
  page.wait_for_timeout(3500)
  snap("10-rejoined-world-candidate")
  send("/execute if block ~ ~-1 ~ minecraft:diamond_block run say PLETZEL_SAVE_PROBE")
  page.wait_for_timeout(2800);snap("11-persistence-query-result")
  after=sum("PLETZEL_SAVE_PROBE" in e["text"] and "CHAT" in e["text"] for e in events)
  if after<=before:raise AssertionError("Reopened world never confirmed saved block below player")
  print("WORLD_SAVE_RELOAD_PASS",json.dumps({"serverConfirmationsBefore":before,"after":after}),flush=True)
  b.close()
except Exception:
 fault=traceback.format_exc()
 print("WORLD_SAVE_RELOAD_ERROR",fault[-2800:],flush=True)
finally:
 srv.shutdown()
result={"screens":screens,"commands":command_log,"fault":fault,
        "pageErrors":[e for e in events if e["kind"]=="pageerror"],
        "durationSeconds":round(time.monotonic()-started,1),
        "notes":"Game actions use real Minecraft UI. Block query is server-side. A browser-only store inspection is not counted as persistence."}
(out/"results.json").write_text(json.dumps(result,indent=2))
(out/"browser-events.json").write_text(json.dumps(events,indent=2))
if fault:sys.exit(2)
print("PASS: server-confirmed saved block after same-world reopen",flush=True)

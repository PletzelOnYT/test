#!/usr/bin/env python3
"""Real Chrome 26.2 Easy Pick hotbar selection in a genuine creative world.

The nine hotbar items and tenth inventory-only item are created by real vanilla
game commands in an Allow Cheats world, NOT by manipulating JavaScript state,
inventory packets, world memory or schematic data. User right-click is a real
Playwright mouse event consumed by the native Minecraft control mapping.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server,threading,traceback,json,time,re,sys,runpy
root=Path("candidate");html=list(root.rglob("*.html"));assert len(html)==1,html
game=html[0].resolve()
out=Path("easy-pick-real-chrome-evidence");out.mkdir(exist_ok=True)
make=runpy.run_path(str(Path(__file__).with_name("make-easypick-fixture.py")))
fixture=make["create"](out/"fixtures")
materials=make["MATERIALS"]
assert len(materials)==10
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(game.parent),**kw)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
started=time.monotonic();events=[];shots=[];commands=[];fault=None;observations=[]
def elapsed():return round(time.monotonic()-started,1)
def console_text():
 return [x["text"] for x in events]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(
    executable_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("google-chrome-stable"),
    headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist",
          "--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.on("console",lambda m:events.append({"t":elapsed(),"kind":m.type,"text":m.text[:2500]}))
  page.on("pageerror",lambda e:events.append({"t":elapsed(),"kind":"pageerror","text":str(e)[:3000]}))
  def choose(fc):
   fc.set_files(str(fixture.resolve()))
   print("EASYPICK_REAL_CHOOSER",fixture.name,flush=True)
  page.on("filechooser",choose)
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=60000)
   shots.append(name);print("EASYPICK_SHOT",name,elapsed(),flush=True)
  def click(x,y,wait=1200):
   page.mouse.click(x,y)
   page.wait_for_timeout(wait)
  def send(command,delay=1200):
   page.keyboard.press("t")
   page.wait_for_timeout(1500)
   for offset in range(0,len(command),42):
    part=command[offset:offset+42]
    page.evaluate("""s => {
      function info(c){
        if(/^[A-Za-z]$/.test(c))return ['Key'+c.toUpperCase(),c.toUpperCase().charCodeAt(0),c!==c.toLowerCase()];
        if(/^[0-9]$/.test(c))return ['Digit'+c,c.charCodeAt(0),false];
        const d={' ':['Space',32,false],'/':['Slash',191,false],
        '~':['Backquote',192,true],'-':['Minus',189,false],
        '@':['Digit2',50,true],
        ':':['Semicolon',186,true],'.':['Period',190,false]};
        return d[c]||['Unidentified',0,false];
      }
      for(const c of s){
        const [code,which,shiftKey]=info(c);
        const data={key:c,code,shiftKey,bubbles:true,cancelable:true,composed:true};
        for(const type of ['keydown','keyup']){
          const ev=new KeyboardEvent(type,data);
          Object.defineProperty(ev,'which',{value:which});
          Object.defineProperty(ev,'keyCode',{value:which});
          window.dispatchEvent(ev);
        }
      }
    }""",part)
    page.wait_for_timeout(1000)
   page.keyboard.press("Enter")
   page.wait_for_timeout(delay)
   commands.append(command)
   print("EASYPICK_REAL_COMMAND",command,elapsed(),flush=True)
  def hold_use(ms=3200):
   page.mouse.down(button="right");page.wait_for_timeout(ms)
   page.mouse.up(button="right");page.wait_for_timeout(700)
  def open_schematic():
   page.keyboard.press("Escape");page.wait_for_timeout(1200)
   click(478,394)
   click(875,579)
  def close_schematic():
   # Ninth row of the packed native 26.2 Schematica screen.
   click(875,652)
   click(640,672)
   page.mouse.move(640,252);page.wait_for_timeout(400)
   click(640,252,1700)
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(server.server_address[1],game.name),
     wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(26000);snap("01-initial-profile")
  click(638,618,3500);click(638,572,3500)
  click(638,353,2000);page.keyboard.press("Enter");page.wait_for_timeout(18000)
  click(638,282,25000);snap("02-create-new-world")
  click(640,426,1600) # Allow Cheats ON (verified old workflow screenshot)
  snap("03-allow-cheats-enabled")
  click(404,672,5500)
  began=time.monotonic()
  while time.monotonic()-began<360:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",beat)) and int(m.group(1))>320 for beat in beats):break
   page.wait_for_timeout(3500)
  else:raise AssertionError("Singleplayer never completed 320 authoritative ticks")
  click(640,360,1200);snap("04-real-world")
  send("/gamemode creative")
  send("/fill ~-2 ~-1 ~-2 ~13 ~-1 ~2 minecraft:bedrock")
  send("/fill ~-2 ~ ~-2 ~13 ~3 ~2 minecraft:air")
  for index,name in enumerate(materials[:9]):
   send(f"/item replace entity @p hotbar.{index} with {name} 64")
  # Tenth block is available in MAIN INVENTORY, deliberately not hotbar.
  send(f"/item replace entity @p inventory.0 with {materials[9]} 64")
  send("/tp @p ~ ~ ~ 0 90")
  snap("05-nine-hotbar-items-ready")

  open_schematic()
  snap("06-easy-pick-default-off")
  click(410,183,8500)
  if not any("[PletzelSchematicImport] LOADED "+fixture.name in s for s in console_text()):
   raise AssertionError("Mixed ten-block native schematic import did not finish")
  click(868,394)
  snap("07-schematic-loaded-default-off")
  close_schematic()
  page.keyboard.press("9");page.wait_for_timeout(700)
  before=len([s for s in console_text() if "[PletzelEasyPick] SELECT " in s])
  hold_use()
  after=len([s for s in console_text() if "[PletzelEasyPick] SELECT " in s])
  assert after==before,("Easy Pick OFF unexpectedly selected a hotbar slot",before,after)
  snap("08-default-off-no-autoselect")
  # Restore any accidentally placed block from ordinary vanilla right-click.
  send("/fill ~-2 ~ ~-2 ~13 ~2 ~2 minecraft:air")
  send("/tp @p ~ ~ ~ 0 90")

  open_schematic()
  snap("09-easy-pick-before-toggle")
  click(410,652,1800)
  snap("10-easy-pick-toggle-on")
  if not any("[PletzelEasyPick] SETTING enabled=true" in s for s in console_text()):
   raise AssertionError("Native Easy Pick OFF/ON switch was not activated")
  close_schematic()
  page.keyboard.press("9");page.wait_for_timeout(700)
  for slot in range(10):
   t0=len(events)
   hold_use(2700)
   window=events[t0:]
   selected=[e["text"] for e in window if "[PletzelEasyPick] SELECT " in e["text"]]
   missing=[e["text"] for e in window if "[PletzelEasyPick] MISSING " in e["text"]]
   observations.append({"material":materials[slot],"position":slot,
      "slotSelections":selected,"missingMessages":missing})
   print("EASYPICK_REAL_SLOT_TEST",json.dumps(observations[-1])[:2200],flush=True)
   snap("11-real-hotbar-target-%02d"%slot)
   if slot<9 and not any("slot="+str(slot) in line for line in selected):
    raise AssertionError("Did not switch to the actual matching hotbar slot "+str(slot))
   if slot==9 and (selected or not missing):
    raise AssertionError("Inventory-only 10th material wrongly selected or not rejected")
   if slot<9:
    # Move the player, never move the schematic: aim straight at the
    # bedrock floor below the next indexed schematic position.
    send("/tp @p ~1 ~ ~ 0 90",900)
  # Confirm setting remains enabled on reopening the native options screen.
  open_schematic();snap("12-native-setting-retained")
  close_schematic()
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("EASYPICK_REAL_FAILURE",fault[-5000:],flush=True)
finally:
 server.shutdown()
report={"actions":commands,"screenshots":shots,"slotObservations":observations,
        "fault":fault,"pageErrors":[e for e in events if e["kind"]=="pageerror"][-15:],
        "unverified":["Actual multiplayer server placement has not been exercised",
          "Normal placement outcome after blocked player-collision targets not independently measured",
          "Persistent options across full browser restart requires a separate test",
          "No proof of correct slab/stair orientation without actual physical build screenshots"]}
(out/"result.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("EASYPICK_REAL_RESULT",json.dumps({"screens":len(shots),"observations":len(observations),
  "fault":fault})[:3000],flush=True)
if fault or len(observations)!=10:sys.exit(2)
print("REAL_CHROME_EASYPICK_NINE_HOTBAR_PLUS_MISSING_TENTH_ACCEPTANCE_PASSED",flush=True)

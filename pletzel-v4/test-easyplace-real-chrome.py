#!/usr/bin/env python3
"""Real Chrome 26.2 Easy Pick hotbar selection in a genuine creative world.

The nine hotbar items and tenth inventory-only item are created by real vanilla
game commands in an Allow Cheats world, NOT by manipulating JavaScript state,
inventory packets, world memory or schematic data. User right-click is a real
Playwright mouse event consumed by the native Minecraft control mapping.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server,threading,traceback,json,time,re,sys,runpy,base64,gzip
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
   print("EASYPLACE_EASYPICK_REAL_CHOOSER",fixture.name,flush=True)
  page.on("filechooser",choose)
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=60000)
   shots.append(name);print("EASYPLACE_SHOT",name,elapsed(),flush=True)
  def stored_easy_pick():
   # The 26.2 EagRuntime profile is saved as GZIP/Base64 under the
   # client namespace + ".g". Read the real browser storage, not a mock.
   entries=page.evaluate("""() => Array.from({length:localStorage.length},(_,i)=>{
     const key=localStorage.key(i);
     return {key,body:localStorage.getItem(key)};
   }).filter(x=>x.key.endsWith('.g'))""")
   for item in entries:
    try:
     contents=gzip.decompress(base64.b64decode(item["body"])).decode("utf8")
    except Exception:
     continue
    for line in contents.splitlines():
     if line.startswith("pletzelEasyPick:"):return line.strip()
   return None
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
   print("EASYPLACE_EASYPICK_REAL_COMMAND",command,elapsed(),flush=True)
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
  page.keyboard.press("e");page.wait_for_timeout(2500)
  snap("05a-inventory-before-selection")
  page.keyboard.press("Escape");page.wait_for_timeout(1000)

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
  click(410,652,1400) # Main Litematica -> Building / Easy Place
  snap("10-building-settings-open")
  click(410,180,1500) # Easy Place ON, default Hold
  snap("10-easy-place-on")
  click(410,255,1500) # Easy Pick ON
  snap("10-easy-pick-on")
  if not any("[PletzelBuildSettings] Easy Place=true" in s for s in console_text()):
   raise AssertionError("Native Easy Place OFF/ON switch was not activated")
  if not any("[PletzelBuildSettings] Easy Pick=true" in s for s in console_text()):
   raise AssertionError("Native Easy Pick OFF/ON switch was not activated")
  click(875,470,1500) # Building settings -> Litematica
  saved=stored_easy_pick()
  print("EASYPLACE_EASYPICK_REAL_OPTIONS_STORAGE",saved,flush=True)
  assert saved=="pletzelEasyPick:true",("Easy Pick ON was not persisted in native Minecraft options",saved)
  close_schematic()
  page.keyboard.press("9");page.wait_for_timeout(700)
  for slot in range(10):
   t0=len(events)
   hold_use(2700)
   window=events[t0:]
   selected=[e["text"] for e in window if "[PletzelEasyPick] SELECT " in e["text"]]
   easy_place=[e["text"] for e in window if "[PletzelEasyPlace] VANILLA_ATTEMPT" in e["text"]]
   missing=[e["text"] for e in window if "[PletzelEasyPick] MISSING " in e["text"]]
   observations.append({"material":materials[slot],"position":slot,
      "slotSelections":selected,"missingMessages":missing,"nativePlaceAttempts":easy_place})
   print("EASYPLACE_EASYPICK_REAL_SLOT_TEST",json.dumps(observations[-1])[:2200],flush=True)
   snap("11-real-hotbar-target-%02d"%slot)
   if slot<9 and not any("slot="+str(slot) in line for line in selected):
    raise AssertionError("Did not switch to the actual matching hotbar slot "+str(slot))
   if slot==9 and (selected or not missing):
    raise AssertionError("Inventory-only 10th material wrongly selected or not rejected")
   if slot<9:
    # Move the player, never move the schematic: aim straight at the
    # bedrock floor below the next indexed schematic position.
    send("/tp @p ~1 ~ ~ 0 90",900)
  # Independent actual placement proof. We move TWO blocks behind the
  # first hologram cell, look down at the bedrock support face, and send one
  # REAL right mouse hold. Only vanilla placement may create the stone.
  send("/tp @p ~-9 ~ ~-2 0 38")
  send("/setblock ~ ~ ~2 minecraft:air")
  snap("11b-supported-vanilla-placement-target")
  page.keyboard.press("9");page.wait_for_timeout(700)
  placement_at=len(events)
  hold_use(2700)
  snap("11c-after-real-mouse-placement")
  placement_events=[e["text"] for e in events[placement_at:]
                    if "[PletzelEasyPick] SELECT slot=0 " in e["text"]]
  if not placement_events:
   raise AssertionError("Normal gameplay did not select Stone before placement")
  send("/execute if block ~ ~ ~2 minecraft:stone run say PLETZEL_EASY_PICK_REAL_PLACEMENT_OK")
  if not any("PLETZEL_EASY_PICK_REAL_PLACEMENT_OK" in x["text"] and "CHAT" in x["text"] for x in events):
   raise AssertionError("Real server did not confirm vanilla stone placement at the schematic target")
  print("EASYPLACE_EASYPICK_REAL_VANILLA_PLACEMENT_CONFIRMED",flush=True)

  # Compare real hotbar/main-inventory screenshots, not fabricated item data.
  page.keyboard.press("e");page.wait_for_timeout(2200)
  snap("11a-inventory-after-selection")
  page.keyboard.press("Escape");page.wait_for_timeout(850)
  # Confirm setting remains enabled on reopening the native options screen.
  open_schematic();snap("12-native-setting-retained")
  click(410,652,1500)
  snap("12-build-settings-retained")
  click(875,180,1500) # Mode -> Hover Auto-Place
  snap("12-hover-mode-activated")
  if not any("[PletzelBuildSettings] Easy Place=true" in s for s in console_text()):
   raise AssertionError("Easy Place setting missing")
  click(875,470,1200)
  close_schematic()
  # Reopen a previously proven vanilla-legal target, but now DO NOT
  # press right-click. The only new placement must come from Easy Place
  # passing through the ordinary Minecraft startUseItem() method.
  send("/setblock ~ ~ ~2 minecraft:air")
  hover_start=len(events)
  page.wait_for_timeout(12000)
  hover_attempts=[e["text"] for e in events[hover_start:] if
     "[PletzelEasyPlace] VANILLA_ATTEMPT" in e["text"] and "mode=hover" in e["text"]]
  print("EASYPLACE_HOVER_AUTO_ATTEMPTS",len(hover_attempts),flush=True)
  snap("12-hover-auto-mode-no-click")
  if not hover_attempts:
   raise AssertionError("Hover auto-place failed to attempt a real vanilla-supported ghost block")
  send("/execute if block ~ ~ ~2 minecraft:stone run say PLETZEL_HOVER_AUTO_SERVER_CONFIRMED")
  if not any("PLETZEL_HOVER_AUTO_SERVER_CONFIRMED" in x["text"] and "CHAT" in x["text"] for x in events):
   raise AssertionError("Native server never confirmed hover-mode vanilla block placement")

  # Same browser origin, fresh game boot: persisted profile must survive a
  # genuine page reload (not merely toggling a JS variable).
  page.reload(wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(5000)
  reloaded=stored_easy_pick()
  print("EASYPICK_RELOADED_OPTIONS_STORAGE",reloaded,flush=True)
  assert reloaded=="pletzelEasyPick:true",("Saved option lost on actual browser reload",reloaded)
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("EASYPLACE_EASYPICK_REAL_FAILURE",fault[-5000:],flush=True)
finally:
 server.shutdown()
report={"actions":commands,"screenshots":shots,"slotObservations":observations,
        "fault":fault,"pageErrors":[e for e in events if e["kind"]=="pageerror"][-15:],
        "unverified":["Actual multiplayer server placement has not been exercised",
          "Single real stone placement checks server response; other rotated or multi-block placements are not independently verified",
          "LocalStorage persistence on reload is checked; UI restoration after full world reopen not separately checked",
          "No proof of correct slab/stair orientation without actual physical build screenshots",
          "Hover-mode real placement requires verified physical support and is reported separately"]}
(out/"result.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("EASYPLACE_EASYPICK_REAL_RESULT",json.dumps({"screens":len(shots),"observations":len(observations),
  "fault":fault})[:3000],flush=True)
if fault or len(observations)!=10:sys.exit(2)
print("REAL_CHROME_EASYPLACE_EASYPICK_TEN_MATERIAL_TEST_PASSED",flush=True)

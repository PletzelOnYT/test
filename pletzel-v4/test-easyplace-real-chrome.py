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
  def stored_option(name):
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
     if line.startswith(name+":"):return line.strip()
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
  def move_to_player():
   click(410,440,950) # Position/Transform panel
   click(875,280,950) # Move to Player
   click(875,525,950) # Back to main
  def close_schematic():
   click(640,672) # Schematica Done
   click(640,672) # Options Done
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
  snap("06-easy-pick-and-easy-place-separate-off")
  # Inspect the REAL native Minecraft screen at three actual viewport sizes.
  # Full-size is restored before calibrated gameplay button clicks.
  page.set_viewport_size({"width":1024,"height":768})
  page.wait_for_timeout(1600);snap("06-gui-1024x768-no-overlap")
  page.set_viewport_size({"width":800,"height":600})
  page.wait_for_timeout(1600);snap("06-gui-800x600-page-navigation")
  page.set_viewport_size({"width":1280,"height":720})
  page.wait_for_timeout(1600);snap("06-gui-1280x720-restored")
  click(410,183,8500)
  if not any("[PletzelSchematicImport] LOADED "+fixture.name in s for s in console_text()):
   raise AssertionError("Mixed ten-block native schematic import did not finish")
  move_to_player()
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
  snap("09-two-separate-easy-settings-off")
  click(410,360,1400) # Pick ON, Place stays OFF
  snap("10-pick-on-place-off")
  assert any("[PletzelEasyPick] SETTING enabled=true" in x for x in console_text())
  assert stored_option("pletzelEasyPick")=="pletzelEasyPick:true"
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:false"
  close_schematic()
  page.keyboard.press("9");page.wait_for_timeout(700)
  before_pick=len(events)
  hold_use(2500)
  if not any("[PletzelEasyPick] SELECT " in ev["text"] for ev in events[before_pick:]):
   raise AssertionError("Easy Pick ON with Easy Place OFF did not choose a hotbar item")
  print("EASY_PICK_ONLY_REAL_HOTBAR_SELECTION_PASS",flush=True)
  send("/fill ~-2 ~ ~-2 ~13 ~2 ~2 minecraft:air")
  send("/tp @p ~ ~ ~ 0 90")
  open_schematic()
  click(410,360,1300) # Pick OFF
  click(875,360,1300) # Place ON
  snap("10-pick-off-place-on")
  assert stored_option("pletzelEasyPick")=="pletzelEasyPick:false"
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:true"
  close_schematic()
  page.keyboard.press("1");page.wait_for_timeout(700)
  before_place=len(events)
  hold_use(2700)
  placed=[ev["text"] for ev in events[before_place:]]
  if any("[PletzelEasyPick] SELECT " in x for x in placed):
   raise AssertionError("Easy Place without Easy Pick illegally changed hotbar")
  if not any("[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in x for x in placed):
   raise AssertionError("Easy Place alone never reached vanilla right-click")
  print("EASY_PLACE_ONLY_VANILLA_USE_PASS",flush=True)
  send("/fill ~-2 ~ ~-2 ~13 ~2 ~2 minecraft:air")
  send("/tp @p ~ ~ ~ 0 90")
  open_schematic()
  click(410,360,1400) # Both ON independently
  snap("10-pick-on-place-on")
  assert stored_option("pletzelEasyPick")=="pletzelEasyPick:true"
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:true"
  close_schematic()
  page.keyboard.press("9");page.wait_for_timeout(700)
  for slot in range(10):
   t0=len(events)
   hold_use(2700)
   window=events[t0:]
   selected=[e["text"] for e in window if "[PletzelEasyPick] SELECT " in e["text"]]
   easy_place=[e["text"] for e in window if "[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in e["text"]]
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
  # Extract the ACTUAL ghost target logged by Minecraft, not a relative
  # player coordinate that drifts when the player falls during screenshots.
  target_match=re.search(r"target=BlockPos\{x=(-?\d+), y=(-?\d+), z=(-?\d+)\}",placement_events[0])
  if not target_match: raise AssertionError("Native Easy Pick did not expose target BlockPos")
  tx,ty,tz=map(int,target_match.groups())
  send(f"/execute if block {tx} {ty} {tz} minecraft:stone run say PLETZEL_EASY_PICK_REAL_PLACEMENT_OK")
  if not any("PLETZEL_EASY_PICK_REAL_PLACEMENT_OK" in x["text"] and "CHAT" in x["text"] for x in events):
   raise AssertionError("Real server did not confirm vanilla stone placement at the schematic target")
  print("EASYPLACE_EASYPICK_REAL_VANILLA_PLACEMENT_CONFIRMED",flush=True)

  # Compare real hotbar/main-inventory screenshots, not fabricated item data.
  page.keyboard.press("e");page.wait_for_timeout(2200)
  snap("11a-inventory-after-selection")
  page.keyboard.press("Escape");page.wait_for_timeout(850)
  # Confirm setting remains enabled on reopening the native options screen.
  open_schematic();snap("12-independent-buttons-retained")
  click(410,525,1400) # Advanced Settings, separate from both toggles
  snap("12-advanced-settings-layout")
  click(410,183,1500) # attempt to enable disallowed Hover mode
  snap("12-hover-refused")
  assert stored_option("pletzelEasyPlaceHover")=="pletzelEasyPlaceHover:false", (
      "Hover Auto-Place must remain OFF",stored_option("pletzelEasyPlaceHover"))
  click(875,440,1400) # Back to main
  close_schematic()

  # Controlled integrated server: real click, not fabricated placement.
  # Stone, oak planks, glass; one pending attempt per long physical hold.
  for offset,block,slot in ((0,"minecraft:stone",0),
                            (1,"minecraft:oak_planks",1),
                            (2,"minecraft:glass",2)):
   actual_x=tx+offset
   send(f"/setblock {actual_x} {ty} {tz} minecraft:air")
   send(f"/setblock {actual_x} {ty-1} {tz} minecraft:bedrock")
   send(f"/tp @p {actual_x+0.5:.1f} {ty} {tz-1.5:.1f} 0 38")
   page.keyboard.press("9")
   idle_start=len(events)
   page.wait_for_timeout(4200)
   assert not any("[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in
                  e["text"] for e in events[idle_start:]), (
                  "Client placed without a physical user right-click")
   used_at=len(events)
   hold_use(2700)
   texts=[e["text"] for e in events[used_at:]]
   attempts=[x for x in texts if "[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in x]
   accepts=[x for x in texts if "[PletzelEasyPlace] SERVER_CONFIRMED" in x]
   rejects=[x for x in texts if "[PletzelEasyPlace] SERVER_REJECTED_OR_CORRECTED" in x]
   if len(attempts)!=1:raise AssertionError((
       "Physical Hold must generate exactly one placement",block,len(attempts),attempts))
   if len(accepts)!=1 or rejects:raise AssertionError((
       "No authoritative server confirmation or unexpected rejection",
       block,accepts,rejects))
   marker="PLETZEL_HOLD_SERVER_"+block.split(":")[-1].upper()
   send(f"/execute if block {actual_x} {ty} {tz} {block} run say {marker}")
   if not any(marker in t and "CHAT" in t for t in console_text()):
    raise AssertionError("Integrated server did not accept "+block)
   snap("13-hold-server-confirmed-"+block.split(":")[-1])
   print("EASYPLACE_REAL_HOLD_SERVER_CONFIRMED",block,flush=True)

  print("MANUAL_HOLD_STONE_OAK_PLANKS_GLASS_SERVER_ACCEPTED_NO_DUPLICATES",flush=True)

  # Same browser origin, fresh game boot: persisted profile must survive a
  # genuine page reload (not merely toggling a JS variable).
  page.reload(wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(5000)
  reloaded=stored_option("pletzelEasyPick")
  print("EASYPICK_RELOADED_OPTIONS_STORAGE",reloaded,flush=True)
  assert reloaded=="pletzelEasyPick:true",("Easy Pick ON not saved after reload",reloaded)
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:true", "Easy Place ON not saved after reload"
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
          "Hover Auto-Place is disabled; controlled dedicated remote multiplayer remains unverified"]}
(out/"result.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("EASYPLACE_EASYPICK_REAL_RESULT",json.dumps({"screens":len(shots),"observations":len(observations),
  "fault":fault})[:3000],flush=True)
if fault or len(observations)!=10:sys.exit(2)
print("REAL_CHROME_EASYPLACE_EASYPICK_TEN_MATERIAL_TEST_PASSED",flush=True)

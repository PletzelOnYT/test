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
# Extra real Sponge schematic for continuous building: 11 consecutive cells
# using only the three AVAILABLE hotbar materials. Distinct from the
# inventory-only 10th-material Easy Pick regression fixture.
long_blocks=["minecraft:stone","minecraft:oak_planks","minecraft:glass"]*4
long_blocks=long_blocks[:11]
_n=make["t_compound"]
_long_palette=_n("Palette",*(make["t_int"](block,i) for i,block in
                          enumerate(("minecraft:stone","minecraft:oak_planks","minecraft:glass"))))
_long_blob=_n("",make["t_int"]("Version",2),make["t_short"]("Width",11),
             make["t_short"]("Height",1),make["t_short"]("Length",1),
             _long_palette,make["t_byte_array"]("BlockData",[i%3 for i in range(11)]))
continuous_fixture=fixture.parent/"easyplace-continuous-eleven.schem"
continuous_fixture.write_bytes(gzip.compress(_long_blob,mtime=0))
active_fixture=[fixture]
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(game.parent),**kw)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
started=time.monotonic();events=[];shots=[];commands=[];fault=None;observations=[]
def elapsed():return round(time.monotonic()-started,1)
def console_text():
 return [x["text"] for x in events]
def server_proves(page,marker):
 # A real integrated-server /execute if block ... run say marker emits this
 # unforgeable-in-test SERVER THREAD line only when the authoritative block
 # has the requested state. Client chat packets can be delayed or dropped at
 # 2-6 browser FPS; never substitute the predicted client world.
 for _ in range(30):
  if any(marker in e["text"] and "[Server thread" in e["text"] and
         "[Not Secure]" in e["text"] for e in events):
   return True
  page.wait_for_timeout(400)
 print("EASYPLACE_SERVER_MARKER_MISSING",marker,flush=True)
 return False
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
   fc.set_files(str(active_fixture[0].resolve()))
   print("EASYPLACE_EASYPICK_REAL_CHOOSER",active_fixture[0].name,flush=True)
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
   click(875,519)
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
  if not any("[PletzelEasyPlace] SERVER_REJECTED_OR_CORRECTED" in line for line in placed):
   raise AssertionError("Occupied-target placement rejection must be reported from server")
  print("EASY_PLACE_SERVER_REJECTED_OCCUPIED_TARGET_SAFELY",flush=True)
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
   missing=[e["text"] for e in window if "[PletzelEasyPick] MISSING " in e["text"] or "[PletzelEasyPlace] NO_CORRECT_HOTBAR_ITEM" in e["text"]]
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
  # The previous slot-selection checks intentionally aimed straight down
  # while the player occupied the schematic target. The local server correctly
  # rejected that illegal placement, and Easy Place SUSPENDED itself. Prove
  # recovery requires a deliberate user OFF -> ON action before a legal test.
  open_schematic()
  click(875,360,1400) # Explicit Easy Place OFF, clears safety suspension
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:false"
  click(875,360,1400) # Explicit Easy Place ON, legitimate new intent
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:true"
  snap("11-suspension-reset-after-authoritative-rejection")
  close_schematic()

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
  if not server_proves(page,"PLETZEL_EASY_PICK_REAL_PLACEMENT_OK"):
   raise AssertionError("Real server did not confirm vanilla stone placement at the schematic target")
  print("EASYPLACE_EASYPICK_REAL_VANILLA_PLACEMENT_CONFIRMED",flush=True)

  # Controlled integrated server: real click, not fabricated placement.
  # Restore server-confirmed EMPTY space across the ray path. Earlier hotbar
  # trials left a solid Stone block between the eye and intended floor face.
  # Clearing actual world blocks is fixture setup, NOT mocked placement.
  send(f"/fill {tx-2} {ty} {tz-4} {tx+12} {ty+4} {tz+4} minecraft:air")
  send(f"/fill {tx-2} {ty-1} {tz-4} {tx+12} {ty-1} {tz+4} minecraft:bedrock")
  snap("13-server-fixture-ray-path-cleared")
  # Stone, oak planks, glass; one pending attempt per long physical hold.
  for offset,block,slot in ((0,"minecraft:stone",0),
                            (1,"minecraft:oak_planks",1),
                            (2,"minecraft:glass",2)):
   actual_x=tx+offset
   # 38 degrees below horizon from z-1.5 intersects the bedrock TOP face
   # at the target cell, with no intervening solid collision. Only vanilla
   # placement can create the expected block; no world edit supplies success.
   send(f"/tp @p {actual_x+0.5:.1f} {ty} {tz-1.5:.1f} 0 38")
   page.keyboard.press(str(slot+1))
   snap("13-before-legal-hold-"+block.split(":")[-1])
   idle_start=len(events)
   page.wait_for_timeout(4200)
   assert not any("[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in
                  e["text"] for e in events[idle_start:]), (
                  "Client placed without a physical user right-click")
   used_at=len(events)
   hold_use(2700)
   snap("13-after-legal-hold-"+block.split(":")[-1])
   texts=[e["text"] for e in events[used_at:]]
   print("EASYPLACE_HOLD_DIAGNOSTIC",
      block,json.dumps([x for x in texts if
         "PletzelEasyPlace" in x or "PletzelEasyPick" in x][-12:])[:5000],
      flush=True)
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
   if not server_proves(page,marker):
    raise AssertionError("Integrated server did not accept "+block)
   snap("13-hold-server-confirmed-"+block.split(":")[-1])
   print("EASYPLACE_REAL_HOLD_SERVER_CONFIRMED",block,flush=True)

  print("MANUAL_HOLD_STONE_OAK_PLANKS_GLASS_SERVER_ACCEPTED_NO_DUPLICATES",flush=True)



  # Compare real hotbar/main-inventory screenshots, not fabricated item data.
  page.keyboard.press("e");page.wait_for_timeout(2200)
  snap("11a-inventory-after-selection")
  page.keyboard.press("Escape");page.wait_for_timeout(850)
  # Confirm setting remains enabled on reopening the native options screen.
  open_schematic();snap("12-independent-buttons-retained")
  click(410,525,1400) # Advanced Settings, separate from both toggles
  snap("12-advanced-settings-layout")
  click(410,183,1500) # Enable actual Hover Auto-Place mode
  snap("12-hover-enabled")
  assert stored_option("pletzelEasyPlaceHover")=="pletzelEasyPlaceHover:true", (
      "Hover must be selectable and persist",stored_option("pletzelEasyPlaceHover"))
  click(875,440,1400) # Back to main
  assert stored_option("pletzelEasyPlace")=="pletzelEasyPlace:true", (
      "Changing modes must NOT turn Easy Place off")
  close_schematic()

  # HOVER: no physical right click, one native vanilla placement per
  # genuine schematic target. Use server commands only to prepare empty
  # fixture cells and separately QUERY server state. Commands cannot create
  # the expected material and cannot serve as placement evidence.
  for offset,block in ((0,"minecraft:stone"),
                       (1,"minecraft:oak_planks"),(2,"minecraft:glass")):
   x=tx+offset
   send(f"/setblock {x} {ty} {tz} minecraft:air")
   started=len(events)
   send(f"/tp @p {x+0.5:.1f} {ty} {tz-1.5:.1f} 0 38")
   page.wait_for_timeout(7000)
   trace=[e["text"] for e in events[started:]]
   sends=[e for e in trace if "[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in e]
   ack=[e for e in trace if "[PletzelEasyPlace] SERVER_CONFIRMED_AND_RECONCILED" in e]
   if len(sends)!=1 or len(ack)!=1 or "mode=HOVER" not in sends[0]:
    raise AssertionError(("Hover must auto-place exactly one real block WITHOUT right-click",block,sends,ack))
   marker="PLETZEL_HOVER_SERVER_"+str(offset)
   send(f"/execute if block {x} {ty} {tz} {block} run say {marker}")
   if not server_proves(page,marker):
    raise AssertionError("Hover block not confirmed by integrated server "+block)
   snap("13-hover-authoritative-"+block.split(":")[-1])
  print("EASYPLACE_HOVER_THREE_SERVER_CONFIRMED_WITHOUT_MOUSE_DOWN",flush=True)

  # HOLD: import the genuine 11-cell schematic (three available block
  # types), and keep ONE physical right-button press active while moving the
  # crosshair over the whole row. Chat commands are never used while held.
  open_schematic()
  click(410,525,1400) # Advanced Settings
  click(410,183,1400) # Change Hover back to Hold
  assert stored_option("pletzelEasyPlaceHover")=="pletzelEasyPlaceHover:false"
  click(875,440,1400) # Return to schematic main panel
  active_fixture[0]=continuous_fixture
  click(410,183,8500)
  if not any("[PletzelSchematicImport] LOADED "+continuous_fixture.name in t for t in console_text()):
   raise AssertionError("Native continuous 11-cell schematic did not import")
  move_to_player()
  snap("13-continuous-eleven-ghosts-imported")
  close_schematic()
  bx,bz=tx+2,tz-2
  # The old test parked the player SIX blocks away and rotated only the
  # camera, never reaching any of the 11 real targets. Prepare a flat real
  # walkable support platform and an unobstructed corridor at the same y.
  # These commands place only AIR/BEDROCK support, NEVER expected materials.
  send(f"/fill {bx-2} {ty} {bz-4} {bx+12} {ty+3} {bz+1} minecraft:air")
  send(f"/fill {bx-2} {ty-1} {bz-4} {bx+12} {ty-1} {bz+1} minecraft:bedrock")
  # Minecraft yaw 0 faces +Z; holding A physically strafes +X down this
  # eleven-cell row. Eye height +1.62 and pitch 25 reaches z=bz at y=ty.
  # A stationary player could NEVER reach all 11 cells (4.5-block reach).
  send(f"/tp @p {bx-0.5:.1f} {ty} {bz-2.5:.1f} 0 25")
  page.mouse.move(640,360);page.wait_for_timeout(1600)
  before_continuous=len(events)
  page.mouse.down(button="right")
  continuous_down_events=1
  try:
   # One REAL physical mouse-down throughout. Move the PLAYER/crosshair
   # relative to the world using ordinary Minecraft A key input; do NOT
   # teleport, open chat, forge input packets or call mouse.down again.
   page.wait_for_timeout(1600)
   for stride in range(26):
    page.keyboard.down("a")
    page.wait_for_timeout(100)
    page.keyboard.up("a")
    page.wait_for_timeout(650) # allow vanilla server ACK at 2-6 Chrome FPS
    if stride%5==0:snap("13-continuous-hold-strafe-"+str(stride))
  finally:
   page.keyboard.up("a")
   page.mouse.up(button="right")
  page.wait_for_timeout(4000)
  continuous_logs=[e["text"] for e in events[before_continuous:]]
  continuous_attempts=[t for t in continuous_logs if
      "[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in t and
      "mode=CONTINUOUS_HOLD" in t]
  continuous_confirmations=[t for t in continuous_logs if
      "[PletzelEasyPlace] SERVER_CONFIRMED_AND_RECONCILED" in t]
  print("EASYPLACE_CONTINUOUS_ONE_MOUSE_DOWN_DIAGNOSTIC",
        json.dumps({"downs":continuous_down_events,"attempts":len(continuous_attempts),
                    "confirmed":len(continuous_confirmations),
                    "logs":[t for t in continuous_logs if "PletzelEasyPlace" in t][-25:]})[:7000],
        flush=True)
  assert continuous_down_events==1
  if len(continuous_attempts)<10 or len(continuous_confirmations)<10:
   raise AssertionError("A SINGLE held right-click must build at least TEN real schematic blocks")
  verified_continuous=[]
  for offset in range(11):
   block=("minecraft:stone","minecraft:oak_planks","minecraft:glass")[offset%3]
   marker="PLETZEL_CONTINUOUS_SERVER_"+str(offset)
   send(f"/execute if block {bx+offset} {ty} {bz} {block} run say {marker}")
   if server_proves(page,marker):
    verified_continuous.append(offset)
  if len(verified_continuous)<10:
   raise AssertionError(("Under ten server-authoritative continuous Hold blocks",verified_continuous))
  snap("13-continuous-hold-ten-plus-server-accepted")
  print("EASYPLACE_CONTINUOUS_HOLD_TEN_OR_MORE_REAL_BLOCKS_ONE_PRESS",verified_continuous,flush=True)

  # Separate strict schematic boundary check: a NORMAL bedrock support,
  # but no ghost at the aimed destination. Easy Place ON must consume the
  # held physical use rather than send a single outside-schematic packet.
  send(f"/tp @p {bx+5.5:.1f} {ty} {bz-5.5:.1f} 0 90")
  off_at=len(events)
  hold_use(1900)
  off_attempts=[e["text"] for e in events[off_at:]
      if "[PletzelEasyPlace] PENDING_VANILLA_RIGHT_CLICK" in e["text"]]
  if off_attempts:raise AssertionError(("Off-schematic physical Hold sent placement",off_attempts))
  off_marker="PLETZEL_OFF_SCHEMATIC_AIR_VERIFIED"
  send(f"/execute if block {bx+5} {ty} {bz-5} minecraft:air run say {off_marker}")
  if not server_proves(page,off_marker):
   raise AssertionError("Unintended solid block outside schematic")
  print("EASYPLACE_HOLD_OFF_SCHEMATIC_NO_PLACEMENT",flush=True)

  # Save, quit, and reopen the EXACT integrated-server world. Verify the
  # three placed materials from new server-side block queries after restart.
  # This proves actual persistence rather than only a client-rendered block.
  page.keyboard.press("Escape");page.wait_for_timeout(2000)
  snap("14-before-save-and-quit")
  page.mouse.click(625,470);page.wait_for_timeout(19000)
  snap("15-after-save-and-quit")
  page.mouse.click(638,353);page.wait_for_timeout(3500)
  page.keyboard.press("Enter");page.wait_for_timeout(7500)
  before_reopen=len(events)
  page.mouse.click(632,200);page.wait_for_timeout(850)
  page.mouse.click(402,595);page.wait_for_timeout(5500)
  t0=time.monotonic()
  reopened=False
  while time.monotonic()-t0<360:
   stream=[e["text"] for e in events[before_reopen:]]
   started=any("Worker received StartServer for world" in x for x in stream)
   heartbeats=[x for x in stream if "[EagPerfHeartbeat]" in x]
   if started and any((m:=re.search(r"lastTick=(\d+)",t)) and int(m.group(1))>320 for t in heartbeats[-30:]):
    reopened=True
    break
   page.wait_for_timeout(4000)
  if not reopened:raise AssertionError("Save/reload: integrated server never reopened to 320 real ticks")
  page.wait_for_timeout(3000)
  snap("16-world-reopened")
  for offset,block in ((0,"minecraft:stone"),(1,"minecraft:oak_planks"),
                       (2,"minecraft:glass")):
   marker="PLETZEL_SAVED_"+block.split(":")[-1].upper()
   send(f"/execute if block {tx+offset} {ty} {tz} {block} run say {marker}")
   if not server_proves(page,marker):
    raise AssertionError("Previously placed block did NOT persist after reload: "+block)
  # Every one of the ten-plus continuous Hold placements must persist in the
  # actual reopened integrated-server world (not a local predicted ghost).
  for offset in verified_continuous:
   block=("minecraft:stone","minecraft:oak_planks","minecraft:glass")[offset%3]
   marker="PLETZEL_REJOINED_CONTINUOUS_"+str(offset)
   send(f"/execute if block {bx+offset} {ty} {bz} {block} run say {marker}")
   if not server_proves(page,marker):
    raise AssertionError("Continuous Hold accepted block lost after world reopen "+str(offset))
  snap("17-all-three-plus-ten-continuous-persisted")
  print("EASYPLACE_HOLD_SAVE_RELOAD_THREE_AND_TEN_PLUS_BLOCKS_SERVER_CONFIRMED",flush=True)

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
          "Hover Auto-Place requires dedicated Chrome confirmation; controlled remote multiplayer remains unverified"]}
(out/"result.json").write_text(json.dumps(report,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("EASYPLACE_EASYPICK_REAL_RESULT",json.dumps({"screens":len(shots),"observations":len(observations),
  "fault":fault})[:3000],flush=True)
if fault or len(observations)!=10:sys.exit(2)
print("REAL_CHROME_EASYPLACE_EASYPICK_TEN_MATERIAL_TEST_PASSED",flush=True)

#!/usr/bin/env python3
"""Real native Map + Shulker Box tooltips browser acceptance probe.
Never fabricates map data or draws overlays. Real maps are created by player USE.
Screenshots and commands alone are NOT sufficient evidence of correct previews.
"""
from pathlib import Path
import http.server, threading, time, json, traceback, re, os, base64
from playwright.sync_api import sync_playwright

html_files=list(Path("candidate").rglob("*.html"))
assert len(html_files)==1, html_files
html=html_files[0].resolve()
out=Path("map-shulker-real-inventory-evidence")
out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(html.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic(); events=[]; shots=[]; cmds=[]; fault=None
try:
 with sync_playwright() as p:
  # A persistent Chrome profile is required to test a *real browser
  # process restart*, rather than the much weaker page.reload() case.
  profile_dir=str(Path("mapart-chrome-persistent-profile").resolve())
  chrome_args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
      "--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
      "--use-gl=desktop","--disable-features=Vulkan"]
  chrome_path=__import__("shutil").which("google-chrome") or __import__("shutil").which("google-chrome-stable")
  browser=p.chromium.launch_persistent_context(user_data_dir=profile_dir,
      executable_path=chrome_path,headless=False,
      viewport={"width":1280,"height":720},args=chrome_args)
  page=browser.pages[0] if browser.pages else browser.new_page()
  # No auto-create: navigate world creation UI and enable real server commands.
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:1800]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:1800]}))
  def snap(name):
   page.screenshot(path=str(out/(name+".png")),timeout=45000)
   shots.append({"name":name,"elapsed":round(time.monotonic()-start,1)})
   print("SCREENSHOT",name,shots[-1]["elapsed"],flush=True)
  def cached_pixels():
   # Observe the real IndexedDB object store, NOT an emulated map or
   # stale localStorage entry. Both packed data and keys must persist.
   entries=page.evaluate("""async () => {
     const db=await new Promise((resolve,reject)=>{
       const req=indexedDB.open('pletzel-map-art-v1',1);
       req.onsuccess=()=>resolve(req.result);
       req.onerror=()=>reject(req.error);
     });
     return await new Promise((resolve,reject)=>{
       const tx=db.transaction('pixels','readonly');
       const store=tx.objectStore('pixels');
       const keys=store.getAllKeys(),values=store.getAll();
       tx.oncomplete=()=>{
         const data=(keys.result||[]).map((key,i)=>({key,value:values.result[i]}));
         db.close();resolve(data);
       };
       tx.onerror=()=>reject(tx.error);
     });
   }""")
   good={}
   for item in entries:
    try: data=base64.b64decode(item["value"])
    except Exception: continue
    if len(data)==16392 and data.startswith(b"PMART26\x01"):
     good[item["key"]]=data.hex()
   return good

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
  page.wait_for_timeout(26000);snap("01-first-boot-profile")
  page.mouse.click(638,618);page.wait_for_timeout(3500);snap("02-username-check")
  page.mouse.click(638,572);page.wait_for_timeout(3500);snap("03-main-menu")
  page.mouse.click(638,353);page.wait_for_timeout(1800);snap("04-native-warning")
  # This is the genuine Minecraft native Continue button, keyboard focused.
  page.keyboard.press("Enter");page.wait_for_timeout(18000);snap("05-world-chooser")
  # New World choice only after Continue. It never bypasses the warning.
  page.mouse.click(638,282);page.wait_for_timeout(25000);snap("06-create-world-menu")
  # Source-calibrated vanilla Create World "Allow Cheats" option.
  page.mouse.click(640,426);page.wait_for_timeout(1600);snap("07-allow-cheats-enabled")
  page.mouse.click(404,672);page.wait_for_timeout(5500);snap("08-world-creation-started")
  began=time.monotonic()
  reached_world=False
  while time.monotonic()-began<330:
   beats=[e["text"] for e in events if "[EagPerfHeartbeat]" in e["text"]]
   if any((m:=re.search(r"lastTick=(\d+)",beat)) and int(m.group(1))>320 for beat in beats):
    reached_world=True
    break
   page.wait_for_timeout(4500)
  snap("09-world-checkpoint")
  if not reached_world:
   raise RuntimeError("Known broken singleplayer never reached 320 completed server ticks; cannot test two genuine maps")
  page.mouse.click(640,360);page.wait_for_timeout(1500)
  send("/time query gametime")
  snap("10-genuine-commands-enabled")
  send("/give @p minecraft:map 1")
  page.keyboard.press("1");page.wait_for_timeout(1500)
  page.mouse.click(640,360,button="right")
  page.wait_for_timeout(18000);snap("11-first-real-map-in-hand")
  # Normal maps automatically preview and persist without manual marking.
  # Second map MUST be used in a different geographic area. We neither patch
  # map pixel data nor manufacture client textures.
  send("/tp @p ~1024 ~ ~1024")
  page.wait_for_timeout(65000);snap("12-moved-to-second-area")
  send("/give @p minecraft:map 1")
  page.keyboard.press("2");page.wait_for_timeout(1500)
  page.mouse.click(640,360,button="right")
  page.wait_for_timeout(18000);snap("13-second-real-map-in-hand")
  # Normal map #2 also auto-persists its authentic server pixels.
  saved_before=cached_pixels()
  print("REAL_MAP_ART_PERSISTED_BEFORE_RESTART",len(saved_before),flush=True)
  if len(saved_before)<2:
   raise AssertionError("Normal filled-map pixel bytes missing from real browser IndexedDB")
  page.keyboard.press("e");page.wait_for_timeout(5500);snap("14-real-inventory")
  # At default 1280x720 GUI scale ~3, first two hotbar slots in the survival inventory.
  page.mouse.move(410,555);page.wait_for_timeout(6000);snap("15-first-filled-map-tooltip")
  page.mouse.move(464,555);page.wait_for_timeout(6000);snap("16-second-filled-map-tooltip")
  # Revisit both actual server-created map items; never simulate map pixels.
  # Each screenshot is taken after a real hover in the native 26.2 inventory.
  for cycle in range(6):
   page.mouse.move(410,555);page.wait_for_timeout(1500);snap("map-%d-id0"%cycle)
   page.wait_for_timeout(550);snap("map-%d-id0-held"%cycle)
   page.mouse.move(464,555);page.wait_for_timeout(1500);snap("map-%d-id1"%cycle)
   page.wait_for_timeout(550);snap("map-%d-id1-held"%cycle)
  page.keyboard.press("Escape");page.wait_for_timeout(1200)
  send("/give @p minecraft:shulker_box 1")
  send('/give @p red_shulker_box[container=[{slot:0,item:{id:"diamond",count:42}},{slot:8,item:{id:"golden_apple",count:5}}]] 1')
  page.keyboard.press("e");page.wait_for_timeout(5000);snap("17-shulker-items-in-inventory")
  page.mouse.move(532,562);page.wait_for_timeout(4600);snap("18-empty-shulker-27-slots")
  page.mouse.move(586,562);page.wait_for_timeout(4600);snap("19-red-populated-shulker-27-slots")
  page.mouse.move(532,562);page.wait_for_timeout(2000);snap("20-switch-back-to-empty-shulker")
  page.keyboard.press("Escape");page.wait_for_timeout(3500);snap("21-inventory-closed")
  page.set_viewport_size({"width":1024,"height":768});page.wait_for_timeout(3500)
  page.keyboard.press("e");page.wait_for_timeout(4000);snap("22-resized-inventory")
  page.keyboard.press("Escape");page.wait_for_timeout(900)
  # Save the actual integrated server world before reloading the page. Select
  # empty hotbar slot 9 so the rejoin does NOT immediately activate maps.
  page.keyboard.press("9");page.wait_for_timeout(700)
  page.keyboard.press("Escape");page.wait_for_timeout(1900)
  page.mouse.click(625,470);page.wait_for_timeout(19000)
  snap("23-save-and-quit-before-restart")
  browser.close() # Browser process and all game workers are fully gone.
  print("REAL_MAP_ART_BROWSER_PROCESS_CLOSED",flush=True)
  browser=p.chromium.launch_persistent_context(user_data_dir=profile_dir,
      executable_path=chrome_path,headless=False,
      viewport={"width":1280,"height":720},args=chrome_args)
  page=browser.pages[0] if browser.pages else browser.new_page()
  page.on("console",lambda m:events.append({"t":round(time.monotonic()-start,1),"kind":m.type,"text":m.text[:1800]}))
  page.on("pageerror",lambda e:events.append({"t":round(time.monotonic()-start,1),"kind":"pageerror","text":str(e)[:1800]}))
  page.goto("http://127.0.0.1:%d/%s?perfdebug"%(srv.server_address[1],html.name),
      wait_until="domcontentloaded",timeout=150000)
  page.wait_for_timeout(26000)
  saved_after=cached_pixels()
  print("REAL_MAP_ART_PERSISTED_AFTER_RELOAD",len(saved_after),flush=True)
  if saved_before!=saved_after:
   raise AssertionError("Map art bytes changed after actual Chromium process close and fresh launch")
  snap("24-reloaded-main-menu")
  # Rejoin the genuine saved world, WITHOUT holding or opening either map.
  page.mouse.click(638,353);page.wait_for_timeout(3500)
  page.keyboard.press("Enter");page.wait_for_timeout(7500)
  snap("25-reloaded-world-selection")
  previous_count=len(events)
  page.mouse.click(632,200);page.wait_for_timeout(850)
  page.mouse.click(402,595);page.wait_for_timeout(5500)
  begun=time.monotonic()
  rejoined=False
  while time.monotonic()-begun<360:
   newevents=[e["text"] for e in events[previous_count:]]
   started=any("Worker received StartServer for world" in t for t in newevents)
   freshbeats=[t for t in newevents if "[EagPerfHeartbeat]" in t]
   if started and any((m:=re.search(r"lastTick=(\d+)",t)) and int(m.group(1))>320 for t in freshbeats[-30:]):
    rejoined=True;break
   page.wait_for_timeout(4500)
  if not rejoined:
   raise AssertionError("Saved world did not genuinely reopen after browser reload")
  page.keyboard.press("e");page.wait_for_timeout(6000)
  page.mouse.move(410,555);page.wait_for_timeout(6000)
  snap("26-map0-cached-tooltip-after-rejoin")
  page.mouse.move(464,555);page.wait_for_timeout(6000)
  snap("27-map1-cached-tooltip-after-rejoin")
  from PIL import Image
  def colors_after(name,box):
   im=Image.open(out/(name+".png")).convert("RGB").crop(box)
   return len({im.getpixel((x,y)) for x in range(8,im.width-8,5)
                                  for y in range(8,im.height-8,5)})
  reloaded_colors=[
   colors_after("26-map0-cached-tooltip-after-rejoin",(450,500,628,675)),
   colors_after("27-map1-cached-tooltip-after-rejoin",(504,500,682,675))]
  print("REAL_MAP_ART_REJOIN_COLOR_COUNTS",reloaded_colors,flush=True)
  if any(count<10 for count in reloaded_colors):
   raise AssertionError("Real cached artwork did not reappear on hover after restarting same world")
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("ERROR",fault[-4000:],flush=True)
finally:
 srv.shutdown()
beats=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
from PIL import Image, ImageChops
differences=None
if (out/"15-first-filled-map-tooltip.png").exists() and (out/"16-second-filled-map-tooltip.png").exists():
 first=Image.open(out/"15-first-filled-map-tooltip.png").convert("RGB")
 second=Image.open(out/"16-second-filled-map-tooltip.png").convert("RGB")
 # A broad tooltip region is intentionally saved for human pixel verification.
 # Different pixels ALONE are not proof of two real map data sets.
 differences=sum(1 for p in ImageChops.difference(first.crop((480,300,1100,670)),
                  second.crop((480,300,1100,670))).getdata() if p!=(0,0,0))
# Real colored map art from the previous user's successful 1280x720 layout:
# these two crop windows lie within the actual MapRenderer pixel texture.
# Different map artwork is not guaranteed: terrains can overlap.\n# Real baseline terrain-map crops contained 18-19 distinct sampled colors.\n# Requiring 24 would falsely fail genuine map pixels; threshold 10 only\n# distinguishes these known terrain fixtures from a blank tooltip.
def image_color_count(path,box):
 im=Image.open(path).convert("RGB").crop(box)
 sampled=[im.getpixel((x,y)) for y in range(8,im.height-8,5)
                                 for x in range(8,im.width-8,5)]
 return len(set(sampled))
hover_art=[]
for cycle in range(6):
 for kind,region in (("id0",(450,500,628,675)),("id1",(504,500,682,675))):
  for held in ("", "-held"):
   name=f"map-{cycle}-{kind}{held}"
   p=out/(name+".png")
   if p.exists():
    hover_art.append({"name":name,"colorCount":image_color_count(p,region)})
print("MAP_HOVER_REAL_ART_SAMPLES",json.dumps(hover_art),flush=True)
if len(hover_art)!=24 or any(d["colorCount"]<10 for d in hover_art):
 fault=(fault or "")+" real repeated-map-hover artwork missing or insufficiently diverse"
result={"screenshots":shots,"vanillaCommandsSubmitted":cmds,"realMapHoverSamples":hover_art,
 "persistedPixelEntryCount":len(saved_before) if "saved_before" in locals() else None,
 "heartbeatCount":len(beats),"tooltipPixelDifferenceCount":differences,
 "fatal":fault,"pageErrors":[e for e in events if e["kind"]=="pageerror"][-30:],
 "manual_verification_required":[
  "Check that first and second player-held items are actual filled maps",
  "Check both native tooltip frames are exactly 66 GUI pixels",
  "Check two distinct map IDs and distinct real terrain map colors",
  "Check no synthetic terrain or browser overlay was used",
  "Check map updates after receiving a later vanilla map packet",
  "Multiplayer server-scoped map-art retrieval requires separate actual-server testing",
  "Check multiplayer map data and map item in a chest independently",
  "Check real empty shulker has exactly 27 empty native slots",
  "Check red shulker slot 0 diamond 42 and slot 8 golden apples 5",
  "Check switching back to empty shulker clears populated icons",
  "Check original shulker item data never changes and no server-side mod is needed"
 ]}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"all-events.json").write_text(json.dumps(events,indent=2))
print("REAL_MAP_GAMEPLAY_RESULT",json.dumps({"screens":len(shots),"commands":len(cmds),
 "heartbeatCount":len(beats),"tooltipPixelDiff":differences,"fault":fault})[:3000],flush=True)
if fault or len(shots)<22:
 raise SystemExit(2)
print("BROWSER EXECUTION DONE; human preview content checks still required.",flush=True)

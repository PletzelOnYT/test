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
  page.mouse.click(638,257);page.wait_for_timeout(600)
  page.mouse.click(638,257);page.wait_for_timeout(1100);snap("06-creative-chosen")
  page.mouse.click(638,426);page.wait_for_timeout(1100);snap("07-cheats-toggle")
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
  # Focus the real Minecraft canvas and exercise server-issued inventory data.
  page.mouse.click(635,350);page.wait_for_timeout(900)
  send("/time set day")
  send("/difficulty peaceful")
  send("/gamerule drowningDamage false")
  send("/gamerule fallDamage false")
  send("/give @p minecraft:shulker_box 1")
  send("/give @p minecraft:red_shulker_box 1")
  send("/give @p minecraft:blue_shulker_box 1")
  # The following containers use the native 26.2 component codec; no test
  # writes game WASM, inventory memory or creates false in-browser icons.
  send('/give @p minecraft:green_shulker_box[minecraft:container=[{slot:0,item:"minecraft:diamond"},{slot:8,item:"minecraft:golden_apple"}]] 1')
  send('/give @p minecraft:yellow_shulker_box[minecraft:container=[{slot:0,item:{id:"minecraft:diamond",count:42}},{slot:17,item:{id:"minecraft:iron_ingot",count:16}}]] 1')
  # 27 distinct occupied server item slots, generated with the exact
  # Slot CODEC shape from the current Minecraft 26.2 source.
  filled = ",".join("{slot:"+str(i)+',item:"minecraft:cobblestone"}' for i in range(27))
  send("/give @p minecraft:purple_shulker_box[minecraft:container=["+filled+"]] 1",delay=4)
  snap("10-genuine-server-command-feedback")
  # Preserve survival-style inventory layout for reliable slot coords while
  # remaining safe from drowning/fall damage. Server commands are real.
  send("/gamemode survival")
  page.wait_for_timeout(2000)
  page.keyboard.press("e");page.wait_for_timeout(4500);snap("11-inventory-shulker-items")
  # Hotbar at 1280x720, gui scale 3: slot centers ~410+54*N at y=555.
  # Mouse pointer is moved over REAL inventory slots.
  hover=[("12-undyed-empty",410,556),
         ("13-red-empty",464,556),
         ("14-blue-empty",518,556),
         ("15-green-partial",572,556),
         ("16-yellow-counts",626,556),
         ("17-purple-full",680,556)]
  for name,x,y in hover:
   page.mouse.move(x,y);page.wait_for_timeout(4000);snap(name)
  page.mouse.move(572,556);page.wait_for_timeout(1700)
  # ORIGINAL MOD: hold CTRL to lock the item tooltip to the shulker source
  # slot while moving into its preview. Never click, drag, or edit items.
  page.keyboard.down("Control")
  page.wait_for_timeout(900)
  page.mouse.move(905,590)
  page.wait_for_timeout(2000);snap("18-ctrl-lock-hover-inner-slot")
  page.keyboard.up("Control")
  page.wait_for_timeout(1300);snap("18b-ctrl-unlock-cleanup")
  page.keyboard.press("Escape");page.wait_for_timeout(1800)
  page.set_viewport_size({"width":1024,"height":768})
  page.keyboard.press("e");page.wait_for_timeout(3500);snap("19-resized-inventory")
  page.mouse.move(380,574);page.wait_for_timeout(2800);snap("20-resized-blank-shulker")
  page.keyboard.press("Escape");page.wait_for_timeout(1200)
  browser.close()
except Exception:
 fault=traceback.format_exc()
 print("ERROR",fault[-4000:],flush=True)
finally:
 srv.shutdown()
beats=[e for e in events if "[EagPerfHeartbeat]" in e["text"]]
from PIL import Image,ImageChops
screens=[f for f in out.glob("*.png")]
results={"screenshots":shots,"commands":cmds,"heartbeatCount":len(beats),
 "error":fault,"pageErrors":[e for e in events if e["kind"]=="pageerror"],
 "manualAcceptanceRequirements":[
 "Inspect screenshot 06: Game Mode CREATIVE, not Survival/Hardcore",
 "Inspect screenshot 11: SIX real vanilla shulker items present",
 "Inspect 12-14: original mod-tinted empty shulker 9x3 GUI",
 "Inspect 15-16: real contents icons and stack counts from server component",
 "Inspect 17: all 27 occupied slots actually visible",
 "Inspect 18: Ctrl-lock retains source shulker tooltip while pointer enters actual preview slot",
 "Inspect 18b: Ctrl release cleans up locked preview without changing inventory",
 "Inspect 19-20: GUI scale changes without clipping",
 "Confirm that no death screen or command parsing errors appear",
 "Compare screenshots against the actual official mod Full Preview reference and 32x32 source asset"
 ]}
(out/"results.json").write_text(json.dumps(results,indent=2))
(out/"console.json").write_text(json.dumps(events,indent=2))
print("SHULKER_ORIGINAL_PARITY_GAMEPLAY",json.dumps({
 "screenshots":len(shots),"commands":len(cmds),"error":fault,
 "pageErrors":len(results["pageErrors"])})[:2500],flush=True)
if fault or results["pageErrors"] or len(shots)<20:
 raise SystemExit(2)
print("BROWSER PIXEL CAPTURE ONLY: no automatic claim of exact visual/item parity",flush=True)

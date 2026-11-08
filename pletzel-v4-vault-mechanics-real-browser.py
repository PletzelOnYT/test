#!/usr/bin/env python3
"""Runtime Vault block entity activation, trial key, loot validation of EXACT precompiled HTML.
UI commands/scoreboard are observed via screenshots; successful script exit is NOT proof of AI.
Screenshots plus server-authoritative Vault state and NBT must be reviewed.
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
  page.mouse.click(640,354);page.wait_for_timeout(1500)
  send("/gamemode creative",2)
  send("/time set day",1)
  send("/scoreboard objectives add vaultCheck dummy")
  send("/fill ~-4 160 ~-4 ~4 160 ~4 minecraft:stone",2)
  # Local-only move to an already FULL chunk; don't conflate the remote
  # asynchronous teleport regression with Vault mechanics.
  send("/tp @p ~ 161 ~ 0 25",2)
  send("/setblock ~ ~ ~2 minecraft:vault[facing=north]",2)
  snap("01-vault-created-close-to-player")
  page.wait_for_timeout(35000)
  send("/execute if block ~ ~ ~2 minecraft:vault[state=active] run say PLETZEL_VAULT_ACTIVATED",1)
  snap("02-vault-state-after-35s")
  send("/data get block ~ ~ ~2",1)
  send("/item replace entity @p weapon.mainhand with minecraft:trial_key",1)
  snap("03-trial-key-in-hand")
  for n in range(4):
   page.mouse.click(640,353,button="right")
   page.wait_for_timeout(1400)
  snap("04-real-rightclick-vault")
  send("/execute if block ~ ~ ~2 minecraft:vault[state=unlocking] run say PLETZEL_VAULT_UNLOCKING",1)
  send("/execute if block ~ ~ ~2 minecraft:vault[state=ejecting] run say PLETZEL_VAULT_EJECTING",1)
  send("/data get block ~ ~ ~2",1)
  snap("05-vault-server-state-after-key")
  page.wait_for_timeout(15000)
  send("/data get block ~ ~ ~2",1)
  send("/execute if entity @e[type=minecraft:item,distance=..8] run say PLETZEL_VAULT_DROPPED_ITEM",1)
  snap("06-vault-loot-after-15s")
  page.wait_for_timeout(15000)
  send("/data get block ~ ~ ~2",1)
  snap("07-vault-post-ejection")
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
 "disclaimer":"Player mouse clicks were sent after a server-positioned target; screenshots and server-health scoreboard require visual confirmation. A /damage command occurs only afterwards as a separate control. Clicks alone are NOT proof of attack or knockback."}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"all-events.json").write_text(json.dumps(events,indent=2))
print("RESULT",json.dumps({"screens":len(shots),"commands":len(cmds),"chickenReports":len(chicken),"heartbeatCount":len(beats),"fault":fault})[:3000],flush=True)
logs="\\n".join(e.get("text","") for e in events)
activated="PLETZEL_VAULT_ACTIVATED" in logs
(out/"vault-assertions.json").write_text(json.dumps({"vault_active_evidence":activated,
 "manual_reward_item_and_state_verification_required":True},indent=2))
if fault or len(shots)<8 or not activated:raise SystemExit(2)

#!/usr/bin/env python3
"""Real Chromium screens of built-in Controls/Keybinds with Freecam entry.
No synthetic UI, keybind injection or fake success. Screenshots for human review.
"""
import http.server,threading,time,json,traceback,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
games=list(Path("candidate").rglob("*.html"))
assert len(games)==1,games
game=games[0].resolve()
output=Path("freecam-keybind-real-ui-evidence")
output.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(game.parent),**k)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
errors=[];snaps=[];fatal=None;start=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=__import__('shutil').which('google-chrome') or __import__('shutil').which('google-chrome-stable'),headless=False,args=["--no-sandbox","--disable-dev-shm-usage","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720})
  page.add_init_script("window.__eaglerAutoTest='sp';")
  page.on("pageerror",lambda e:errors.append(str(e)[:1800]))
  def shot(name):
   page.screenshot(path=str(output/(name+".png")),timeout=45000)
   snaps.append(name)
   print("FREECAM_REAL_GUI_SCREENSHOT",name,round(time.monotonic()-start,1),flush=True)
  def click(x,y,name):
   page.mouse.click(x,y);page.wait_for_timeout(3000);shot(name)
  page.goto("http://127.0.0.1:%d/%s"%(srv.server_address[1],game.name),wait_until="domcontentloaded",timeout=140000)
  page.wait_for_timeout(115000)
  shot("01-world")
  page.keyboard.press("Escape");page.wait_for_timeout(3000);shot("02-paused")
  click(478,394,"03-options-from-pause")
  click(825,363,"04-controls-candidate")
  click(825,100,"05-keybinds-candidate")
  for i in range(8):
   page.mouse.move(650,380);page.mouse.wheel(0,420)
   page.wait_for_timeout(1200)
   shot("06-keybind-scroll-%02d"%i)
  browser.close()
except Exception:
 fatal=traceback.format_exc();print("FREECAM_GUI_ERROR",fatal[-3500:],flush=True)
finally:srv.shutdown()
result={"screens":snaps,"elapsed":time.monotonic()-start,"fatal":fatal,"pageErrors":errors,
"browser_acceptance":"UNVERIFIED: screenshots must show real Freecam keybind entry and gameplay toggle; this scout does not claim a pass"}
(output/"results.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result)[:2000],flush=True)
if fatal or len(snaps)<13:sys.exit(2)

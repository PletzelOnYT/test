#!/usr/bin/env python3
"""Actual unmodified Pletzel V4 creative world state-comparison test.
Captures real block transitions with /setblock in the integrated server; no fake overlay.
Screenshots intentionally require external visual inspection.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import gzip,struct,json,time,threading,http.server,traceback,sys

htmls=list(Path('candidate').rglob('*.html'));assert len(htmls)==1,htmls
source=htmls[0].resolve()
out=Path('root-live-block-evidence');out.mkdir(exist_ok=True)

def classic(name, block, data):
 b=bytearray(b'\x0a\x00\x00')
 def tag(k,typ,val):
  n=k.encode();b.extend(bytes([typ])+struct.pack('>H',len(n))+n+val)
 for n in ('Width','Height','Length'):tag(n,2,struct.pack('>h',1))
 tag('Blocks',7,struct.pack('>i',1)+bytes([block]))
 tag('Data',7,struct.pack('>i',1)+bytes([data]))
 tag('Materials',8,struct.pack('>H',5)+b'Alpha')
 b.append(0)
 path=out/name;path.write_bytes(gzip.compress(b,mtime=0))
 return path.resolve()
fixtures=[classic('target-stone.schematic',1,0),classic('target-oak-log.schematic',17,0)]
selection=[0];file_picks=[];screen=[];events=[];fatal=None
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(source.parent),**kw)
 def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
start=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720})
  page.on('console',lambda m:events.append({'at':round(time.monotonic()-start,2),'kind':m.type,'text':m.text[:1500]}))
  page.on('pageerror',lambda e:events.append({'at':round(time.monotonic()-start,2),'kind':'pageerror','text':str(e)[:1500]}))
  def choose(fc):
   try:fc.set_files(str(fixtures[selection[0]]));file_picks.append(fixtures[selection[0]].name)
   except Exception as e:file_picks.append('FILE ERROR '+str(e))
  page.on('filechooser',choose)
  def snap(label):
   page.screenshot(path=str(out/(label+'.png')),timeout=30000)
   screen.append(label);print('SCREEN',label,flush=True)
  def click(x,y,label,delay=2):
   page.mouse.click(x,y);time.sleep(delay);snap(label)
  def command(text,delay=2):
   page.keyboard.press('t');time.sleep(0.65)
   page.keyboard.type(text,delay=15)
   page.keyboard.press('Enter');time.sleep(delay)
   print('COMMAND',text,flush=True)
  def open_schema(label):
   page.keyboard.press('Escape');time.sleep(1)
   click(478,393,label+'-options',1)
   click(876,578,label+'-schema',1)
  def exit_schema():
   page.mouse.click(876,669);time.sleep(1)
   page.mouse.click(630,671);time.sleep(1)
   page.mouse.click(637,252);time.sleep(2)

  page.goto(f'http://127.0.0.1:{srv.server_address[1]}/{source.name}?perfdebug',wait_until='domcontentloaded',timeout=150000)
  time.sleep(27)
  click(638,618,'01-profile',4)
  click(638,572,'02-menu',5)
  click(638,352,'03-select-singleplayer',34)
  click(638,282,'04-create-world',14)
  snap('05-before-creative')
  # Native Game-mode and cheats cycle controls. One click Survival -> Creative.
  click(640,257,'06-hardcore-intermediate')
  click(640,257,'06-creative-on')
  snap('07-cheats-default-creative')
  click(397,671,'08-create-click',92)
  snap('09-game-loaded')
  # All placements at fixed coordinates high above terrain, on actual server blocks.
  command('/setblock 0 149 0 minecraft:stone')
  command('/setblock 0 149 5 minecraft:stone')
  command('/setblock 0 150 0 minecraft:air')
  command('/tp 0 150 0')
  snap('10-at-target')
  open_schema('11')
  selection[0]=0
  click(408,184,'12-import-stone',6)
  snap('13-stone-loaded')
  exit_schema()
  command('/tp @s 0 150 5 180 18',3)
  snap('14-missing-translucent-ghost')
  command('/setblock 0 150 0 minecraft:dirt',3)
  snap('15-incorrect-dirt-red')
  command('/setblock 0 150 0 minecraft:stone',3)
  snap('16-correct-stone-no-ghost')
  command('/setblock 0 150 0 minecraft:air',3)
  snap('17-removed-stone-ghost-back')
  command('/tp 0 150 0',2)
  open_schema('18')
  selection[0]=1
  click(405,183,'19-import-oak-log',6)
  snap('20-log-loaded')
  exit_schema()
  command('/tp @s 0 150 5 180 18')
  command('/setblock 0 150 0 minecraft:oak_log[axis=x]',3)
  snap('21-oak-log-wrong-orientation-orange')
  command('/setblock 0 150 0 minecraft:oak_log[axis=y]',3)
  snap('22-oak-log-correct-orientation-hidden')
  page.keyboard.press('Escape')
  click(480,393,'23-return-options',1)
  click(875,578,'24-open-for-unload',1)
  click(875,185,'25-unload-schematic',1)
  snap('26-unloaded')
  browser.close()
except Exception:
 fatal=traceback.format_exc()
 print('TEST FAILURE',fatal[-2800:],flush=True)
finally:
 srv.shutdown()
 out.joinpath('results.json').write_text(json.dumps({'screens':screen,'filePicks':file_picks,'errors':[x for x in events if x['kind'] in ['error','pageerror']][-30:],'fatal':fatal,'note':'Screenshot colors and confirmed server block placements require visual verification; script completion is not proof.'},indent=2))
 out.joinpath('console.json').write_text(json.dumps(events,indent=2))
 print('COMPLETE',len(screen),'screens',file_picks,'FATAL',bool(fatal),flush=True)
 sys.exit(0 if fatal is None and '26-unloaded' in screen and file_picks==['target-stone.schematic','target-oak-log.schematic'] else 2)

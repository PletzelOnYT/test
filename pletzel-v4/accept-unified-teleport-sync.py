#!/usr/bin/env python3
"""Real 26.2 browser-player distant teleport synchronization regression.

Exercises ONLY genuine Minecraft game commands and observed in-game client and
integrated server telemetry. No synthetic player movement, packet injection,
fake world overlays, or mocked renderers. One exact HTML from build artifact.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import http.server,threading,time,re,json,traceback,sys
from PIL import Image,ImageStat
files=list(Path('candidate').rglob('*.html'));assert len(files)==1
html=files[0].resolve();out=Path('teleport-real-sync-evidence');out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k):super().__init__(*a,directory=str(html.parent),**k)
 def log_message(self,*args):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
events=[];shots=[];commands=[];started=time.monotonic();result={'binary':html.name,'tests':[]}
def snap(page,name):
 p=out/(name+'.png');page.screenshot(path=str(p),timeout=45000)
 st=ImageStat.Stat(Image.open(p).convert('L')).stddev[0]
 shots.append({'name':name,'t':round(time.monotonic()-started,2),'lumaVariation':round(st,2)})
def send(page,command):
 page.keyboard.press('t');page.wait_for_timeout(1300)
 for n in range(0,len(command),40):
  page.evaluate("""s=>{
   for(const c of s){
    let k=0,code='Unidentified',shiftKey=false;
    if(/[a-zA-Z]/.test(c)){k=c.toUpperCase().charCodeAt(0);code='Key'+c.toUpperCase();shiftKey=c!==c.toLowerCase();}
    else if(/[0-9]/.test(c)){k=c.charCodeAt(0);code='Digit'+c;}
    else {const m={'/':['Slash',191,false],' ':['Space',32,false],'~':['Backquote',192,true],'-':['Minus',189,false],'.':['Period',190,false]};
    if(m[c]){[code,k,shiftKey]=m[c]}}
    for(const type of ['keydown','keyup']){
     const ev=new KeyboardEvent(type,{key:c,code,shiftKey,bubbles:true,cancelable:true});
     Object.defineProperty(ev,'which',{value:k});Object.defineProperty(ev,'keyCode',{value:k});
     window.dispatchEvent(ev)
    }
   }
  }""",command[n:n+40])
  page.wait_for_timeout(1100)
 page.keyboard.press('Enter');page.wait_for_timeout(1700)
 commands.append(command);print('REAL_TP_SEND',command,flush=True)
def count_packets():
 return sum('inbound packet type=ClientboundPlayerPositionPacket' in e['text'] for e in events)
def count_server_teleports():
 return sum('[CHAT] Teleported ' in e['text'] for e in events)
fault=None
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader','--use-gl=desktop','--disable-features=Vulkan'])
  page=browser.new_page(viewport={'width':1280,'height':720})
  page.on('console',lambda m:events.append({'at':round(time.monotonic()-started,2),'kind':m.type,'text':m.text[:2000]}))
  page.on('pageerror',lambda e:events.append({'at':round(time.monotonic()-started,2),'kind':'pageerror','text':str(e)[:2000]}))
  page.goto('http://127.0.0.1:%s/%s?perfdebug'%(srv.server_address[1],html.name),wait_until='domcontentloaded',timeout=180000)
  page.wait_for_timeout(27000)
  page.mouse.click(638,618);page.wait_for_timeout(3000)
  page.mouse.click(638,572);page.wait_for_timeout(3000)
  page.mouse.click(638,353);page.wait_for_timeout(2200)
  page.keyboard.press('Enter');page.wait_for_timeout(18000)
  page.mouse.click(638,282);page.wait_for_timeout(24000)
  page.mouse.click(640,255);page.wait_for_timeout(900)
  page.mouse.click(640,255);page.wait_for_timeout(900)
  snap(page,'01-real-creative-world-config')
  page.mouse.click(404,672);page.wait_for_timeout(5000)
  t0=time.monotonic()
  while time.monotonic()-t0<340:
   if any((m:=re.search(r'lastTick=(\d+)',e['text'])) and int(m.group(1))>340 for e in events if '[EagPerfHeartbeat]' in e['text']):break
   page.wait_for_timeout(4200)
  else:raise AssertionError('Actual integrated server did not complete initial 340 ticks')
  page.mouse.click(640,360);page.wait_for_timeout(1900)
  snap(page,'02-real-first-playable-world')
  send(page,'/time query gametime')
  assert any('[CHAT] The game time is ' in e['text'] for e in events),'Server cheats not enabled, cannot test real teleport'
  for n,cmd in enumerate(['/tp @p ~1024 180 ~1024','/tp @p ~128 180 ~128']):
   previous=count_packets();server_before=count_server_teleports();began=time.monotonic()
   send(page,cmd)
   seen_server=False;seen_client=False
   for step in range(80):
    seen_server=count_server_teleports()>server_before
    seen_client=count_packets()>previous
    if seen_server and seen_client:break
    page.wait_for_timeout(3500)
   seconds=round(time.monotonic()-began,2)
   obs={'command':cmd,'t':seconds,'server_teleport_confirmed':seen_server,'client_position_packet_confirmed':seen_client,
     'server_teleport_responses':count_server_teleports()-server_before,
     'client_position_packets':count_packets()-previous}
   result['tests'].append(obs);print('REAL_TELEPORT_AUTHORITATIVE_RESULT',json.dumps(obs),flush=True)
   snap(page,'03-teleport-%d-real-world'%(n+1))
   if not seen_server or not seen_client:raise AssertionError('Teleport did not reach both server and client: '+json.dumps(obs))
  browser.close()
except Exception:
 fault=traceback.format_exc();print('REAL_TELEPORT_FATAL',fault[-3000:],flush=True)
finally:srv.shutdown()
result.update({'screens':shots,'commands':commands,'failure':fault,
 'page_errors':[e for e in events if e['kind']=='pageerror'],
 'context':'Normal Ubuntu Chromium software GL; no physical Mac verification'})
(out/'result.json').write_text(json.dumps(result,indent=2))
(out/'all-events.json').write_text(json.dumps(events,indent=2))
if fault or result['page_errors']:sys.exit(2)
print('PASS: real integrated-server command and client transport both confirmed across two distant teleports',flush=True)

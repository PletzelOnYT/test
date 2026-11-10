#!/usr/bin/env python3
"""Two separate Chromium browser profiles, synthetic mic signal, real WebRTC.

This validates auth, SDP/ICE, peer audio RTP byte counters, position-based
unpair and microphone stream cleanup, but NOT two HUMAN players or a REAL
Minecraft server. Do not present it as final microphone/audio acceptance.
"""
import os,sys,json,base64,secrets,subprocess,threading,time,urllib.request,http.server,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
js=root/'client/voice-runtime.js'
assert js.is_file()
work=Path('voice-browser-evidence');work.mkdir(exist_ok=True)
secret=secrets.token_urlsafe(40)
port=25491
listen=25492
env={**os.environ,'VOICE_ADMIN_SECRET':secret,'VOICE_PORT':str(port),
     'VOICE_BIND':'127.0.0.1','VOICE_RANGE':'32','VOICE_ICE_SERVERS':'[]'}
proc=subprocess.Popen(['node',str(root/'gateway/server.mjs')],cwd=str(root/'gateway'),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(root/'client'),**kw)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',listen),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
(root/'client/voice-test.html').write_text('<!doctype html><meta charset="utf-8"><script src="voice-runtime.js"></script><title>Voice audio transport test only</title>')
events=[];result={}
def admin(path,data):
 req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=json.dumps(data).encode('utf-8'),method='POST',headers={'Content-Type':'application/json','X-Pletzel-Admin':secret})
 with urllib.request.urlopen(req,timeout=5) as r:return r.status
pA='00000000-0000-0000-0000-000000000011';pB='00000000-0000-0000-0000-000000000012'
A={'id':pA,'name':'BrowserA','world':'world-uuid-1','x':0,'y':64,'z':0}
B={'id':pB,'name':'BrowserB','world':'world-uuid-1','x':10,'y':64,'z':0}
keepRunning=threading.Event();currentPosition={'b':B}
try:
 for _ in range(80):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as r:
    if r.status==200:break
  except:time.sleep(.15)
 else:raise RuntimeError('Voice gateway did not start')
 assert admin('/admin/snapshot',{'server':'paper-test','players':[A,B]})==200
 tA=secrets.token_urlsafe(32);tB=secrets.token_urlsafe(32)
 for i,t in [(pA,tA),(pB,tB)]:assert admin('/admin/grant',{'id':i,'token':t})==200
 def refreshSnapshots():
  while keepRunning.is_set():
   try: admin('/admin/snapshot',{'server':'paper-test','players':[A,currentPosition['b']]})
   except:pass
   time.sleep(.3)
 keepRunning.set()
 threading.Thread(target=refreshSnapshots,daemon=True).start()
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=[
    '--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--autoplay-policy=no-user-gesture-required','--enable-features=WebRTC-H264WithOpenH264FFmpeg',
    '--disable-dev-shm-usage'])
  ctx1=browser.new_context(permissions=['microphone'],viewport={'width':1280,'height':720})
  ctx2=browser.new_context(permissions=['microphone'],viewport={'width':1280,'height':720})
  pages=[ctx1.new_page(),ctx2.new_page()]
  for i,page in enumerate(pages):
   page.on('pageerror',lambda e,i=i:events.append({'page':i,'type':'error','detail':str(e)}))
   page.on('console',lambda m,i=i:events.append({'page':i,'type':m.type,'detail':m.text[:400]}))
   page.goto(f'http://127.0.0.1:{listen}/voice-test.html',wait_until='load',timeout=40000)
   assert page.evaluate('typeof window.PletzelVoice')=='object'
  for page,token in zip(pages,[tA,tB]):
   page.evaluate('(args)=>window.PletzelVoice.connect(args.url,args.token)',{'url':f'ws://127.0.0.1:{port}/voice','token':token})
  for i,page in enumerate(pages):
   page.wait_for_function('window.PletzelVoice.connected() && window.PletzelVoice.status().includes("nearby: 1")',timeout=45000)
   result[f'connected{i}']=page.evaluate('window.PletzelVoice.status()')
   page.evaluate('window.PletzelVoice.setMode("ptt");window.PletzelVoice.unmute();window.PletzelVoice.setPtt(true)')
  good=False
  for _ in range(100):
   vals=[page.evaluate('window.PletzelVoice.diagnostics()') for page in pages]
   if all(v and v[0]['connection']=='connected' and v[0]['outboundBytes']>1500 and v[0]['inboundBytes']>1500 for v in vals):
    good=True;result['rtpCounters']=vals;break
   time.sleep(.4)
  if not good:raise RuntimeError('Two-way WebRTC AUDIO byte counters never advanced: '+str(vals))
  currentPosition['b']={**B,'x':100}
  assert admin('/admin/snapshot',{'server':'paper-test','players':[A,currentPosition['b']]})==200
  for page in pages:page.wait_for_function('window.PletzelVoice.status().includes("nearby: 0")',timeout=12000)
  result['unpairedAfterDistance']=[p.evaluate('window.PletzelVoice.status()') for p in pages]
  for page in pages:
   page.evaluate('window.PletzelVoice.disconnect()')
   assert page.evaluate('window.PletzelVoice.enabled()')==False
  result['disconnect']='both microphone sessions stopped'
  browser.close()
except Exception as e:
 result['failure']=traceback.format_exc()
 print('BROWSER_VOICE_FAILURE',result['failure'][-5000:],flush=True)
finally:
 keepRunning.clear()
 server.shutdown()
 proc.terminate()
 try:proc.wait(timeout=5)
 except:proc.kill()
 result['events']=events
 (work/'result.json').write_text(json.dumps(result,indent=2))
 print('BROWSER_VOICE_TEST',json.dumps({k:v for k,v in result.items() if k!='events'})[:2000],flush=True)
 if 'failure' in result or any(e['type']=='error' for e in events):sys.exit(2)
print('PASS: TWO synthetic-audio browser streams exchanged real WebRTC RTP and unpaired at range',flush=True)
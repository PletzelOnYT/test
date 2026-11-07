#!/usr/bin/env python3
"""Evidence-gathering UI smoke test, not a proof of hologram success by itself."""
import glob, json, os, time, threading, http.server
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path("candidate").resolve()
htmls = list(root.rglob("*Schematica*CANDIDATE.html"))
assert len(htmls)==1, [str(p) for p in htmls]
source=htmls[0]
out=Path("smoke-evidence");out.mkdir(parents=True,exist_ok=True)
# CI test-only: restore soundless yet valid EPK bytes in the HTML to
# exercise the REAL standalone inline payload routing, including worker boot.
# Never publish or deliver this modified test-only HTML.
import re,base64
test_source=source.read_text('utf8')
m=re.search(r'<script\b(?=[^>]*\bid="eag-inline-assets")[^>]*>(.*?)</script>',test_source,re.S)
assert m,'missing real asset EPK'
assets=base64.b64decode(re.sub(r'\s+','',m.group(1)))
assert assets.startswith(b'EAGPKG$$'),assets[:20]
m2=re.search(r'(<script type="application/octet-stream" id="eag-inline-sounds" data-size=")(\d+)(">\s*)(.*?)(</script>)',test_source,re.S)
assert m2,'missing temporary sound placeholder'
b64=base64.b64encode(assets).decode('ascii')
formatted='\n'.join(b64[i:i+262144] for i in range(0,len(b64),262144))
replacement=m2.group(1)+str(len(assets))+m2.group(3)+'\n'+formatted+'\n'+m2.group(5)
test_source=test_source[:m2.start()]+replacement+test_source[m2.end():]
# Test-only XMLHttpRequest bridge for inline EPK data on HTTP origin.
# Main browser fetch is already patched by the standalone generator; worker
# XHR has its own inline-asset override, but main-page XHR needs one too.
anchor='  window.fetch = function (input, init) {'
assert test_source.count(anchor)==1,'unknown standalone fetch shim'
helper="""  var __testOriginalXHR = window.XMLHttpRequest;
  var __testPayloadMemo = Object.create(null);
  function __testPayload(name){
    var id=payloadIds[name];
    if(!id)return Promise.reject(new Error('Unknown inline EPK '+name));
    if(!__testPayloadMemo[id])__testPayloadMemo[id]=decodePayloadAsync(id);
    return __testPayloadMemo[id];
  }
  window.XMLHttpRequest = function(){
    var self=this, real=null, url='', inline=false, callbacks=Object.create(null);
    this.responseType='';this.status=0;this.response=null;this.readyState=0;
    this.addEventListener=function(name,cb){
      (callbacks[name]||(callbacks[name]=[])).push(cb);
    };
    this.removeEventListener=function(name,cb){
      callbacks[name]=(callbacks[name]||[]).filter(function(fn){return fn!==cb;});
    };
    function dispatch(name){
      var evt={type:name,target:self,currentTarget:self,loaded:self.response?self.response.byteLength:0};
      (callbacks[name]||[]).forEach(function(fn){try{fn.call(self,evt);}catch(e){console.error(e);}});
      var fn=self['on'+name];if(typeof fn==='function')fn.call(self,evt);
    }
    this.open=function(method,nextURL,async){
      url=String(nextURL);inline=url.indexOf(inlinePayloadPrefix)===0;
      if(inline){self.readyState=1;dispatch('readystatechange');}
      else{
        real=new __testOriginalXHR();
        real.open(method,nextURL,async);
        for(var name in callbacks)(function(n){real.addEventListener(n,function(e){dispatch(n);});})(name);
      }
    };
    this.send=function(body){
      if(!inline){
        real.responseType=self.responseType;
        real.send(body);
        return;
      }
      __testPayload(url.slice(inlinePayloadPrefix.length).split(/[?#]/)[0])
      .then(function(buf){
        self.response=buf;self.status=200;self.readyState=4;
        dispatch('readystatechange');dispatch('load');dispatch('loadend');
      },function(err){
        self.status=0;self.readyState=4;
        dispatch('error');dispatch('loadend');console.error(err);
      });
    };
    this.abort=function(){if(real)real.abort();};
    this.setRequestHeader=function(k,v){if(real)real.setRequestHeader(k,v);};
    this.getResponseHeader=function(k){return real?real.getResponseHeader(k):null;};
  };
"""
test_source=test_source.replace(anchor,helper+anchor,1)
test_source=test_source.replace('return decodePayloadAsync(id).then(function (raw) {',
    'return __testPayload(name).then(function (raw) {',1)
source.write_text(test_source)
print('CI TEST ONLY: valid EPK inlined for both assets and sound, main+worker custom URL routing',len(assets),flush=True)
class Server(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(source.parent),**kwargs)
    def log_message(self,format,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Server)
threading.Thread(target=server.serve_forever,daemon=True).start()
fixture=out/"mini-house-5x4x5.schematic"
import gzip,struct
W,H,L=5,4,5
blocks=[1 if y==0 or (y>0 and (x==0 or z==0 or x==4 or z==4)) else 0
        for y in range(H) for z in range(L) for x in range(W)]
b=bytearray(b"\x0a\x00\x00")
def tag(name,typ,value):
    key=name.encode()
    b.extend(bytes([typ])+struct.pack(">H",len(key))+key+value)
for n,v in [("Width",W),("Height",H),("Length",L)]:
    tag(n,2,struct.pack(">h",v))
for n,values in [("Blocks",blocks),("Data",[0]*100)]:
    tag(n,7,struct.pack(">i",len(values))+bytes(values))
tag("Materials",8,struct.pack(">H",5)+b"Alpha")
b.append(0);fixture.write_bytes(gzip.compress(b,mtime=0))
assert len(blocks)==100
errors=[];steps=[];file_select=[];import_debug=[]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=False,args=[
      "--no-sandbox","--disable-dev-shm-usage","--enable-webgl",
      "--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
      "--use-gl=desktop","--disable-features=Vulkan"])
  page=browser.new_page(viewport={"width":1280,"height":720},accept_downloads=True)
  page.on("pageerror",lambda e:errors.append("JS: "+str(e)[:1000]))
  page.on("console",lambda m:errors.append("CONSOLE: "+m.text[:900]) if m.type=="error" else None)
  page.on("crash",lambda:errors.append("CHROMIUM RENDERER CRASH"))
  def picked(fc):
      try:fc.set_files(str(fixture.resolve()));file_select.append("filled 5x4x5 NBT")
      except Exception as e:file_select.append("file picker error "+str(e))
  page.on("filechooser",picked)
  page.on("console",lambda m:import_debug.append(m.text[:800]) if "[SMOKE]" in m.text else None)
  page.add_init_script("""
  (() => {
    var NativeFR = window.FileReader;
    window.FileReader=function(){
      var r=new NativeFR();
      r.addEventListener('load',function(){
        console.log('[SMOKE] FileReader load bytes='+(r.result&&r.result.byteLength));
      });
      r.addEventListener('error',function(){
        console.log('[SMOKE] FileReader error '+(r.error&&r.error.message));
      });
      return r;
    };
    window.FileReader.prototype=NativeFR.prototype;
  })();
  """)
  def snapshot(name):
      try:
          page.screenshot(path=str(out/(name+".png")),timeout=12000)
          steps.append(name+": screenshot")
      except Exception as e:steps.append(name+": screenshot unavailable "+str(e)[:180])
  def click(name,x,y,delay=5):
      try:
          page.mouse.click(x,y);time.sleep(delay)
          snapshot(name)
      except Exception as e:
          steps.append(name+": click error "+str(e)[:180])
  try:
      page.goto("http://127.0.0.1:%d/%s"%(server.server_address[1],source.name),
                wait_until="domcontentloaded",timeout=150000)
      time.sleep(25);snapshot("01-boot")
      click("02-profile",638,618,8)
      click("03-continue",638,572,8)
      click("09-options",480,570,6)
      click("10-schematica",876,578,6)
      click("11-load-file",405,174,12)
      page.mouse.click(119,89);time.sleep(5);snapshot("12-refocused-after-import")
  except Exception as e:errors.append("TEST: "+str(e)[:1200])
  try:
      diag=page.evaluate("""() => ({origin:location.origin,webgl2:!!document.createElement('canvas').getContext('webgl2'),canvas:document.querySelectorAll('canvas').length,hasWasm:!!window.__eaglerWasmModule})""")
  except Exception as e:diag={"error":str(e)[:250]}
  try:
      gameLogTail=page.evaluate("""() => (window.__log||[]).filter(x=>/schematica|schematic|FileChooser|NBT|load/i.test(x)).slice(-70)""")
  except Exception as e:
      gameLogTail=["log probe failed: "+str(e)[:300]]
  (out/"results.json").write_text(json.dumps({"steps":steps,"errors":errors[-80:],
     "fileChooser":file_select,"importDebug":import_debug,"inGameLogTail":gameLogTail, "diagnostic":diag,"proofOfHologram":False,
     "note":"Screenshot must be visually inspected; fixture import does not prove rendering."},indent=2))
  browser.close()
server.shutdown()
print((out/"results.json").read_text()[:6000])

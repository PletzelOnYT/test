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
# CI test-only: serve real EPK bytes over same-origin HTTP rather than using the
# standalone custom URL (not valid as XMLHttpRequest origin in Chromium HTTP mode).
# Never publish this smoke-test HTML as the playable client.
import re,base64
test_source=source.read_text('utf8')
m=re.search(r'<script\b(?=[^>]*\bid="eag-inline-assets")[^>]*>(.*?)</script>',test_source,re.S)
assert m, 'missing built-in asset archive'
assets=base64.b64decode(re.sub(r'\s+','',m.group(1)))
assert assets.startswith(b'EAGPKG$'), assets[:20]
(source.parent/'assets.epk').write_bytes(assets)
# Prior CI intermediate intentionally contains a 48-byte placeholder sound EPK.
# Use valid base asset EPK as a soundless substitute ONLY for this CI rendering test;
# user-delivered final HTML restores the full V3 sound library locally.
(source.parent/'sounds.epk').write_bytes(assets)
anchor='entries[i].url = inlinePayloadPrefix + name;'
assert test_source.count(anchor)==1, 'unknown standalone asset shim'
test_source=test_source.replace(anchor,'entries[i].url = name;',1)
source.write_text(test_source)
print('CI TEST ONLY: replaced custom asset URLs with same-origin EPKs',len(assets),'bytes',flush=True)
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
errors=[];steps=[];file_select=[]
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
      click("04-title",638,353,7) # Singleplayer
      click("05-new-world-choice",638,282,7)
      click("06-create-world",638,661,80)
      snapshot("07-world-maybe")
      page.keyboard.press("Escape");time.sleep(4);snapshot("08-pause")
      click("09-options",484,500,6)
      click("10-schematica",895,577,5)
      click("11-load-file",405,183,12)
      page.keyboard.press("Escape");time.sleep(3);snapshot("12-after-escape")
  except Exception as e:errors.append("TEST: "+str(e)[:1200])
  try:
      diag=page.evaluate("""() => ({origin:location.origin,webgl2:!!document.createElement('canvas').getContext('webgl2'),canvas:document.querySelectorAll('canvas').length,hasWasm:!!window.__eaglerWasmModule})""")
  except Exception as e:diag={"error":str(e)[:250]}
  (out/"results.json").write_text(json.dumps({"steps":steps,"errors":errors[-80:],
     "fileChooser":file_select,"diagnostic":diag,"proofOfHologram":False,
     "note":"Screenshot must be visually inspected; fixture import does not prove rendering."},indent=2))
  browser.close()
server.shutdown()
print((out/"results.json").read_text()[:6000])

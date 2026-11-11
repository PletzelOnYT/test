#!/usr/bin/env python3
"""Standalone HTML opened via file:// with ALL HTTP(S) requests blocked.

Uses real headed Chromium, real game WebGL canvas, and screenshots. No localhost
server, DOM mock, or injected resource replacements. Proves offline title boot,
not full singleplayer acceptance.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image,ImageStat
import time,json,traceback,sys,os
htmls=list(Path("candidate").rglob("*.html"));assert len(htmls)==1
html=htmls[0].resolve();out=Path("offline-file-url-evidence");out.mkdir(exist_ok=True)
events=[];http_requests=[];screens=[];fault=None;started=time.monotonic()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=os.environ.get("PLETZEL_CI_HEADLESS")=="1",args=["--no-sandbox","--disable-dev-shm-usage",
    "--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader",
    "--use-gl=desktop","--disable-features=Vulkan"])
  ctx=browser.new_context(viewport={"width":1280,"height":720})
  def block(route):
   http_requests.append(route.request.url)
   route.abort("blockedbyclient")
  ctx.route("http://**/*",block)
  ctx.route("https://**/*",block)
  page=ctx.new_page()
  page.on("console",lambda m:events.append({"at":round(time.monotonic()-started,2),"kind":m.type,"text":m.text[:1600]}))
  page.on("pageerror",lambda e:events.append({"at":round(time.monotonic()-started,2),"kind":"pageerror","text":str(e)[:1700]}))
  def snap(name):
   p=out/(name+".png")
   page.screenshot(path=str(p),timeout=60000)
   sd=ImageStat.Stat(Image.open(p).convert("L")).stddev[0]
   screens.append({"name":name,"lumaStdDev":round(sd,2),"seconds":round(time.monotonic()-started,1)})
   print("OFFLINE_FILE_SCREEN",screens[-1],flush=True)
  page.goto(html.as_uri()+"?perfdebug",wait_until="domcontentloaded",timeout=180000)
  page.wait_for_timeout(30000);snap("01-native-offline-profile")
  page.mouse.click(638,618);page.wait_for_timeout(4000)
  page.mouse.click(638,572);page.wait_for_timeout(5000)
  snap("02-native-offline-main-menu")
  # Must still have the actual Minecraft canvas after the entire inline WASM
  # and assets boot. DOM canvas check is not a substitute for the screenshot.
  canvas=page.evaluate("() => Array.from(document.querySelectorAll('canvas')).map(c=>({width:c.width,height:c.height}))")
  print("OFFLINE_CANVASES",canvas,flush=True)
  browser.close()
except Exception:
 fault=traceback.format_exc();print("OFFLINE_FILE_FATAL",fault[-3200:],flush=True)
result={"tested_html":html.name,"browser":"Chromium file://, http/https deliberately blocked",
        "screenshots":screens,"external_requests":http_requests,
        "page_errors":[e for e in events if e["kind"]=="pageerror"],
        "fault":fault,"limit":"Title boot only, not singleplayer save or voice server"}
(out/"result.json").write_text(json.dumps(result,indent=2))
(out/"events.json").write_text(json.dumps(events,indent=2))
print("OFFLINE_STANDALONE_RESULT",json.dumps(result)[:5000],flush=True)
if fault or len(screens)!=2 or result["page_errors"] or http_requests or any(s["lumaStdDev"]<12 for s in screens):
 sys.exit(2)
if not canvas or not any(x["width"]>=1000 and x["height"]>=600 for x in canvas):
 raise SystemExit("No real full-size Minecraft WebGL canvas in offline file:// mode")
print("PASS: real native title/profiles/render canvas boot from ONE HTML offline",flush=True)

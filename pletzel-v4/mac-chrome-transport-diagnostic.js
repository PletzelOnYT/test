/* Pletzel V4 Chrome/macOS diagnostic. No payloads, servers or player coordinates recorded.
   Paste in DevTools Console before reproducing, export with __pletzelDiag.export().
   Does not upload telemetry or modify the Minecraft packet data. */
(() => {
 if (globalThis.__pletzelDiag?.running) return console.warn("Pletzel diagnostic already running");
 const original=WebSocket.prototype.send, born=performance.now(), events=[];
 const stats={attempts:0,sent:0,errors:0,bytes:0,lastSend:null,maxBuffered:0,longTasks:0,maxLongTask:0,rafGaps:0};
 const t=()=>performance.now()-born;
 const record=(type,fields={})=>{events.push({atSeconds:+(t()/1000).toFixed(2),type,...fields});if(events.length>1500)events.shift()};
 function intercept(data){
  stats.attempts++;
  const size=typeof data==="string"?data.length:ArrayBuffer.isView(data)?data.byteLength:data instanceof ArrayBuffer?data.byteLength:typeof data?.size==="number"?data.size:0;
  try{const ret=original.apply(this,arguments);stats.sent++;stats.bytes+=size;stats.lastSend=t();stats.maxBuffered=Math.max(stats.maxBuffered,this.bufferedAmount||0);return ret}
  catch(e){stats.errors++;record("websocketSendException",{message:String(e)});throw e}
 }
 WebSocket.prototype.send=intercept;
 const visibility=()=>record("visibility",{state:document.visibilityState});
 const error=e=>record("pageError",{message:String(e.message||e.reason||e).slice(0,240)});
 document.addEventListener("visibilitychange",visibility);addEventListener("error",error);addEventListener("unhandledrejection",error);
 let perf;try{perf=new PerformanceObserver(list=>{for(const x of list.getEntries()){stats.longTasks++;stats.maxLongTask=Math.max(stats.maxLongTask,x.duration)}});perf.observe({entryTypes:["longtask"]})}catch(e){}
 let on=true,prior=performance.now(),frame;
 const raf=x=>{if(!on)return;if(x-prior>250)stats.rafGaps++;prior=x;frame=requestAnimationFrame(raf)};
 frame=requestAnimationFrame(raf);
 let last=0;
 const timer=setInterval(()=>{const elapsed=t();record("sample",{outboundFramesIn5s:stats.sent-last,secondsSinceLastSend:stats.lastSend===null?null:+((elapsed-stats.lastSend)/1000).toFixed(2),maxBufferedBytes:stats.maxBuffered,visibility:document.visibilityState,jsHeapBytes:performance.memory?.usedJSHeapSize??null,rafGaps:stats.rafGaps});last=stats.sent;console.info("[PletzelDiag]",events.at(-1))},5000);
 const api={running:true,
  snapshot:()=>({created:new Date().toISOString(),browser:navigator.userAgent,cores:navigator.hardwareConcurrency,visible:document.visibilityState,stats:{...stats},events:events.slice()}),
  export(){const blob=new Blob([JSON.stringify(this.snapshot(),null,2)],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="pletzel-mac-chrome-"+Date.now()+".json";a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);return a.download},
  stop(){on=false;cancelAnimationFrame(frame);clearInterval(timer);perf?.disconnect();document.removeEventListener("visibilitychange",visibility);removeEventListener("error",error);removeEventListener("unhandledrejection",error);if(WebSocket.prototype.send===intercept)WebSocket.prototype.send=original;this.running=false}
 };
 Object.defineProperty(globalThis,"__pletzelDiag",{value:api,configurable:true});
 record("start",{visibility:document.visibilityState});
 console.info("[PletzelDiag] Enabled; reproduce then call __pletzelDiag.export().");
})();
/* Pletzel V4 opt-in field diagnostics v1. Safe default: only an Alt+Shift+D key listener.
   Activate at startup with ?pletzeldiag=1&perfdebug&workerlog, or Alt+Shift+D.
   No packets, WASM bytes, chat text, server address, or credentials are recorded. */
(() => {
  'use strict';
  if (window.__pletzelFieldDiagnostics) return;
  const version = '1.0.0-field';
  const maxEvents = 1800;
  const maxSnapshots = 1600;
  const state = {
    version, startedUTC: null, enabled: false, activatedBy: null,
    browser: { userAgent: navigator.userAgent, language: navigator.language, platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency || null, deviceMemoryGiB: navigator.deviceMemory || null },
    page: { protocol: location.protocol, pageVisible: document.visibilityState,
      crossOriginIsolated: !!self.crossOriginIsolated },
    network: { socketsConstructed: 0, socketsOpened: 0, socketsClosed: 0,
      socketErrors: 0, readyStates: [], framesSentToWebSocketAPI: 0, bytesSentToWebSocketAPI: 0,
      framesReceivedByWebSocket: 0, bytesReceivedByWebSocket: 0,
      lastOutboundAt: null, lastInboundAt: null, maxBufferedAmountBytes: 0,
      lastMovementPacketAcceptedByRemoteServer: null, remoteServerPingMs: null,
      note: 'WebSocket.send success means queued in browser, NOT delivered/accepted by remote Minecraft server. Movement packet IDs are not decoded.' },
    workers: { constructed: 0, messageEvents: 0, errorEvents: 0, messageErrorEvents: 0, lastMessageAt: null },
    render: { canvasElements: 0, contextsLost: 0, contextsRestored: 0,
      webglGetErrorCalls: 0, nonZeroWebglErrors: 0, recentWebglErrors: [],
      createdMeshes: null, failedBufferUploads: null,
      note: 'Native WASM renderer has no exposed mesh counters in this binary. WebGL errors only observed when application calls getError().' },
    server: { heartbeatCount: 0, lastTick: null, lastTickChangedUTC: null, lastHeartbeatUTC: null,
      phase: null, activeTick: null, sinceCompletedMs: null,
      worldgenQueue: null, generationClaims: null, generationTasks: null,
      liveBlockingChunk: null, reportedTPS: null, observedTPS: null, lastCompletedTickMs: null,
      startedTick: null, steadyNowMs: null, progressed: null, gcCount: null, gcTimeMs: null,
      clientXYZ: null, lastSentMovementXYZ: null, serverAuthoritativeXYZ: null,
      note: 'Live server TPS/position requires native ?perfdebug&workerlog logs or server-side receipt logging. No synthetic TPS or XYZ.' },
    errors: [], events: [], snapshots: [], markers: []
  };
  let enabled = false, installed = false, panel = null, output = null, indicator = null;
  let frameCount = 0, frameLast = 0, fps = null, fpsRAF = 0;
  const date = () => new Date().toISOString();
  function push(array, item, limit = maxEvents) { array.push(item); if (array.length > limit) array.splice(0, array.length-limit); }
  function clean(text) {
    return String(text).slice(0, 1100)
      .replace(/(?:wss?:\/\/)[^/\s)'"<>]+/gi, '[websocket-server-redacted]')
      .replace(/https?:\/\/[^\s)'"<>]+/gi, '[url-redacted]')
      .replace(/(token|secret|password|authorization|sessionid|cookie)\s*[:=]\s*[^\s,;]+/gi, '$1=[redacted]');
  }
  const number = (s, key) => { const m = new RegExp('\\b'+key+'=(-?\\d+(?:\\.\\d+)?)').exec(s); return m ? Number(m[1]) : null; };
  function event(type, detail) { if (enabled) push(state.events, { at:date(), type, detail: clean(detail) }); }
  function takeNativeLog(level, args) {
    if (!enabled) return;
    const text = args.map(a => typeof a === 'string' ? a : a && a.message ? a.message : typeof a).join(' ');
    const diagnostic = /\[(?:EagPerf(?:Client|Heartbeat|ChunkWait)?|Pletzel(?:ActiveChunkWait|WakeRescue26|TeleportTrace)|.*(?:WebGL|WebGPU|WASM))\]/i.test(text);
    if (diagnostic) {
      const v = clean(text);
      push(state.events, {at:date(),type:'native-'+level,detail:v});
      if (/\[EagPerfHeartbeat\]/.test(text)) {
        state.server.heartbeatCount++;
        const tick=number(text,'lastTick');
        const steadyNow=number(text,'steadyNow');
        if (tick !== null) {
          if (state.server.lastTick !== null && state.server.steadyNowMs !== null &&
                steadyNow !== null && steadyNow>state.server.steadyNowMs && tick>=state.server.lastTick) {
            const observed=(tick-state.server.lastTick)*1000/(steadyNow-state.server.steadyNowMs);
            state.server.observedTPS = Math.round(observed*100)/100;
          }
          if (tick !== state.server.lastTick) state.server.lastTickChangedUTC = date();
          state.server.lastTick=tick;
        }
        state.server.steadyNowMs=steadyNow;
        const startedAt=number(text,'tickStartedAt'), completedAt=number(text,'tickCompletedAt');
        if(startedAt!==null && completedAt!==null && completedAt>=startedAt && startedAt>0)
          state.server.lastCompletedTickMs=completedAt-startedAt;
        state.server.startedTick=number(text,'startedTick');
        state.server.gcCount=number(text,'gcCount');
        state.server.gcTimeMs=number(text,'gcTime');
        const progressed=/\bprogressed=(true|false)/.exec(text);
        if(progressed)state.server.progressed=progressed[1]==='true';
        state.server.lastHeartbeatUTC=date();
        for (const [from,to] of [['activeTick','activeTick'],['sinceCompleted','sinceCompletedMs'],
          ['worldgenQueue','worldgenQueue'],['claims','generationClaims'],['tasks','generationTasks']]) {
          const n=number(text,from); if(n!==null) state.server[to]=n;
        }
        const phase = /\bphase=([^\s]+)/.exec(text); if(phase)state.server.phase=phase[1];
      }
      if (/\[PletzelActiveChunkWait\]/.test(text)) state.server.liveBlockingChunk=clean(text);
    } else if (level==='error' || (level==='warn' && /(webgl|webgpu|wasm|worker|unhandled|exception|chunk|meshing)/i.test(text))) {
      push(state.errors, {at:date(),kind:'console-'+level,text:clean(text)},250);
    }
  }
  const size = data => typeof data === 'string' ? new TextEncoder().encode(data).byteLength
    : data && typeof data.byteLength === 'number' ? data.byteLength
    : data && typeof data.size === 'number' ? data.size : 0;
  function installHooks(){
    if (installed) return; installed=true;
    for (const level of ['log','info','warn','error','debug']) {
      const original = console[level];
      if(typeof original!=='function')continue;
      console[level] = function (...args) { try { takeNativeLog(level,args); } catch(e){} return Reflect.apply(original,this,args); };
    }
    window.addEventListener('error', e => { if(enabled)push(state.errors,{at:date(),kind:'uncaught',text:clean(e.message||e.error||'unknown')},250); });
    window.addEventListener('unhandledrejection',e=>{ if(enabled)push(state.errors,{at:date(),kind:'unhandled-promise',text:clean(e.reason?.message||e.reason||'unknown')},250); });
    document.addEventListener('visibilitychange',()=>{state.page.pageVisible=document.visibilityState;event('tab-visibility',document.visibilityState);});
    try {
      const NativeWebSocket=window.WebSocket;
      class WatchedWebSocket extends NativeWebSocket {
        constructor(...args){
          super(...args);
          state.network.socketsConstructed++;
          this.addEventListener('open',()=>{if(enabled){state.network.socketsOpened++;event('websocket-open','socket opened, endpoint redacted');}});
          this.addEventListener('close', e=>{if(enabled){state.network.socketsClosed++;event('websocket-close','code='+e.code+' clean='+e.wasClean);}});
          this.addEventListener('error',()=>{if(enabled){state.network.socketErrors++;event('websocket-error','transport error');}});
          this.addEventListener('message',e=>{if(!enabled)return;state.network.framesReceivedByWebSocket++;state.network.bytesReceivedByWebSocket+=size(e.data);state.network.lastInboundAt=date();});
        }
      }
      window.WebSocket=WatchedWebSocket;
      const oldSend=NativeWebSocket.prototype.send;
      NativeWebSocket.prototype.send=function(data){
        if(enabled){
          state.network.framesSentToWebSocketAPI++;
          state.network.bytesSentToWebSocketAPI+=size(data);
          state.network.lastOutboundAt=date();
          state.network.maxBufferedAmountBytes=Math.max(state.network.maxBufferedAmountBytes,this.bufferedAmount||0);
        }
        return Reflect.apply(oldSend,this,[data]);
      };
    } catch(e){event('hook-unavailable','WebSocket hooks: '+clean(e.message));}
    try {
      const NativeWorker=window.Worker;
      class WatchedWorker extends NativeWorker {
        constructor(...args){
          super(...args);
          state.workers.constructed++;
          this.addEventListener('message',()=>{if(enabled){state.workers.messageEvents++;state.workers.lastMessageAt=date();}});
          this.addEventListener('error',e=>{if(enabled){state.workers.errorEvents++;push(state.errors,{at:date(),kind:'worker-error',text:clean(e.message)},250);}});
          this.addEventListener('messageerror',()=>{if(enabled){state.workers.messageErrorEvents++;event('worker-messageerror','undecodable worker message');}});
        }
      }
      window.Worker=WatchedWorker;
    }catch(e){event('hook-unavailable','Worker hooks: '+clean(e.message));}
    for(const cls of ['WebGLRenderingContext','WebGL2RenderingContext']) {
      try {
        const P=window[cls]?.prototype, orig=P?.getError;
        if(!orig)continue;
        P.getError=function(){const value=Reflect.apply(orig,this,[]);if(enabled){state.render.webglGetErrorCalls++;if(value!==0){state.render.nonZeroWebglErrors++;push(state.render.recentWebglErrors,{at:date(),context:cls,code:value},40);}}return value;};
      }catch(e){event('hook-unavailable',cls+' '+clean(e.message));}
    }
    const watchCanvas=canvas=>{
      if(canvas.__pletzelCanvasWatched)return;
      canvas.__pletzelCanvasWatched=true;state.render.canvasElements++;
      canvas.addEventListener('webglcontextlost',()=>{if(enabled)state.render.contextsLost++;});
      canvas.addEventListener('webglcontextrestored',()=>{if(enabled)state.render.contextsRestored++;});
    };
    document.querySelectorAll('canvas').forEach(watchCanvas);
    new MutationObserver(mutations=>{for(const m of mutations){for(const n of m.addedNodes){if(n.nodeType!==1)continue;if(n.tagName==='CANVAS')watchCanvas(n);n.querySelectorAll?.('canvas').forEach(watchCanvas);}}}).observe(document.documentElement,{childList:true,subtree:true});
    if(window.PerformanceObserver){
      try{new PerformanceObserver(list=>{for(const e of list.getEntries()){if(enabled && e.duration>=50)event('main-thread-longtask',`${Math.round(e.duration)}ms`);}}).observe({entryTypes:['longtask']});}catch(e){}
    }
    setInterval(snapshot,2000);
  }
  function frame(t){
    if(!enabled){fpsRAF=0;return;}
    frameCount++;
    if(!frameLast)frameLast=t;
    if(t-frameLast>=2000){fps=Math.round(frameCount*1000/(t-frameLast));frameCount=0;frameLast=t;}
    fpsRAF=requestAnimationFrame(frame);
  }
  function snapshot(){
    if(!enabled)return;
    const heartbeatAge=state.server.lastHeartbeatUTC ? Date.now()-Date.parse(state.server.lastHeartbeatUTC) : null;
    const lastCompletedAge=state.server.lastTickChangedUTC ? Date.now()-Date.parse(state.server.lastTickChangedUTC) : null;
    const reported = state.server.heartbeatCount ? (lastCompletedAge>5000 ? 'server tick not advancing' : 'heartbeat seen') : 'no worker heartbeat received';
    const record={at:date(),fps,visibility:document.visibilityState,heartbeatAgeMs:heartbeatAge,
      timeSinceTickAdvancedMs:lastCompletedAge,integratedServer:reported,
      lastTick:state.server.lastTick,observedTPS:state.server.observedTPS,
      lastCompletedTickMs:state.server.lastCompletedTickMs,activeTick:state.server.activeTick,
      phase:state.server.phase,sinceCompletedMs:state.server.sinceCompletedMs,
      worldgenQueue:state.server.worldgenQueue,claims:state.server.generationClaims,tasks:state.server.generationTasks,
      workerMessages:state.workers.messageEvents,socketOutbound:state.network.framesSentToWebSocketAPI,
      socketInbound:state.network.framesReceivedByWebSocket,wsMaxBufferedBytes:state.network.maxBufferedAmountBytes,
      memoryBytes:performance.memory?.usedJSHeapSize || null};
    push(state.snapshots,record,maxSnapshots);
    if(output){output.textContent=`Main: ${fps===null?'—':fps+' FPS'} · ${record.visibility} · Workers ${state.workers.constructed} / ${state.workers.messageEvents} messages\n`+
      `Server: ${record.integratedServer}; tick ${record.lastTick??'n/a'}; ${record.observedTPS??'n/a'} TPS; ${record.lastCompletedTickMs??'n/a'} ms tick; phase ${record.phase??'n/a'}\n`+
      `Chunks: ${record.worldgenQueue??'n/a'} queued / ${record.tasks??'n/a'} tasks / ${record.claims??'n/a'} claims\n`+
      `WS API: sent ${state.network.framesSentToWebSocketAPI} / received ${state.network.framesReceivedByWebSocket} · max queue ${Math.round(state.network.maxBufferedAmountBytes/1024)} KiB · WebGL errors ${state.render.nonZeroWebglErrors}`;}
  }
  function report(){
    snapshot();return {...state, exportedUTC:date(), keyLimitations:[
      'Remote server authoritative position, remote movement-receipt count, and actual network RTT are UNAVAILABLE unless server logs or server-side plugin confirms them.',
      'WASM local XYZ, chunk mesh counts, and movement packet IDs are not exposed by this compiled binary. Never infer them from WebSocket.send().',
      'Integrated server heartbeat may be unavailable without perfdebug&workerlog at page startup.',
      'Report intentionally does not include chat, WebSocket binary contents, authentication tokens, or complete server addresses.'
    ]};
  }
  function download(ext){
    const data=report();const txt=ext==='json'?JSON.stringify(data,null,2):[
      'Pletzel V4 field diagnostics',`Export: ${data.exportedUTC}`,`Browser: ${data.browser.userAgent}`,
      '\nSUMMARY\n'+JSON.stringify(data.snapshots.slice(-20),null,2),
      '\nSERVER\n'+JSON.stringify(data.server,null,2),
      '\nNETWORK\n'+JSON.stringify(data.network,null,2),
      '\nWORKERS / WEBGL\n'+JSON.stringify({workers:data.workers,render:data.render},null,2),
      '\nERRORS\n'+JSON.stringify(data.errors,null,2),
      '\nEVENTS\n'+JSON.stringify(data.events,null,2),
      '\nMARKERS\n'+JSON.stringify(data.markers,null,2),
      '\nLIMITATIONS\n'+data.keyLimitations.join('\n')].join('\n');
    const blob=new Blob([txt],{type:ext==='json'?'application/json':'text/plain'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`Pletzel-V4-Mac-${new Date().toISOString().replace(/[:.]/g,'-')}.${ext}`;
    document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  function button(label,handler){const b=document.createElement('button');b.textContent=label;b.type='button';b.style.cssText='background:#193e28;color:#d1f5d5;border:1px solid #73987c;border-radius:5px;padding:6px 8px;cursor:pointer;font:12px system-ui';b.addEventListener('click',handler);return b;}
  function ensurePanel(){
    if(panel)return;
    panel=document.createElement('section'); panel.setAttribute('aria-label','Pletzel diagnostics');
    panel.style.cssText='position:fixed!important;right:14px;top:12px;z-index:2147483647!important;background:#102019f2;color:#e9fff0;padding:12px;border:1px solid #6da07b;border-radius:8px;box-shadow:0 6px 22px #0009;min-width:280px;max-width:min(520px,90vw);font:12px system-ui;pointer-events:auto';
    const heading=document.createElement('div');heading.textContent='Pletzel V4 · Field diagnostics (opt-in)';heading.style.cssText='font-weight:700;margin-bottom:8px';panel.appendChild(heading);
    output=document.createElement('pre');output.style.cssText='white-space:pre-wrap;margin:0 0 8px 0;font:11px/1.5 ui-monospace,monospace';output.textContent='Recording native/browser metrics. Open with ?pletzeldiag=1&perfdebug&workerlog for server ticks.';panel.appendChild(output);
    const buttons=document.createElement('div');buttons.style.cssText='display:flex;gap:5px;flex-wrap:wrap';
    buttons.append(button('Export JSON',()=>download('json')),button('Export TXT',()=>download('txt')),
      button('Mark problem',()=>{let kind=prompt('Briefly describe the problem (e.g. multiplayer server-position freeze):');if(kind)push(state.markers,{at:date(),description:clean(kind),snapshot:state.snapshots.at(-1)},100);}),
      button('Stop',disable));panel.appendChild(buttons);
    const note=document.createElement('div');note.textContent='No chat or packet payloads recorded. Browser WebSocket sends ≠ server movement acceptance.';
    note.style.cssText='font-size:10px;opacity:.85;margin-top:9px';panel.appendChild(note);
    (document.body||document.documentElement).appendChild(panel);
  }
  function activate(by){
    if(enabled)return;enabled=true;state.enabled=true;state.startedUTC ||= date();state.activatedBy=by;
    installHooks();ensurePanel();if(!fpsRAF){frameCount=0;frameLast=0;fpsRAF=requestAnimationFrame(frame);}
    event('activation',by);snapshot();
  }
  function disable(){enabled=false;state.enabled=false;event('disabled','user action');if(panel){panel.remove();panel=null;output=null;}fpsRAF=0;}
  window.__pletzelFieldDiagnostics=Object.freeze({start:()=>activate('console'),stop:disable,exportJSON:()=>download('json'),snapshot:()=>JSON.parse(JSON.stringify(report()))});
  document.addEventListener('keydown',e=>{
    if(e.altKey && e.shiftKey && e.code==='KeyD'){
      e.preventDefault();e.stopImmediatePropagation();enabled?disable():activate('Alt+Shift+D');
    }
  },true);
  if(new URLSearchParams(location.search).get('pletzeldiag')==='1'){
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>activate('URL flag'),{once:true});
    else activate('URL flag');
  }
})();

/* Pletzel V4 browser voice runtime (original implementation, no Fabric runtime).
 * No DOM overlay: Minecraft Java renders all GUI. Real audio uses browser WebRTC.
 * Permission and stream start occur ONLY from a user-clicked native GUI button.
 * IMPORTANT: WebRTC P2P peers may see each other's public IP address.
 */
(function () {
  'use strict';
  if (window.PletzelVoice) return;
  const voice = {
    enabled:false,ready:false, muted:true,ptt:false,mode:'ptt',threshold:0.055,
    currentGain:1,othersGain:1,serverRange:48,localRange:48,yaw:0,
    status:'Voice disabled',url:'',token:'',ws:null,ctx:null,raw:null,rawTrack:null,
    outputTrack:null,outputStream:null,sourceNode:null,localGain:null,analyser:null,
    meter:0,transmitting:false,meterTimer:0,history:0,devices:[],speakers:[],
    micIndex:0,speakerIndex:0,peers:new Map(),peerNames:[],iceServers:[],
    lastError:'', userGestureSeen:false,
  };
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const trackState=()=>{
    const active=voice.enabled && voice.ready && !voice.muted &&
      (voice.mode==='ptt'?voice.ptt:voice.meter>voice.threshold||Date.now()-voice.history<180);
    if(voice.outputTrack) voice.outputTrack.enabled=!!active;
    voice.transmitting=!!active;
  };
  const send=message=>{
    const ws=voice.ws;
    if(ws?.readyState===WebSocket.OPEN && ws.bufferedAmount<256_000) ws.send(JSON.stringify(message));
  };
  function closePeer(id){
    const p=voice.peers.get(id);
    if(!p)return;
    voice.peers.delete(id);
    try{p.source?.disconnect()}catch{}
    try{p.panner?.disconnect()}catch{}
    try{p.volume?.disconnect()}catch{}
    try{p.pc.close()}catch{}
  }
  function dispose(reason='Voice disconnected') {
    voice.ready=false; voice.enabled=false;voice.muted=true;voice.ptt=false;
    voice.transmitting=false;
    if(voice.meterTimer){clearInterval(voice.meterTimer);voice.meterTimer=0;}
    for(const id of [...voice.peers.keys()])closePeer(id);
    const ws=voice.ws;voice.ws=null;
    if(ws){try{ws.onclose=null;ws.close()}catch{}}
    if(voice.outputTrack){try{voice.outputTrack.stop()}catch{}}
    if(voice.raw)for(const track of voice.raw.getTracks())track.stop();
    voice.raw=null;voice.rawTrack=null;voice.outputStream=null;voice.outputTrack=null;
    try{voice.sourceNode?.disconnect();voice.localGain?.disconnect()}catch{}
    voice.sourceNode=null;voice.localGain=null;voice.analyser=null;
    if(voice.ctx){voice.ctx.close().catch(()=>{});voice.ctx=null;}
    voice.status=reason;
  }
  function volumeAndPosition(p,dx,dy,dz){
    if(!p)return;
    const distance=Math.hypot(dx,dy,dz);
    const allow=distance<=Math.min(voice.localRange,voice.serverRange);
    if(p.panner){p.panner.positionX.value=dx;p.panner.positionY.value=dy;p.panner.positionZ.value=dz;}
    if(p.volume){p.volume.gain.value=allow?voice.othersGain:0;}
  }
  async function offer(peer){
    try{
      const desc=await peer.pc.createOffer();
      await peer.pc.setLocalDescription(desc);
      send({t:'signal',peer:peer.id,kind:'offer',payload:peer.pc.localDescription.toJSON()});
    }catch(e){voice.lastError='Offer failed: '+String(e).slice(0,110);closePeer(peer.id)}
  }
  function makePeer(id,name,initiator){
    if(voice.peers.has(id))return voice.peers.get(id);
    const pc=new RTCPeerConnection({iceServers:voice.iceServers});
    const peer={id,name,pc,source:null,panner:null,volume:null,candidates:[]};
    voice.peers.set(id,peer);
    pc.onicecandidate=e=>{if(e.candidate)send({t:'signal',peer:id,kind:'candidate',payload:e.candidate.toJSON()})};
    pc.onconnectionstatechange=()=>{
      if(['failed','closed'].includes(pc.connectionState))closePeer(id);
    };
    pc.ontrack=e=>{
      if(!voice.ctx || !e.streams[0])return;
      try{
        if(peer.source)peer.source.disconnect();
        peer.source=voice.ctx.createMediaStreamSource(e.streams[0]);
        peer.panner=voice.ctx.createPanner();
        peer.panner.panningModel='HRTF';
        peer.panner.distanceModel='linear';
        peer.panner.refDistance=2;
        peer.panner.maxDistance=Math.min(voice.serverRange,voice.localRange);
        peer.panner.rolloffFactor=1;
        peer.volume=voice.ctx.createGain();
        peer.volume.gain.value=voice.othersGain;
        peer.source.connect(peer.panner);peer.panner.connect(peer.volume);
        peer.volume.connect(voice.ctx.destination);
      }catch(error){voice.lastError='Speaker: '+String(error).slice(0,100)}
    };
    if(voice.outputTrack&&voice.outputStream)pc.addTrack(voice.outputTrack,voice.outputStream);
    if(initiator)queueMicrotask(()=>{if(voice.peers.get(id)===peer)offer(peer)});
    return peer;
  }
  async function signal(msg){
    let p=voice.peers.get(msg.from);if(!p)return;
    try{
      if(msg.kind==='offer'){
        await p.pc.setRemoteDescription(new RTCSessionDescription(msg.payload));
        const answer=await p.pc.createAnswer();
        await p.pc.setLocalDescription(answer);
        send({t:'signal',peer:p.id,kind:'answer',payload:p.pc.localDescription.toJSON()});
      } else if(msg.kind==='answer') {
        await p.pc.setRemoteDescription(new RTCSessionDescription(msg.payload));
      } else if(msg.kind==='candidate'){
        if(p.pc.remoteDescription)await p.pc.addIceCandidate(msg.payload);
        else p.candidates.push(msg.payload);
      }
      if(p.pc.remoteDescription){
        for(const c of p.candidates.splice(0))await p.pc.addIceCandidate(c);
      }
    }catch(e){voice.lastError='WebRTC signaling: '+String(e).slice(0,120)}
  }
  async function openMicrophone(deviceId){
    const requested={audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,
      channelCount:1,...(deviceId?{deviceId:{ideal:deviceId}}:{})},video:false};
    const raw=await navigator.mediaDevices.getUserMedia(requested);
    const old=voice.raw;const prev=voice.sourceNode;
    voice.raw=raw;voice.rawTrack=raw.getAudioTracks()[0];
    if(voice.ctx){
      if(prev)prev.disconnect();
      voice.sourceNode=voice.ctx.createMediaStreamSource(raw);
      voice.sourceNode.connect(voice.localGain);
      voice.sourceNode.connect(voice.analyser);
    }
    if(old)for(const t of old.getTracks())t.stop();
    voice.userGestureSeen=true;
  }
  async function enable(url,token){
    // Native Minecraft button click is the explicit permission gesture.
    if(voice.enabled)return 'Already enabled';
    if(typeof url!=='string'|| !/^(wss:\/\/[^\s/]+\/voice|ws:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?\/voice)$/.test(url)){
      voice.status='Use a secure wss://.../voice URL (localhost ws:// permitted)';return voice.status;
    }
    if(!token || !/^[-_A-Za-z0-9]{40,90}$/.test(token)){
      voice.status='Enter a fresh /pvoice token from your Minecraft server';return voice.status;
    }
    if(!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection){
      voice.status='WebRTC or microphone API unavailable in this browser';return voice.status;
    }
    if(!window.isSecureContext && !url.startsWith('ws://localhost') && !url.startsWith('ws://127.0.0.1')){
      voice.status='Microphone requires HTTPS or a localhost secure context';return voice.status;
    }
    try{
      const Ctx=window.AudioContext || window.webkitAudioContext;
      if(!Ctx)throw new Error('Web Audio unavailable');
      voice.ctx=new Ctx();await voice.ctx.resume();
      voice.analyser=voice.ctx.createAnalyser();voice.analyser.fftSize=1024;
      voice.localGain=voice.ctx.createGain();voice.localGain.gain.value=voice.currentGain;
      const out=voice.ctx.createMediaStreamDestination();voice.localGain.connect(out);
      voice.outputStream=out.stream;voice.outputTrack=out.stream.getAudioTracks()[0];
      voice.outputTrack.enabled=false;
      await openMicrophone();
      voice.enabled=true;voice.muted=true;voice.ready=false;voice.url=url;
      voice.status='Connecting to authenticated voice gateway...';
      const ws=new WebSocket(url);voice.ws=ws;
      ws.onopen=()=>send({t:'auth',token});
      ws.onmessage=e=>{
        let m;try{m=JSON.parse(e.data)}catch{return;}
        if(m.t==='welcome'){
          voice.ready=true;voice.serverRange=clamp(m.range||48,8,96);
          voice.localRange=Math.min(voice.localRange,voice.serverRange);
          voice.status='Connected (mic muted). WebRTC P2P may expose IP addresses.';
          trackState();
        }else if(m.t==='pair'){
          const p=makePeer(m.peer,m.name,m.initiator);
          volumeAndPosition(p,m.dx,m.dy,m.dz);
        }else if(m.t==='position'){
          volumeAndPosition(voice.peers.get(m.peer),m.dx,m.dy,m.dz);
        }else if(m.t==='unpair'){
          closePeer(m.peer);
        }else if(m.t==='signal'){signal(m);}
      };
      ws.onerror=()=>{voice.lastError='Voice WebSocket error; check TLS, server, and token'};
      ws.onclose=e=>{if(voice.ws===ws)dispose('Voice disconnected ('+e.code+'). '+(e.reason||'No compatible server'))};
      voice.meterTimer=setInterval(()=>{
        if(!voice.analyser)return;
        const data=new Float32Array(1024);voice.analyser.getFloatTimeDomainData(data);
        let sum=0;for(const s of data)sum+=s*s;
        voice.meter=Math.sqrt(sum/data.length);
        if(voice.meter>voice.threshold)voice.history=Date.now();
        trackState();
      },35);
      await refreshDevices();
      return voice.status;
    }catch(e){
      dispose('Mic denied or audio initialization failed: '+String(e.message||e).slice(0,130));
      return voice.status;
    }
  }
  async function refreshDevices(){
    try{
      const list=await navigator.mediaDevices.enumerateDevices();
      voice.devices=list.filter(x=>x.kind==='audioinput');
      voice.speakers=list.filter(x=>x.kind==='audiooutput');
    }catch{}
  }
  async function cycleMic(){
    if(!voice.enabled)return 'Enable voice first';
    await refreshDevices();if(voice.devices.length<2)return 'Only one microphone available';
    voice.micIndex=(voice.micIndex+1)%voice.devices.length;
    try{await openMicrophone(voice.devices[voice.micIndex].deviceId);
      return 'Microphone: '+(voice.devices[voice.micIndex].label||('Device '+(voice.micIndex+1)));
    }catch(e){return 'Could not switch microphone: '+String(e).slice(0,80)}
  }
  async function cycleSpeaker(){
    if(!voice.ctx)return 'Enable voice first';
    await refreshDevices();if(voice.speakers.length<2)return 'Only one output or selection unavailable';
    if(typeof voice.ctx.setSinkId!=='function')return 'Speaker selection is unsupported in this browser';
    voice.speakerIndex=(voice.speakerIndex+1)%voice.speakers.length;
    try{await voice.ctx.setSinkId(voice.speakers[voice.speakerIndex].deviceId);
      return 'Speaker: '+(voice.speakers[voice.speakerIndex].label||('Device '+(voice.speakerIndex+1)));
    }catch(e){return 'Output selection failed: '+String(e).slice(0,80)}
  }
  function setYaw(deg){
    voice.yaw=deg;if(!voice.ctx)return;
    const l=voice.ctx.listener;const a=deg*Math.PI/180;
    const fx=-Math.sin(a),fz=Math.cos(a);
    if(l.forwardX){l.forwardX.value=fx;l.forwardY.value=0;l.forwardZ.value=fz;}
    else if(l.setOrientation)l.setOrientation(fx,0,fz,0,1,0);
  }
  window.PletzelVoice={
    connect:(url,token)=>{enable(url,token)},
    disconnect:()=>dispose('Voice disabled (mic stopped)'),
    status:()=>voice.status+(voice.lastError?' | '+voice.lastError:'')+(voice.ready?' | nearby: '+voice.peers.size:''),
    connected:()=>voice.ready,
    transmitting:()=>voice.transmitting,
    enabled:()=>voice.enabled,
    muted:()=>voice.muted,
    mute:()=>{voice.muted=true;trackState();},
    unmute:()=>{if(voice.enabled&&voice.ready){voice.muted=false;trackState()}},
    mode:()=>voice.mode,
    setMode:mode=>{voice.mode=mode==='voice'?'voice':'ptt';trackState()},
    setPtt:down=>{voice.ptt=!!down;trackState()},
    sensitivity:v=>{voice.threshold=clamp(Number(v),0.01,0.3)},
    sensitivityValue:()=>voice.threshold,
    microphoneLevel:()=>voice.meter,
    setMicrophoneGain:g=>{voice.currentGain=clamp(Number(g),0,3);if(voice.localGain)voice.localGain.gain.value=voice.currentGain},
    setOtherVolume:g=>{voice.othersGain=clamp(Number(g),0,3);for(const p of voice.peers.values())if(p.volume)p.volume.gain.value=voice.othersGain},
    setMaxRange:d=>{voice.localRange=clamp(Number(d),8,voice.serverRange);
      for(const p of voice.peers.values())if(p.panner)p.panner.maxDistance=voice.localRange},
    range:()=>voice.serverRange,
    cycleMic:()=>{cycleMic().then(s=>voice.status=s)},
    cycleSpeaker:()=>{cycleSpeaker().then(s=>voice.status=s)},
    setYaw,
    microphoneName:()=>voice.devices[voice.micIndex]?.label||'Default microphone',
    speakerName:()=>voice.speakers[voice.speakerIndex]?.label||'Default output',
    test:()=>{
      voice.status='Mic test level: '+Math.round(voice.meter*1000)+' (no recording stored)';
    },
  };
  window.addEventListener('pagehide',()=>dispose());
})();
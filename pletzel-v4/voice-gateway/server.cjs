'use strict';
// Pletzel V4 browser voice bridge: original implementation, not a Simple Voice Chat protocol adapter.
// Signaling only; WebRTC encrypts and transports media separately. No media is recorded or relayed here.
const crypto = require('node:crypto');
const http = require('node:http');
const { WebSocketServer, WebSocket } = require('ws');

const KEY = process.env.VOICE_HMAC_SECRET;
const ADMIN = process.env.VOICE_POSITION_SECRET;
if (!KEY || Buffer.byteLength(KEY) < 32 || !ADMIN || Buffer.byteLength(ADMIN) < 32) {
  throw new Error('Set VOICE_HMAC_SECRET and VOICE_POSITION_SECRET to independent >=32-byte secrets');
}
const PORT = Number(process.env.PORT || 29454);
const RANGE = Math.max(1, Math.min(64, Number(process.env.VOICE_RANGE || 32)));
const TTL = 8000, MAX_SIGNAL = 128 * 1024;
const peers = new Map(), positions = new Map();
const b64 = data => Buffer.from(data).toString('base64url');
const hmac = input => crypto.createHmac('sha256', KEY).update(input).digest('base64url');
const eq = (a,b) => {
 const x=Buffer.from(a), y=Buffer.from(b);
 return x.length===y.length && crypto.timingSafeEqual(x,y);
};
function verify(ticket) {
 if(typeof ticket!=='string' || ticket.length>4096) return null;
 const parts=ticket.split('.');
 if(parts.length!==2 || !eq(hmac(parts[0]),parts[1])) return null;
 let x;
 try {x=JSON.parse(Buffer.from(parts[0],'base64url').toString('utf8'));} catch {return null;}
 if(x.aud!=='pletzel-voice-v1'||!/^[-\da-f]{36}$/i.test(x.uuid||'')||
    !/^[\w.-]{1,80}$/.test(x.session||'')||
    !Number.isSafeInteger(x.exp)||x.exp<=Date.now()||x.exp>Date.now()+120000) return null;
 return x;
}
function allowed(a,b) {
 if(a===b) return false;
 const x=positions.get(a),y=positions.get(b);
 if(!x||!y||Date.now()-x.updated>TTL||Date.now()-y.updated>TTL||
   x.world!==y.world||x.dimension!==y.dimension) return false;
 return ((x.x-y.x)**2+(x.y-y.y)**2+(x.z-y.z)**2)<=RANGE*RANGE;
}
function send(ws,obj) {
 if(ws?.readyState===WebSocket.OPEN && ws.bufferedAmount<MAX_SIGNAL) ws.send(JSON.stringify(obj));
}
function refresh() {
 for(const [id,ws] of peers) {
   const next=new Set();
   for(const other of peers.keys()) if(allowed(id,other)) next.add(other);
   const prior=ws.nearby||new Set();
   for(const other of next) if(!prior.has(other)) send(ws,{op:'near',peer:other});
   for(const other of prior) if(!next.has(other)) send(ws,{op:'far',peer:other});
   ws.nearby=next;
 }
}
const server=http.createServer((req,res)=>{
 if(req.url!=='/authoritative-positions'||req.method!=='POST') {
   res.writeHead(404);res.end();return;
 }
 if(!eq(req.headers.authorization||'', 'Bearer '+ADMIN)) {
   res.writeHead(401);res.end();return;
 }
 let raw='';
 req.on('data',data=>{
   raw+=data.toString();
   if(raw.length>262144) req.destroy();
 });
 req.on('end',()=>{
   try {
     const msg=JSON.parse(raw);
     if(!Array.isArray(msg.players)||msg.players.length>1000) throw Error('players');
     const next=new Map();
     for(const p of msg.players) {
       if(!/^[-\da-f]{36}$/i.test(p.uuid||'')||
          !/^[\w.-]{1,80}$/.test(p.world||'')||
          !/^[\w:.-]{1,80}$/.test(p.dimension||'')||
          ![p.x,p.y,p.z].every(v=>Number.isFinite(v)&&Math.abs(v)<3e7)) throw Error('position');
       next.set(p.uuid,{x:p.x,y:p.y,z:p.z,world:p.world,dimension:p.dimension,updated:Date.now()});
     }
     // Complete authoritative snapshot: omitted players cannot keep speaking.
     positions.clear();
     for(const [k,v] of next) positions.set(k,v);
     refresh();
     res.writeHead(204);res.end();
   } catch {res.writeHead(400);res.end();}
 });
});
const wss=new WebSocketServer({server,maxPayload:MAX_SIGNAL,perMessageDeflate:false});
wss.on('connection',ws=>{
 let id=null,session=null;
 const authTimeout=setTimeout(()=>ws.close(1008,'authentication required'),3000);
 ws.on('message',raw=>{
   let message;
   try {message=JSON.parse(raw.toString());} catch {ws.close(1003);return;}
   if(!id) {
     if(message?.op!=='auth') {ws.close(1008);return;}
     const ticket=verify(message.ticket);
     if(!ticket || !positions.has(ticket.uuid)) {ws.close(1008,'unauthorized');return;}
     id=ticket.uuid;session=ticket.session;
     const prev=peers.get(id);
     if(prev && prev!==ws) prev.close(1008,'replaced');
     peers.set(id,ws);clearTimeout(authTimeout);
     ws.nearby=new Set();
     send(ws,{op:'ready',self:id,range:RANGE});
     refresh();
     return;
   }
   if(!['offer','answer','ice'].includes(message?.op)||
      typeof message.to!=='string'||typeof message.data!=='string'||
      message.data.length>MAX_SIGNAL-512) {ws.close(1008,'invalid signaling');return;}
   // Client cannot claim coordinates, world, identity or another peer's authority.
   if(!allowed(id,message.to) || !peers.has(message.to)) return;
   send(peers.get(message.to),{op:message.op,from:id,data:message.data});
 });
 ws.on('close',()=>{
   clearTimeout(authTimeout);
   if(id&&peers.get(id)===ws) {
     peers.delete(id);refresh();
   }
 });
});
const interval=setInterval(refresh,1000);
server.listen(PORT,'127.0.0.1',()=>console.log('Pletzel voice signaling listening on localhost:'+PORT+' (TLS reverse proxy required)'));
function shutdown() {clearInterval(interval);for(const p of peers.values())p.close();wss.close();server.close();}
process.on('SIGTERM',shutdown);
module.exports={allowed,verify,server,wss,peers,positions,shutdown};

/**
 * Pletzel Voice — stand-alone signaling gateway. Independently developed;
 * NOT a Simple Voice Chat UDP bridge or an EaglerX protocol emulator.
 *
 * The Paper plugin is the sole authority for identity, player position,
 * dimension and session-token issuance. The gateway never trusts browser
 * coordinates. Media is DTLS-SRTP/Opus over direct WebRTC peers, not the WS.
 */
import http from 'node:http';
import crypto from 'node:crypto';
import { WebSocketServer, WebSocket } from 'ws';

const bind = process.env.VOICE_BIND || '127.0.0.1';
const port = Number(process.env.VOICE_PORT || 25580);
const adminKey = process.env.VOICE_ADMIN_SECRET || '';
if (adminKey.length < 32) throw new Error('VOICE_ADMIN_SECRET must be at least 32 characters');
const range = Math.max(8, Math.min(96, Number(process.env.VOICE_RANGE || 48)));
const rangeSquared = range * range;
// STUN/TURN configuration is supplied by the server operator. TURN-only mode
// prevents direct client-to-client host/server-reflexive ICE candidates.
const iceServers = JSON.parse(process.env.VOICE_ICE_SERVERS || '[{"urls":"stun:stun.l.google.com:19302"}]');
if (!Array.isArray(iceServers) || iceServers.length > 12 || iceServers.some(s =>
  !s || typeof s !== 'object' || typeof s.urls !== 'string' && !Array.isArray(s.urls))) {
  throw new Error('VOICE_ICE_SERVERS must be an array of WebRTC RTCIceServer objects');
}
const icePolicy = process.env.VOICE_TURN_ONLY === '1' ? 'relay' : 'all';
if (icePolicy === 'relay' && !iceServers.some(s => JSON.stringify(s.urls).includes('turn:') || JSON.stringify(s.urls).includes('turns:'))) {
  throw new Error('VOICE_TURN_ONLY requires a TURN server in VOICE_ICE_SERVERS');
}

const clients = new Map();
const grants = new Map();
let positions = new Map();
let updatedAt = 0;
let serverId = '';
let clock = Date.now;
const isUuid = s => typeof s === 'string' && /^[0-9a-f-]{32,36}$/i.test(s);
const within = (a, b) => a && b && a.world === b.world && (a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2<=rangeSquared;
const asJson = (socket, payload) => {
  if (socket.readyState === WebSocket.OPEN && socket.bufferedAmount < 512_000) {
    socket.send(JSON.stringify(payload));
  }
};
const goodKey = received => {
  const x=Buffer.from(typeof received === 'string' ? received : '');
  const y=Buffer.from(adminKey);
  return x.length===y.length && crypto.timingSafeEqual(x,y);
};
const pairKey = (a,b) => [a,b].sort().join(':');
const neighbors = (id, other) => positions.has(id) && positions.has(other) && within(positions.get(id),positions.get(other));
function closePeerPair(a,b) {
  if (!a.peers.delete(b.id)) return;
  b.peers.delete(a.id);
  asJson(a.socket,{t:'unpair',peer:b.id});
  asJson(b.socket,{t:'unpair',peer:a.id});
}
function synchronize() {
  const fresh=clock()-updatedAt<3500;
  for(const p of [...clients.values()]) {
    if(!fresh || !positions.has(p.id) || p.socket.readyState!==WebSocket.OPEN) {
      p.socket.close(4003,'Minecraft player left or server offline');
      continue;
    }
    for(const q of clients.values()) {
      if(p===q) continue;
      const permitted=neighbors(p.id,q.id);
      if(!permitted) {
        if(p.peers.has(q.id))closePeerPair(p,q);
        continue;
      }
      if(p.peers.has(q.id)) {
        if(p.id<q.id) {
          const a=positions.get(p.id),b=positions.get(q.id);
          asJson(p.socket,{t:'position',peer:q.id,dx:b.x-a.x,dy:b.y-a.y,dz:b.z-a.z});
          asJson(q.socket,{t:'position',peer:p.id,dx:a.x-b.x,dy:a.y-b.y,dz:a.z-b.z});
        }
        continue;
      }
      p.peers.add(q.id);q.peers.add(p.id);
      const initiator=p.id<q.id?p.id:q.id;
      const a=positions.get(p.id),b=positions.get(q.id);
      asJson(p.socket,{t:'pair',peer:q.id,name:b.name,initiator:p.id===initiator,
        dx:b.x-a.x,dy:b.y-a.y,dz:b.z-a.z});
      asJson(q.socket,{t:'pair',peer:p.id,name:a.name,initiator:q.id===initiator,
        dx:a.x-b.x,dy:a.y-b.y,dz:a.z-b.z});
    }
  }
}
async function readBody(req,max=65_536) {
  let str='';
  for await (const chunk of req) {
    str+=chunk.toString('utf8');
    if(str.length>max)throw new Error('Payload too large');
  }
  return JSON.parse(str||'{}');
}
const server=http.createServer(async(req,res)=>{
  if(req.url==='/health' && req.method==='GET') {
    res.writeHead(200,{'content-type':'application/json'});
    res.end(JSON.stringify({ok:true,connected:clients.size,serverFresh:clock()-updatedAt<3500,protocol:'pletzel-voice-v1'}));
    return;
  }
  if(!req.url?.startsWith('/admin/') || req.method!=='POST' || !goodKey(req.headers['x-pletzel-admin'])) {
    res.writeHead(404);res.end();return;
  }
  try {
    const data=await readBody(req);
    if(req.url==='/admin/snapshot') {
      if(!Array.isArray(data.players)||data.players.length>3000||typeof data.server!=='string'||data.server.length>80)throw new Error('Invalid snapshot');
      if(serverId && serverId!==data.server)throw new Error('Server ID mismatch');
      const next=new Map();
      for(const p of data.players){
        if(!isUuid(p.id)||typeof p.name!=='string'||p.name.length>32||typeof p.world!=='string'||p.world.length>100||
          ![p.x,p.y,p.z].every(v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<30_000_000))throw new Error('Bad player');
        next.set(p.id,{...p});
      }
      serverId=data.server;positions=next;updatedAt=clock();
      synchronize();
    } else if(req.url==='/admin/grant') {
      if(!isUuid(data.id) || !positions.has(data.id)||typeof data.token!=='string'||!/^[-_a-zA-Z0-9]{40,90}$/.test(data.token))throw new Error('Invalid grant');
      if(grants.size>2000)grants.clear();
      const hash=crypto.createHash('sha256').update(data.token).digest('hex');
      grants.set(hash,{id:data.id,expires:clock()+75_000});
    } else {res.writeHead(404);res.end();return;}
    res.writeHead(200,{'content-type':'application/json'});res.end('{"ok":true}');
  } catch(err) {
    res.writeHead(400,{'content-type':'application/json'});res.end(JSON.stringify({error:String(err.message).slice(0,150)}));
  }
});
const wss=new WebSocketServer({noServer:true,maxPayload:140_000,perMessageDeflate:false});
server.on('upgrade',(req,socket,head)=>{
  if(req.url!=='/voice'){socket.destroy();return;}
  wss.handleUpgrade(req,socket,head,ws=>wss.emit('connection',ws,req));
});
wss.on('connection',socket=>{
  let self=null;let count=0;let second=clock();
  const fail=(code,reason)=>{try{socket.close(code,reason)}catch{socket.terminate()}};
  socket.on('message',raw=>{
    if(socket.readyState!==WebSocket.OPEN)return;
    const now=clock();if(now-second>1000){second=now;count=0;}
    if(++count>50){fail(4008,'Rate limit');return;}
    let data;try{data=JSON.parse(raw.toString('utf8'))}catch{fail(4002,'Invalid JSON');return;}
    if(!self) {
      if(data?.t!=='auth'||typeof data.token!=='string'||data.token.length>100){fail(4001,'Authenticate first');return;}
      const hash=crypto.createHash('sha256').update(data.token).digest('hex');
      const grant=grants.get(hash);grants.delete(hash);
      if(!grant || grant.expires<now || !positions.has(grant.id) || now-updatedAt>3500){fail(4003,'Token invalid or expired');return;}
      if(clients.has(grant.id))clients.get(grant.id).socket.close(4004,'Another voice session started');
      self={id:grant.id,socket,peers:new Set()};clients.set(self.id,self);
      asJson(socket,{t:'welcome',id:self.id,range,server:serverId,iceServers,icePolicy});synchronize();return;
    }
    if(data?.t==='signal') {
      const peer=clients.get(data.peer);
      if(!peer||!self.peers.has(peer.id)||!neighbors(self.id,peer.id))return;
      if(!['offer','answer','candidate'].includes(data.kind)||typeof data.payload!=='object'||data.payload===null)return;
      const serialized=JSON.stringify(data.payload);
      if(serialized.length>110_000)return;
      asJson(peer.socket,{t:'signal',from:self.id,kind:data.kind,payload:data.payload});
    } else if(data?.t==='ping'){asJson(socket,{t:'pong'});}
  });
  socket.on('close',()=>{
    if(!self)return;
    if(clients.get(self.id)===self)clients.delete(self.id);
    for(const id of [...self.peers]){
      const peer=clients.get(id);
      if(peer)closePeerPair(self,peer);
    }
  });
  socket.on('error',()=>{});
});
const interval=setInterval(()=>{
  for(const [token,g] of grants)if(g.expires<clock())grants.delete(token);
  synchronize();
},500);interval.unref();
server.listen(port,bind,()=>console.log(`Pletzel voice signaling on ${bind}:${port}; range=${range}; WebRTC audio is P2P`));
export {server,wss,clients,positions,range};
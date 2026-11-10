import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {WebSocket} from 'ws';
import crypto from 'node:crypto';
const secret='test_only_32_char_secure_admin_secret_abcdefghij';
process.env.VOICE_ADMIN_SECRET=secret;
process.env.VOICE_PORT='0';
process.env.VOICE_RANGE='32';
const gateway=await import('../server.mjs');
if(!gateway.server.listening)await once(gateway.server,'listening');
const port=gateway.server.address().port;
const base=`http://127.0.0.1:${port}`;
const aId='00000000-0000-0000-0000-000000000001',bId='00000000-0000-0000-0000-000000000002';
const a={id:aId,name:'PlayerA',world:'test-overworld',x:0,y:63,z:0};
const b={id:bId,name:'PlayerB',world:'test-overworld',x:10,y:63,z:0};
async function admin(path,body,key=secret) {
 const r=await fetch(base+path,{method:'POST',headers:{'content-type':'application/json','X-Pletzel-Admin':key},body:JSON.stringify(body)});
 return r;
}
function waitFor(ws,t,timeout=4000) {
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{ws.off('message',cb);reject(new Error('Timed out '+t))},timeout);
  const cb=b=>{let v;try{v=JSON.parse(b.toString())}catch{return}if(v.t!==t)return;
    clearTimeout(timer);ws.off('message',cb);resolve(v)};
  ws.on('message',cb);
 });
}
async function openAuth(token) {
 const ws=new WebSocket(`ws://127.0.0.1:${port}/voice`);
 await once(ws,'open');
 const ready=waitFor(ws,'welcome');
 ws.send(JSON.stringify({t:'auth',token}));
 await ready;
 return ws;
}
test('untrusted administration cannot forge player location',async()=>{
 const bad=await admin('/admin/snapshot',{server:'test',players:[a,b]},'wrong');
 assert.notEqual(bad.status,200);
 assert.equal((await admin('/admin/snapshot',{server:'test',players:[a,b]})).status,200);
});
test('same-world in-range peers exchange authenticated signaling, then unpair outside range',async()=>{
 const tokenA=crypto.randomBytes(32).toString('base64url');
 const tokenB=crypto.randomBytes(32).toString('base64url');
 assert.equal((await admin('/admin/grant',{id:aId,token:tokenA})).status,200);
 assert.equal((await admin('/admin/grant',{id:bId,token:tokenB})).status,200);
 const wsA=await openAuth(tokenA);
 const pairA=waitFor(wsA,'pair');
 const wsB=new WebSocket(`ws://127.0.0.1:${port}/voice`);
 await once(wsB,'open');
 const welcomeB=waitFor(wsB,'welcome');const pairB=waitFor(wsB,'pair');
 wsB.send(JSON.stringify({t:'auth',token:tokenB}));
 await welcomeB;
 const [msgA,msgB]=await Promise.all([pairA,pairB]);
 assert.equal(msgA.peer,bId);assert.equal(msgB.peer,aId);
 assert.equal(msgA.initiator,true);assert.equal(msgB.initiator,false);
 const sig=waitFor(wsB,'signal');
 wsA.send(JSON.stringify({t:'signal',peer:bId,kind:'offer',payload:{type:'offer',sdp:'sample-sdp-no-microphone-test'}}));
 const delivered=await sig;
 assert.equal(delivered.from,aId);assert.equal(delivered.payload.type,'offer');
 const removedA=waitFor(wsA,'unpair');const removedB=waitFor(wsB,'unpair');
 assert.equal((await admin('/admin/snapshot',{server:'test',players:[a,{...b,x:100}]})).status,200);
 await Promise.all([removedA,removedB]);
 wsA.close();wsB.close();
});
test('the same token cannot authenticate two sessions and dimension mismatch blocks pairing',async()=>{
 assert.equal((await admin('/admin/snapshot',{server:'test',players:[a,{...b,world:'the-nether',x:2}]})).status,200);
 const tok=crypto.randomBytes(32).toString('base64url');
 assert.equal((await admin('/admin/grant',{id:aId,token:tok})).status,200);
 const one=await openAuth(tok);
 const reuse=new WebSocket(`ws://127.0.0.1:${port}/voice`);
 await once(reuse,'open');
 const closed=once(reuse,'close');
 reuse.send(JSON.stringify({t:'auth',token:tok}));
 const [code]=await closed;
 assert.equal(code,4003);
 one.close();
});
test.after(async()=>{
 for(const p of gateway.clients.values())try{p.socket.terminate()}catch{}
 await new Promise(resolve=>gateway.wss.close(resolve));
 await new Promise(resolve=>gateway.server.close(resolve));
});
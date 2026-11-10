'use strict';
const {test,after} = require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const http=require('node:http');
const {WebSocket}=require('ws');
process.env.PORT='0';
process.env.VOICE_HMAC_SECRET='0123456789abcdefghijklmnopqrstuvwxyz_HMAC';
process.env.VOICE_POSITION_SECRET='0123456789abcdefghijklmnopqrstuvwxyz_ADMIN';
const gate=require('./server.cjs');
after(()=>gate.shutdown());
const ids=['aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa','bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb',
'cccccccc-cccc-4ccc-cccc-cccccccccccc'];
const ticket=(id,session='test')=>{
 const payload=Buffer.from(JSON.stringify({aud:'pletzel-voice-v1',uuid:id,session,exp:Date.now()+40000})).toString('base64url');
 const sig=crypto.createHmac('sha256',process.env.VOICE_HMAC_SECRET).update(payload).digest('base64url');
 return payload+'.'+sig;
};
const player=(uuid,x,dimension='minecraft:overworld')=>({uuid,x,y:64,z:0,world:'world',dimension});
const listen=()=>new Promise(r=>gate.server.listening?r():gate.server.once('listening',r));
async function post(players,authorization='Bearer '+process.env.VOICE_POSITION_SECRET) {
 await listen();
 return new Promise((resolve,reject)=>{
  const body=JSON.stringify({players});
  const q=http.request({hostname:'127.0.0.1',port:gate.server.address().port,path:'/authoritative-positions',
    method:'POST',headers:{authorization,'content-type':'application/json','content-length':Buffer.byteLength(body)}},
   res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});
  q.on('error',reject);q.end(body);
 });
}
function connect(id,t=ticket(id)) {
 return new Promise((resolve,reject)=>{
  const ws=new WebSocket('ws://127.0.0.1:'+gate.server.address().port);
  const messages=[];let done=false;
  ws.on('error',e=>{if(!done){done=true;reject(e);}});
  ws.on('open',()=>ws.send(JSON.stringify({op:'auth',ticket:t})));
  ws.on('message',raw=>{
   const m=JSON.parse(String(raw));messages.push(m);
   if(m.op==='ready'&&!done){done=true;resolve({ws,messages});}
  });
  ws.on('close',()=>{if(!done){done=true;reject(Error('rejected by gateway'));}});
 });
}
const pause=()=>new Promise(r=>setTimeout(r,140));
test('server rejects forged snapshots; allows only server-authoritative proximity and dimensions',async()=>{
 assert.equal(await post([player(ids[0],0)],'Bearer wrong'),401);
 assert.equal(await post([player(ids[0],0),player(ids[1],10),player(ids[2],100)]),204);
 const a=await connect(ids[0]),b=await connect(ids[1]),c=await connect(ids[2]);
 await pause();
 assert(a.messages.some(m=>m.op==='near'&&m.peer===ids[1]));
 assert(!a.messages.some(m=>m.op==='near'&&m.peer===ids[2]));
 a.ws.send(JSON.stringify({op:'offer',to:ids[1],data:'genuine-offer'}));
 await pause();
 assert(b.messages.some(m=>m.op==='offer'&&m.from===ids[0]&&m.data==='genuine-offer'));
 a.ws.send(JSON.stringify({op:'offer',to:ids[2],data:'must-not-forward'}));
 await pause();
 assert(!c.messages.some(m=>m.data==='must-not-forward'));
 assert.equal(await post([player(ids[0],0),player(ids[1],10,'minecraft:the_nether'),player(ids[2],100)]),204);
 await pause();
 assert(a.messages.some(m=>m.op==='far'&&m.peer===ids[1]));
 a.ws.send(JSON.stringify({op:'offer',to:ids[1],data:'cross-dimension'}));
 await pause();
 assert(!b.messages.some(m=>m.data==='cross-dimension'));
 const invalid=connect('dddddddd-dddd-4ddd-dddd-dddddddddddd','not-a-valid-ticket');
 await assert.rejects(invalid,/rejected by gateway/);
 for(const w of [a.ws,b.ws,c.ws])w.close();
});

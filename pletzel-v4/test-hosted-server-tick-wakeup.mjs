#!/usr/bin/env node
// Test the actual @JSBody method extracted from the pinned, source-patched Java
// platform class. No simulated Java code and NO game compilation.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';

const sourcePath=process.argv[2];
assert(sourcePath,"pass patched platform-teavm ServerPlatformSingleplayer.java");
const source=fs.readFileSync(sourcePath,'utf8');
const needle='@JSBody(params = { "handler", "millis" }, script = ';
const start=source.indexOf(needle);
assert(start>=0,"native tick @JSBody not found");
const end=source.indexOf('private static native void scheduleTickContinue(',start);
assert(end>start,"native signature missing");
const body=source.slice(start+needle.length,end);
const parts=[...body.matchAll(/"((?:\\.|[^"\\])*)"/g)].map(m=>JSON.parse('"'+m[1]+'"'));
const js=parts.join('');
assert(js.includes('setTimeout') && js.includes('scheduler') && js.includes('done'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function scenario(name,scheduler,expectedDelayMax,expectedDelayMin=0){
 let wakeCount=0;const started=Date.now();
 const context={globalThis:{scheduler,setTimeout,clearTimeout},handler:()=>{wakeCount++;},
     millis:10};
 vm.runInNewContext("(function(){"+js+"})()",context,{timeout:2000});
 await sleep(165);
 const elapsed=Date.now()-started;
 assert.equal(wakeCount,1,name+' must wake exactly once');
 assert(elapsed<=300 && elapsed>=expectedDelayMin,name+' wake timing incorrect');
 console.log('PASS',name,'one and only one callback, elapsed',elapsed,'ms');
}
await scenario('normal priority postTask', {postTask:fn=>{setTimeout(fn,10);return Promise.resolve()}},300);
await scenario('silently never-resolving postTask', {postTask:()=>new Promise(()=>{})},300);
await scenario('rejected postTask', {postTask:()=>Promise.reject(new Error('simulated scheduling reject'))},300);
await scenario('no scheduler support', null,300);
console.log('ALL HOSTED SERVER TICK WAKE CHECKS PASS');

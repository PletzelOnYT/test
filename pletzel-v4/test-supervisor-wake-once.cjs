/* Regression test against the ACTUAL Java @JSBody source after patching.
 * No game binary is compiled. Simulate browser scheduler task rejection/loss,
 * timer loss, early supervisor polling, overdue supervisor delivery, and late
 * competing callbacks. Exactly one native TeaVM continuation is required.
 */
'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const file = process.argv[2];
if (!file) throw Error('usage: node test-supervisor-wake-once.cjs <patched ServerPlatformSingleplayer.java>');
const java = fs.readFileSync(file,'utf8');
function nativeJs(marker, terminator) {
  const start = java.indexOf(marker);
  if (start < 0) throw Error('Missing native @JSBody '+marker);
  const end = java.indexOf(terminator,start);
  if (end < start) throw Error('No end for '+marker);
  const body = java.slice(start,end);
  const assignment=body.indexOf('script = ');
  if (assignment<0) throw Error('Missing script attr '+marker);
  const quoted=[...body.slice(assignment).matchAll(/"(?:\\.|[^"\\])*"/g)].map(m=>JSON.parse(m[0]));
  return quoted.join('');
}
const tickBody=nativeJs('@JSBody(params = { "handler", "millis" }','private static native void scheduleTickContinue');
const pumpBody=nativeJs('@JSBody(params = {}, script = "var w = globalThis.__pletzelTickWake26;"','public static native void recoverOverdueServerTick');
const schedule=new Function('handler','millis',tickBody);
const pump=new Function(pumpBody);
const realTimeout=globalThis.setTimeout, realClear=globalThis.clearTimeout;
const realScheduler=globalThis.scheduler;
let timers=[], jobs=[], completions=0;
function reset() {
  timers=[];jobs=[];completions=0;
  globalThis.__pletzelTickWake26=null;
  globalThis.__pletzelSupervisorWakeCount26=0;
  globalThis.setTimeout=(fn,d)=>{timers.push({fn,d});return timers.length};
  globalThis.clearTimeout=(id)=>{};
}
try {
  // Normal scheduler callback, then late timeout and supervisor: ONE continuation.
  reset();globalThis.scheduler={postTask:(fn,opts)=>{jobs.push(fn);return new Promise(()=>{});}};
  schedule(()=>completions++,10);
  assert.equal(completions,0);
  jobs[0](); assert.equal(completions,1);
  for(const timer of timers) timer.fn();
  pump();
  assert.equal(completions,1);
  assert.equal(globalThis.__pletzelTickWake26,null);
  // No scheduler: timer branch still completes once.
  reset();delete globalThis.scheduler;
  schedule(()=>completions++,0);
  assert.equal(timers.length,2);
  timers[0].fn();timers[1].fn();
  assert.equal(completions,1);
  // Pending scheduler and both timers lost: the LIVE supervisor rescues AFTER real deadline.
  reset();globalThis.scheduler={postTask:(fn)=>{jobs.push(fn);return new Promise(()=>{});}};
  schedule(()=>completions++,0);
  pump();
  assert.equal(completions,0,'must not advance server tick before its real due time');
  const until=performance.now()+164;
  while(performance.now()<until){}  // deterministic failure simulation only
  pump();
  assert.equal(completions,1,'the live supervisor should resume exactly once');
  assert.equal(globalThis.__pletzelSupervisorWakeCount26,1);
  jobs[0]();
  for(const timer of timers) timer.fn();
  assert.equal(completions,1,'late promises/timeouts must never resume a green thread twice');
  // New tick registers new callback and does not reuse completed prior one.
  schedule(()=>completions++,0);
  timers.at(-1).fn();
  assert.equal(completions,2);
  console.log('PASS: native @JSBody one-shot tick callback, on-time scheduling, fallback, lost callbacks recovered by supervisor, no premature or duplicate ticks');
} finally {
  globalThis.setTimeout=realTimeout;globalThis.clearTimeout=realClear;
  if (realScheduler === undefined) delete globalThis.scheduler; else globalThis.scheduler=realScheduler;
  delete globalThis.__pletzelTickWake26;
}

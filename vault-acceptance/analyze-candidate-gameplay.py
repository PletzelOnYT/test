#!/usr/bin/env python3
"""Evidence-only metrics for immutable Pletzel V4 candidates.

Script success is NOT gameplay acceptance; report explicitly notes which
assertions remain visual/manual and why.
"""
from pathlib import Path
import json, math, re, statistics, os
from evidence_metrics import extract

test=os.environ.get("TEST_KIND","unknown")
variant=os.environ.get("VARIANT","unknown")
files={
 "survival":"singleplayer-pressure-evidence/events.json",
 "onecpu":"singleplayer-pressure-evidence/events.json",
 "teleport":"cheats-entity-evidence/all-events.json",
 "remote":"cheats-entity-evidence/all-events.json",
 "vault":"cheats-entity-evidence/all-events.json",
 "chicken":"cheats-entity-evidence/all-events.json",
 "lifecycle":"lifecycle-evidence/records.json",
 "schematica":"inworld-schematic-evidence/full-console.json",
}
path=Path(files.get(test,""))
events=[]
if path.is_file():
 obj=json.loads(path.read_text())
 events=obj if isinstance(obj,list) else obj.get("events",[])
def key(e):return e.get("t",e.get("at",0))
heart=[]; waits=[]; packet_peaks=[]; packet_ages=[]; per_tick=[]; crashes=[]; chicken=[]; chunk=[]; times=[]
for e in events:
 s=e.get("text","")
 t=key(e)
 if "[EagPerfHeartbeat]" in s:
  m=re.search(r"lastTick=(\d+)",s)
  if m:heart.append((float(t),int(m.group(1))))
  m=re.search(r"sinceCompleted=(\d+)",s)
  if m:times.append(int(m.group(1)))
 if "[EagPerfChunkWait]" in s:
  m=re.search(r"elapsed=(\d+)ms",s)
  waits.append(dict(t=t,ms=int(m.group(1)) if m else None,source=s[:1100]))
 if "[EagPerfClient] singleplayer inbound pumps=" in s:
  m=re.search(r"queue=\d+/(\d+) oldest=[\d.]+/([\d.]+)ms",s)
  if m:packet_peaks.append(int(m.group(1)));packet_ages.append(float(m.group(2)))
 if "[EagPerf] entity type=minecraft:chicken" in s:chicken.append(s[:600])
 if "[EagPerfClient] chunk packets applied=" in s:chunk.append(s[:700])
 if e.get("kind",e.get("type")) in ("pageerror","error","test-exception","crash"):crashes.append(s[:1200])
for (ta,a),(tb,b) in zip(heart,heart[1:]):
 if tb>ta and ta>=0:
  per_tick.append((b-a)/(tb-ta))
def percentile(x,q):
 if not x:return None
 x=sorted(x);i=(len(x)-1)*q;lo=int(i);hi=min(lo+1,len(x)-1)
 return round(x[lo]*(hi-i)+x[hi]*(i-lo),3)
def roundf(x):return round(x,3) if x is not None else None
r={
 "candidate":variant,"test":test,"tested_binary_sha256":None,
 "source_events":len(events),
 "heartbeat_count":len(heart),"tick_start":heart[0] if heart else None,"tick_end":heart[-1] if heart else None,
 "tps_mean_intervals":roundf(statistics.mean(per_tick)) if per_tick else None,
 "tps_median":roundf(statistics.median(per_tick)) if per_tick else None,
 "tps_p05":percentile(per_tick,0.05),"tps_lowest":roundf(min(per_tick)) if per_tick else None,
 "zero_or_two_tps_intervals":sum(x<=2 for x in per_tick),
 "longest_since_completed_ms":max(times) if times else None,
 "chunk_full_sync_wait_max_ms":max((w["ms"] for w in waits if w["ms"] is not None),default=None),
 "chunk_wait_count":len(waits),"chunk_wait_examples":sorted(waits,key=lambda w:w["ms"] or 0,reverse=True)[:7],
 "inbound_queue_highwater":max(packet_peaks,default=None),
 "inbound_oldest_ms_highwater":max(packet_ages,default=None),
 "chunk_apply_reports":chunk[-10:],"chicken_server_tick_reports":len(chicken),
 "browser_errors":crashes[-15:],
 "manual_acceptance_requirements":["Verify screenshots of terrain / F3 position / chicken health and knockback / save-reopen / Schematica, as applicable","A green workflow run alone is NOT gameplay acceptance"],
 "status":"AWAITING_EVIDENCE_REVIEW"
}
# Canonical native measurement decoder is shared with the acceptance gate.
native_evidence=extract(events)
r["native_evidence"]=native_evidence
r["longest_since_completed_ms"]=native_evidence["max_since_completed_heartbeat_ms"]
r["chunk_full_sync_wait_max_ms"]=native_evidence["max_any_sync_chunk_wait_ms"] if native_evidence["chunk_wait_count"] else None
idpath=Path("candidate-identity.json")
if idpath.exists():r["tested_binary_sha256"]=json.loads(idpath.read_text()).get("html_sha256")
p=Path("candidate-metrics.json");p.write_text(json.dumps(r,indent=2))
print("CANDIDATE_METRICS",json.dumps({k:v for k,v in r.items() if k not in ["chunk_wait_examples","chunk_apply_reports","manual_acceptance_requirements"]}))

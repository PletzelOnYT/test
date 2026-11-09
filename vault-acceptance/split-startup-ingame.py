#!/usr/bin/env python3
"""Separate genuine initialization from sustained gameplay in exact browser logs."""
from pathlib import Path
import os,json,re,statistics
kind=os.getenv("TEST_KIND","unknown")
eventfile=Path("singleplayer-pressure-evidence/events.json") if kind in ("survival","onecpu") else Path("cheats-entity-evidence/all-events.json")
out=Path("startup-vs-ingame.json")
if not eventfile.exists():
    out.write_text(json.dumps({"test":kind,"status":"MISSING_RAW_EVENTS"},indent=2))
    raise SystemExit("No raw browser events: "+str(eventfile))
events=json.loads(eventfile.read_text())
hearts=[];waits=[]
for event in events:
    t=event.get("t",event.get("at",0))
    s=event.get("text","")
    if "[EagPerfHeartbeat]" in s:
        m=re.search(r"\blastTick=(\d+)\b",s)
        age=re.search(r"\bsinceCompleted=(\d+)ms\b",s)
        if not m or not age:raise SystemExit("Malformed native heartbeat: "+s[:400])
        hearts.append((float(t),int(m.group(1)),int(age.group(1))))
    if "[EagPerfChunkWait]" in s:
        m=re.search(r"\belapsed=(\d+)ms\b",s)
        if not m:raise SystemExit("Malformed FULL sync wait: "+s[:400])
        waits.append({"at":float(t),"milliseconds":int(m.group(1)),"source":s[:500]})
if not hearts:raise SystemExit("Missing server tick heartbeat telemetry")
first_live=next((x[0] for x in hearts if x[1]>0),None)
if first_live is None:raise SystemExit("No server tick completed")
start_heart=[h for h in hearts if h[0]<first_live]
live_heart=[h for h in hearts if h[0]>=first_live]
init_wait=[w for w in waits if w["at"]<first_live]
inworld_wait=[w for w in waits if w["at"]>=first_live]
rates=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(live_heart,live_heart[1:]) if b[0]>a[0]]
report={
    "kind":kind,
    "status":"MEASURED_NOT_ACCEPTED",
    "startup_first_completed_tick_at_seconds":first_live,
    "startup_max_since_completed_ms":max((h[2] for h in start_heart),default=None),
    "startup_max_sync_chunk_wait_ms":max((w["milliseconds"] for w in init_wait),default=0),
    "startup_waits":init_wait,
    "gameplay_heartbeats":len(live_heart),
    "gameplay_ticks_advanced":live_heart[-1][1]-live_heart[0][1],
    "gameplay_wallclock_average_tps":(live_heart[-1][1]-live_heart[0][1])/(live_heart[-1][0]-live_heart[0][0]) if len(live_heart)>1 and live_heart[-1][0]>live_heart[0][0] else None,
    "gameplay_lowest_interval_tps":min(rates,default=None),
    "gameplay_max_since_completed_ms":max((h[2] for h in live_heart),default=None),
    "gameplay_max_sync_chunk_wait_ms":max((w["milliseconds"] for w in inworld_wait),default=0),
    "gameplay_waits":inworld_wait,
    "warning":"This report is diagnostic only; strict-evidence-gate.py owns acceptance."
}
out.write_text(json.dumps(report,indent=2))
print("STARTUP_VS_INGAME",json.dumps({k:v for k,v in report.items() if k not in ("startup_waits","gameplay_waits","warning")}))

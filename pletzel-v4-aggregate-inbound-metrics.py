#!/usr/bin/env python3
"""Extract measured singleplayer server TPS and FIFO packet-backlog evidence.

Both variants run the same byte-immutable browser workload; do not equate
workflow pass with gameplay acceptance. This file only reads stress-test JSON.
"""
import json,re,statistics,sys
from pathlib import Path
root=Path("singleplayer-pressure-evidence")
result=json.loads((root/"result.json").read_text())
events=json.loads((root/"events.json").read_text())
regex=re.compile(
    r"\[EagPerfClient\] singleplayer inbound pumps=(\d+) frames=(\d+) bytes=(\d+) "
    r"decode avg/max=([\d.]+)/([\d.]+)ms queue=(\d+)/(\d+) "
    r"oldest=([\d.]+)/([\d.]+)ms")
points=[]
for e in events:
    m=regex.search(e.get("text",""))
    if m:
        vals=list(map(float,m.groups()))
        points.append({"at_s":e.get("t",0),"decoded_frames":vals[1],
                       "pending":int(vals[5]),"max_pending_interval":int(vals[6]),
                       "oldest_ms":vals[7],"max_oldest_interval_ms":vals[8],
                       "avg_decode_ms":vals[3],"max_decode_ms":vals[4]})
live=[m for m in result.get("readings",[]) if m.get("lastTick") is not None]
intervals=[]
for left,right in zip(live,live[1:]):
    duration=right.get("elapsed",0)-left.get("elapsed",0)
    if duration>0:
        intervals.append((right["lastTick"]-left["lastTick"])/duration)
summary={
  "first_world_tick_at_s":result.get("first_world_tick_at_s"),
  "actual_tick_rate":result.get("actual_tick_rate"),
  "tick_delta":result.get("tick_after_spawn"),
  "median_interval_tps":round(statistics.median(intervals),2) if intervals else None,
  "min_interval_tps":round(min(intervals),2) if intervals else None,
  "max_since_completed_ms":result.get("max_since_completed_ms"),
  "client_queue_sample_count":len(points),
  "client_queue_median":statistics.median([p["pending"] for p in points]) if points else None,
  "client_queue_max":max((p["max_pending_interval"] for p in points),default=None),
  "client_oldest_frame_max_ms":max((p["max_oldest_interval_ms"] for p in points),default=None),
  "client_oldest_frame_max_after_180s_ms":max((p["max_oldest_interval_ms"] for p in points if p["at_s"]>=180),default=None),
  "worker_errors":sum(1 for e in result.get("errors",[]) if e.get("kind")=="pageerror"),
  "client_queue_time_series":points
}
(root/"queue-summary.json").write_text(json.dumps(summary,indent=2))
print("QUEUE_METRICS",json.dumps({k:v for k,v in summary.items() if k!="client_queue_time_series"}),flush=True)
if not points:
    print("Warning: client inbound debug logs absent; queue behavior UNVERIFIED",flush=True)

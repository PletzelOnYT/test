#!/usr/bin/env python3
"""Field-specific strict regression classifier for recorded browser events.

This cannot prove the exact Mac saved world is reproduced. It can reject a
concrete recurrence: a 500ms+ synchronous STRUCTURE_STARTS request inside the
connection/player-processing server tick. Report UNKNOWN when no such lookup
was exercised; never treat absence as proof that the root cause is solved.
"""
import json,re,os
from pathlib import Path
kind=os.environ["TEST_KIND"]
paths=[
 Path("singleplayer-pressure-evidence/events.json"),
 Path("cheats-entity-evidence/all-events.json"),
 Path("inworld-schematic-evidence/results.json")
]
events=[]
for path in paths:
 if not path.exists():continue
 data=json.loads(path.read_text())
 if isinstance(data,list):events.extend(data)
 elif isinstance(data,dict):events.extend(data.get("errors",[]))
sync=[]
started=[]
for e in events:
 line=str(e.get("text",""))
 if ("[PletzelActiveChunkWait]" in line
    and "minecraft:structure_starts" in line
    and "phase=connection" in line):
  m=re.search(r"waiting=(\d+)ms",line)
  if m:started.append(int(m.group(1)))
 if "[EagPerfChunkWait]" in line and "minecraft:structure_starts" in line and "phase=connection" in line:
  m=re.search(r"elapsed=(\d+)ms",line)
  if m:sync.append(int(m.group(1)))
 out={
 "test":kind,
 "source":"actual game native console telemetry",
 "last_reported_structure_starts_active_wait_ms":max(started,default=None),
 "max_structure_starts_sync_wait_ms":max(sync,default=None),
 "field_regression_reproduced":any(x>=500 for x in sync+started),
 "root_cause_reexercised":bool(sync or started),
 "classification":"GAMEPLAY_FAILURE" if any(x>=500 for x in sync+started) else
                  ("LOOKUP_EXERCISED_NO_LONG_STALL" if sync or started else "NOT_EXERCISED_UNKNOWN"),
 "manual_mac_saved_world_validation_required":True,
 }
Path("field-structure-starts-regression.json").write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
if out["field_regression_reproduced"]:
 raise SystemExit("GAMEPLAY_FAILURE: synchronous player STRUCTURE_STARTS >=500ms")

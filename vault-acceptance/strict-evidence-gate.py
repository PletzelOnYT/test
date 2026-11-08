#!/usr/bin/env python3
"""Fail a Chromium acceptance job on explicitly measured gameplay regressions.
A zero exit does not replace visual review of terrain or hologram.
"""
from pathlib import Path
import json,re,os

kind=os.environ["TEST_KIND"]
out=Path("strict-evidence-gate.json")
evidence_dir=Path("cheats-entity-evidence")
p=Path("singleplayer-pressure-evidence/events.json") if kind in ("survival","onecpu") else evidence_dir/"all-events.json"
events=json.loads(p.read_text()) if p.exists() else []
faults=[];details={"test":kind,"events":len(events)}
def fail(reason):faults.append(reason)
def text(e):return e.get("text","")
logtext="\n".join(map(text,events))
def numbers(pat):
 return [(float(e.get("t",e.get("at",0))),int(m.group(1))) for e in events if (m:=re.search(pat,text(e)))]
if kind in ("survival","onecpu"):
 if len(events)<100:fail("missing substantial raw server and browser telemetry")
 tick=numbers(r"\[EagPerfHeartbeat\].*?\blastTick=(\d+)")
 if len(tick)<12:fail("fewer than 12 observed server tick heartbeats")
 if len(tick)>=2:
  duration=tick[-1][0]-tick[0][0];tps=(tick[-1][1]-tick[0][1])/duration if duration>0 else 0
  details["wallclock_average_tps"]=round(tps,3)
  if tps < (10 if kind=="onecpu" else 17):fail(f"measured TPS below acceptance threshold: {tps:.2f}")
 waits=[]
 for e in events:
  t=text(e)
  if "[EagPerfChunkWait]" not in t:continue
  m=re.search(r"elapsed=(\d+)ms",t)
  if m:waits.append((int(m.group(1)),t))
 details["max_vault_sync_wait_ms"]=max((v for v,s in waits if "callerType=minecraft:vault" in s),default=0)
 details["max_active_blockentity_sync_wait_ms"]=max((v for v,s in waits if "phase=levels.blockEntities" in s),default=0)
 if details["max_vault_sync_wait_ms"]>=1000:fail("VAULT still blocks integrated server for >=1000ms")
 if details["max_active_blockentity_sync_wait_ms"]>=2000:fail("block entity still synchronously blocks a server tick >=2000ms")
 if any(e.get("kind")=="pageerror" for e in events):fail("browser JavaScript pageerror")
elif kind=="remote":
 result=json.loads((evidence_dir/"result.json").read_text())
 details["actual_authoritative_player_x_samples"]=result.get("server_player_x_samples_scaled100")
 details["teleport_future_trace_count"]=len(result.get("traceEvents",[]))
 if not result.get("destination_x_reached"):fail("server authoritative X coordinate never reached x=96.5")
 # F3 client XYZ, chunk visibility, sky/terrain completeness require screenshots.
 if len(result.get("screenshots",[]))<10:fail("insufficient interval screenshots to assess terrain")
 if "[PletzelTeleportTrace] QUEUED" not in logtext:fail("compiled diagnostic module did not log start of remote FULL request")
elif kind=="chicken":
 attack=[e for e in events if "[EagActionTrace]" in text(e)
         and "action=attack" in text(e) and "stage=handler_complete" in text(e)
         and "accepted=true" in text(e) and "healthBefore=4.0" in text(e)
         and "healthAfter=3.0" in text(e)]
 details["server_accepted_mouse_attacks"]=len(attack)
 if not attack:fail("no authoritative real mouse attack reducing chicken HP 4.0→3.0")
 else:
  at=float(attack[0]["t"])
  z=numbers(r"Pos\[2\] on Chicken after scale factor of 100\.00 is (-?\d+)")
  before=[v for t,v in z if t<at]
  after=[v for t,v in z if t>at]
  displacement=abs(after[0]-before[-1])/100 if before and after else 0
  details["mouse_hit_knockback_blocks"]=round(displacement,2)
  if displacement < 0.25:fail("server-authoritative chicken knockback less than 0.25 blocks")
elif kind=="vault":
 assertions=json.loads((evidence_dir/"vault-assertions.json").read_text())
 details["vault_active_evidence"]=assertions.get("vault_active_evidence",False)
 details["unlocking_chat_event"]="PLETZEL_VAULT_UNLOCKING" in logtext
 details["ejecting_chat_event"]="PLETZEL_VAULT_EJECTING" in logtext
 details["reward_item_event"]="PLETZEL_VAULT_DROPPED_ITEM" in logtext
 if not assertions.get("vault_active_evidence"):fail("Vault failed to activate near a real player")
 if not (details["unlocking_chat_event"] or details["ejecting_chat_event"]):
  fail("Vault did not enter expected unlocking/ejecting state following trial-key rightclick")
 if not details["reward_item_event"]:fail("Vault reward item not observed by vanilla item-entity query")
 waits=[(int(m.group(1)),text(e)) for e in events if "[EagPerfChunkWait]" in text(e)
        if (m:=re.search(r"elapsed=(\d+)ms",text(e)))]
 details["max_vault_sync_wait_ms"]=max((v for v,s in waits if "callerType=minecraft:vault" in s),default=0)
 if details["max_vault_sync_wait_ms"]>=1000:fail("vault block entity synchronous FULL wait >=1000ms")
elif kind=="lifecycle":
 if not Path("lifecycle-evidence/records.json").exists():fail("missing save/reopen raw lifecycle records")
elif kind=="schematica":
 p=Path("inworld-schematic-evidence/results.json")
 if not p.exists():fail("missing Schematica results")
 else:
  d=json.loads(p.read_text())
  if not d.get("fileSelection"):fail("classic .schematic was never selected")
  if d.get("exception"):fail("Schematica test crashed")
else:
 fail("unknown test: "+kind)
details["failures"]=faults
details["automatic_gate_pass"]=not faults
details["visual_review_still_required"]=True
out.write_text(json.dumps(details,indent=2))
print("STRICT_GATE",json.dumps(details),flush=True)
if faults:raise SystemExit(2)

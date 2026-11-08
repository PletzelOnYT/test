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
 active_tick=[point for point in tick if point[1]>40]
 if len(active_tick)>=2:
  duration=active_tick[-1][0]-active_tick[0][0];tps=(active_tick[-1][1]-active_tick[0][1])/duration if duration>0 else 0
  details["wallclock_average_tps"]=round(tps,3)
  if tps < (13 if kind=="onecpu" else 17):fail(f"measured TPS below acceptance threshold: {tps:.2f}")
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
elif kind in ("remote","remote2"):
 result=json.loads((evidence_dir/"result.json").read_text())
 details["actual_authoritative_player_x_samples"]=result.get("server_player_x_samples_scaled100")
 details["actual_authoritative_player_z_samples"]=result.get("server_player_z_samples_scaled100")
 details["first_destination_xz_reached"]=result.get("first_destination_xz_reached",False)
 details["second_destination_xz_reached"]=result.get("second_destination_xz_reached",False)
 if not result.get("first_destination_xz_reached"):fail("first distant server X/Z did not reach 96.5,96.5")
 if not result.get("second_destination_xz_reached"):fail("second distant server X/Z did not reach 192.5,192.5")
 if len(result.get("screenshots",[]))<14:fail("missing remote F3 and terrain screenshots")
 ticks=numbers(r"\[EagPerfHeartbeat\].*?\blastTick=(\d+)")
 details["server_tick_samples"]=len(ticks)
 details["server_tick_progression"]=ticks[-1][1]-ticks[0][1] if len(ticks)>1 else 0
 if details["server_tick_progression"]<1000:fail("server did not advance at least 1000 real ticks during distant chunk test")
 if any(e.get("kind")=="pageerror" for e in events):fail("Chromium uncaught error during distant chunk generation")
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
 details["trial_key_unlock_advancement"]=assertions.get("authentic_trial_key_advancement",False)
 details["reward_item_event"]=assertions.get("server_verified_reward_entity",False)
 # A broken /execute block-state property can echo a marker inside red syntax
 # errors, producing a FALSE PASS. Genuine /say outputs have a player-prefix
 # chat message and are counted by the browser script, never by substring.
 if any("does not have property" in text(e) or "<--[" in text(e) for e in events):
  fail("invalid vault block property or command-syntax error in recorded world")
 if not details["vault_active_evidence"]:fail("Vault never entered native ACTIVE block state")
 if not details["trial_key_unlock_advancement"]:fail("no real trial-key Under Lock and Key advancement")
 if not details["reward_item_event"]:fail("no actual item entity observed after vault reward ejection")
 waits=[(int(m.group(1)),text(e)) for e in events if "[EagPerfChunkWait]" in text(e)
        if (m:=re.search(r"elapsed=(\d+)ms",text(e)))]
 details["max_vault_sync_wait_ms"]=max((v for v,t in waits if "callerType=minecraft:vault" in t),default=0)
 if details["max_vault_sync_wait_ms"]>=1000:fail("vault block entity synchronous FULL wait >=1000ms")
elif kind=="lifecycle":
 p=Path("lifecycle-evidence/records.json")
 if not p.exists():fail("missing save/reopen raw lifecycle records")
 else:
  d=json.loads(p.read_text())
  lines="\n".join(e.get("text","") for e in d.get("events",[]))
  details["integrated_world_loads"]=lines.count("data loaded; spinning integrated server core")
  details["recorded_world_joins"]=lines.count(" joined the game")
  details["saved_dimensions_confirmations"]=lines.count("All dimensions are saved")
  if details["integrated_world_loads"]<2:fail("did not actually load the existing saved world twice")
  if details["recorded_world_joins"]<2:fail("player did not rejoin after reopening same world")
  if details["saved_dimensions_confirmations"]<1:fail("world save did not complete")
  if "08-reopened-world-running" not in d.get("screens",[]):fail("no visual evidence of reopened world running")
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

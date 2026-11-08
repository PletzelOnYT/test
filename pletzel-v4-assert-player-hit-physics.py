#!/usr/bin/env python3
"""Evidence gate for real mouse attack and knockback (not /damage command).

The Chromium gameplay driver takes screenshots, clicks the actual game surface,
and samples server-authoritative chicken NBT through vanilla scoreboard commands.
This gate checks that both health loss and displacement occurred BEFORE the
separately issued /damage command, with natural wandering suppressed via a
temporary vanilla Slowness effect. It does not alter the game HTML.
"""
import json
import re
from pathlib import Path

root=Path("cheats-entity-evidence")
events=json.loads((root/"all-events.json").read_text())
result=json.loads((root/"result.json").read_text())
assert result.get("fatal") is None, "browser test raised an exception"
texts=[e.get("text","") for e in events]
applied_slowness=next((i for i,s in enumerate(texts) if "Applied effect Slowness to Chicken" in s),None)
removed_slowness=next((i for i,s in enumerate(texts) if "Removed effect Slowness from Chicken" in s),None)
command_damage=next((i for i,s in enumerate(texts) if re.search(r"Applied 1[.]0 damage to Chicken",s)),None)
assert applied_slowness is not None, "test did not apply Slowness to isolate knockback"
assert removed_slowness is not None and removed_slowness>applied_slowness, "Slowness was not cleared"
assert command_damage is not None and command_damage>removed_slowness, "control command damage ordering not verified"
server_data=texts[applied_slowness:command_damage]
def matches(field):
    pat=re.compile(re.escape(field)+r" on Chicken after scale factor of 100[.]00 is (-?\\d+)")
    out=[]
    for line in server_data:
        m=pat.search(line)
        if m: out.append(int(m.group(1)))
    return out
hp=matches("Health")
pos_x=matches("Pos[0]")
pos_z=matches("Pos[2]")
# Multiple real clicks occurred between the last PRE and POST scoreboard queries.
assert len(hp)>=2 and hp[-2]==400 and hp[-1]<400, f"unproven actual attack health loss: {hp}"
assert len(pos_z)>=2 and len(pos_x)>=2, f"missing authoritative position readback: X={pos_x}, Z={pos_z}"
dx=(pos_x[-1]-pos_x[-2])/100
dz=(pos_z[-1]-pos_z[-2])/100
distance=(dx*dx+dz*dz)**0.5
assert distance>0.25, f"no measurable player-hit displacement before /damage: {distance:.3f} blocks"
assert len([x for x in result.get("screenshots",[]) if "05c-real-player-second-click" in str(x)])>0, "no attack screenshot checkpoint"
proof=dict(
    real_mouse_hit_health_before=hp[-2]/100,
    real_mouse_hit_health_after=hp[-1]/100,
    knockback_x_blocks=dx,
    knockback_z_blocks=dz,
    knockback_horizontal_blocks=round(distance,3),
    damage_control_event_index=command_damage,
    confirmed_before_command_control=True,
    limitation="Works under tested arena conditions; does not establish absence of server stalls or terrain voids",
)
(root/"asserted-player-hit-physics.json").write_text(json.dumps(proof,indent=2))
print("REAL PLAYER HIT / DAMAGE / KNOCKBACK VERIFIED",json.dumps(proof),flush=True)

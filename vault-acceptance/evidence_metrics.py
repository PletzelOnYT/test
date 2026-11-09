#!/usr/bin/env python3
"""Shared parser for raw compiled-browser worker telemetry; malformed markers fail closed."""
import re

def extract(events):
    waits, pending, ages, ticks = [], [], [], []
    malformed_waits = malformed_pending = malformed_heartbeats = 0
    for event in events:
        line = event.get("text", "") or event.get("detail", "")
        if "[EagPerfChunkWait]" in line:
            m = re.search(r"\belapsed=(\d+)ms\b", line)
            if m: waits.append((int(m.group(1)), line[:1100]))
            else: malformed_waits += 1
        if "[PletzelActiveChunkWait]" in line:
            m = re.search(r"\bwaiting=(\d+)ms\b", line)
            if m: pending.append((int(m.group(1)), line[:1100]))
            else: malformed_pending += 1
        if "[EagPerfHeartbeat]" in line:
            age = re.search(r"\bsinceCompleted=(\d+)ms\b", line)
            tick = re.search(r"\blastTick=(\d+)\b", line)
            if age and tick:
                ages.append(int(age.group(1))); ticks.append(int(tick.group(1)))
            else: malformed_heartbeats += 1
    return {
        "chunk_wait_count": len(waits),
        "max_any_sync_chunk_wait_ms": max((n for n,_ in waits),default=0),
        "max_pending_chunk_wait_ms": max((n for n,_ in pending),default=0),
        "max_since_completed_heartbeat_ms": max(ages,default=None),
        "heartbeat_count": len(ticks),
        "malformed_chunk_wait_events": malformed_waits,
        "malformed_pending_wait_events": malformed_pending,
        "malformed_heartbeat_events": malformed_heartbeats,
        "worst_sync_chunk_wait": max(waits,default=(0,None),key=lambda p:p[0])[1],
        "worst_pending_chunk_wait": max(pending,default=(0,None),key=lambda p:p[0])[1],
    }

def stall_failures(metrics, kind):
    """Fail closed on missing worker heartbeats and prolonged native waits."""
    failures=[]
    if not metrics["heartbeat_count"] or metrics["max_since_completed_heartbeat_ms"] is None:
        failures.append("required native server heartbeat/tick-completion telemetry missing")
    for key in ("malformed_chunk_wait_events","malformed_pending_wait_events","malformed_heartbeat_events"):
        if metrics[key]: failures.append(f"unparseable native evidence: {key}={metrics[key]}")
    # 1-CPU is a degraded stress profile, never a claimed normal gameplay pass.
    wait_limit=15000 if kind=="onecpu" else 2000
    for key in ("max_any_sync_chunk_wait_ms","max_pending_chunk_wait_ms"):
        if metrics[key] >= wait_limit:
            failures.append(f"{key}={metrics[key]}ms exceeds {wait_limit}ms")
    age=metrics["max_since_completed_heartbeat_ms"]
    age_limit=30000 if kind=="onecpu" else 10000
    if age is not None and age>=age_limit:
        failures.append(f"max_since_completed_heartbeat_ms={age}ms exceeds {age_limit}ms")
    return failures

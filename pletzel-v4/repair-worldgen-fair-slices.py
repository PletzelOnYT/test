#!/usr/bin/env python3
"""Isolate the web worldgen and server-coroutine cooperative-yield clocks.
This intentionally changes only EaglerWorldgenYield scheduling, never game data,
biomes, block states, AI, the Minecraft TPS reporter or native Schematica.
Fail closed if the pinned upstream source unexpectedly changes.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: repair-worldgen-fair-slices.py <pinned-engine-root>")
path = Path(sys.argv[1]) / ("game/src/main/java/net/lax1dude/"
    "eaglercraft/v1_8/sp/server/EaglerWorldgenYield.java")
src = path.read_text(encoding="utf-8")
def replace_once(before, after, label):
    global src
    actual = src.count(before)
    if actual != 1:
        raise AssertionError(f"{label}: expected one pinned source occurrence, got {actual}")
    src = src.replace(before, after, 1)
    print(f"PATCH {label}")

replace_once(
    "\tprivate static long nextYieldAt;\n\tprivate static int frequentCalls;",
    """\t// TeaVM server/worldgen threads are cooperative fibers in one JS worker. A
\t// single global deadline lets a server ticket loop reschedule a generation
\t// fiber's checkpoint (or vice versa), allowing a hot fiber to run past its
\t// own budget. Keep separate clocks and frequency counters.
\tprivate static long worldgenNextYieldAt;
\tprivate static long serverNextYieldAt;
\tprivate static int worldgenFrequentCalls;
\tprivate static int serverFrequentCalls;""",
    "separate fiber clocks",
)
replace_once(
    """\t\tlong now = EagRuntime.steadyTimeMillis();
\t\tif (now >= nextYieldAt) {""",
    """\t\tlong now = EagRuntime.steadyTimeMillis();
\t\tboolean generationFiber = EaglerWorldgenExecutor.isExecutorThread();
\t\tlong fiberYieldAt = generationFiber ? worldgenNextYieldAt : serverNextYieldAt;
\t\tif (now >= fiberYieldAt) {""",
    "read own fiber clock",
)
replace_once(
    """\t\t\tboolean timerHandoff = EaglerWorldgenExecutor.isExecutorThread()
\t\t\t\t\t&& EaglerServerState.claimWorldgenTimerHandoff(now);""",
    """\t\t\tboolean timerHandoff = generationFiber
\t\t\t\t\t&& EaglerServerState.claimWorldgenTimerHandoff(now);""",
    "preserve timer handoff only for generation fiber",
)
replace_once(
    """\t\t\tnextYieldAt = resumedAt + EaglerServerState.worldgenMillisUntilYield(resumedAt, MAX_SLICE_MILLIS);""",
    """\t\t\tlong nextForFiber = resumedAt
\t\t\t\t\t+ EaglerServerState.worldgenMillisUntilYield(resumedAt, MAX_SLICE_MILLIS);
\t\t\tif (generationFiber) {
\t\t\t\tworldgenNextYieldAt = nextForFiber;
\t\t\t} else {
\t\t\t\tserverNextYieldAt = nextForFiber;
\t\t\t}""",
    "write own fiber clock",
)
replace_once(
    """\t\tif ((++frequentCalls & 31) == 0) {
\t\t\tifNeeded();
\t\t}""",
    """\t\tboolean generationFiber = EaglerWorldgenExecutor.isExecutorThread();
\t\tint calls = generationFiber ? ++worldgenFrequentCalls : ++serverFrequentCalls;
\t\tif ((calls & 31) == 0) {
\t\t\tifNeeded();
\t\t}""",
    "separate hot-loop checkpoint counts",
)
assert "nextYieldAt" not in src, "old shared deadline survived"
assert "frequentCalls" not in src, "old shared counter survived"
path.write_text(src, encoding="utf-8")
print("Browser-only scheduling patch complete. Vanilla worldgen and rendering unchanged.")

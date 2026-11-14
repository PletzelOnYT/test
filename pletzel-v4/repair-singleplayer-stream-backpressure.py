#!/usr/bin/env python3
"""Honor real client chunk-decode ACKs, and drain stale inbound packet backlogs.

Background: one-core real-Chromium sample of the exact V4 HTML built at
bf6d09ae recorded up to 2,756 pending vanilla packet frames and a 28.4 sec
oldest frame age while the server still advanced at 15.95 TPS.
The old 4 chunks/tick WEB_MIN clamp overrides the client's adaptive ACK
feedback; the inbound render-thread pump is artificially capped at 12ms/frame.

Only hosted-web chunk flow control and *bounded* FIFO packet-pump budgets
change. No packet reordering, dropping, worldgen modification or TPS spoofing.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: repair-singleplayer-stream-backpressure.py <engine-root>")
root = Path(sys.argv[1]) / "game/src/main/java"

def patch(rel, edits):
    file = root / rel
    source = file.read_text(encoding="utf-8")
    for label, before, after in edits:
        found = source.count(before)
        if found != 1:
            raise AssertionError(f"{rel} {label}: expected one match, got {found}")
        source = source.replace(before, after, 1)
        print(f"{rel}: {label}")
    file.write_text(source, encoding="utf-8")

patch("net/minecraft/server/network/PlayerChunkSender.java", [
  ("allow sub-one-chunk client ACK backpressure",
   "private static final float WEB_MIN_CHUNKS_PER_TICK = 4.0F;",
   "private static final float WEB_MIN_CHUNKS_PER_TICK = 0.25F;"),
  ("bound initial web chunk burst",
   "private static final float WEB_START_CHUNKS_PER_TICK = 12.0F;",
   "private static final float WEB_START_CHUNKS_PER_TICK = 4.0F;"),
  ("bound peak web chunks per tick",
   "private static final float WEB_MAX_CHUNKS_PER_TICK = 24.0F;",
   "private static final float WEB_MAX_CHUNKS_PER_TICK = 12.0F;"),
  ("single in-flight ACK batch preserves client decode feedback",
   "private static final int WEB_MAX_UNACKNOWLEDGED_BATCHES = 2;",
   "private static final int WEB_MAX_UNACKNOWLEDGED_BATCHES = 1;"),
])

patch("net/lax1dude/eaglercraft/v1_8/sp/SingleplayerInboundPumpPolicy.java", [
 ("set bounded progressive FIFO drain budgets",
  """\tstatic final double NORMAL_BUDGET_MILLIS = 6.0;
\tstatic final double BACKLOG_BUDGET_MILLIS = 9.0;
\tstatic final double DEEP_BACKLOG_BUDGET_MILLIS = 12.0;
\tstatic final int BACKLOG_QUEUE_DEPTH = 256;
\tstatic final int DEEP_BACKLOG_QUEUE_DEPTH = 2048;
\tstatic final long STALE_QUEUE_NANOS = 250_000_000L;
\tstatic final long DEEP_STALE_QUEUE_NANOS = 1_000_000_000L;""",
  """\tstatic final double NORMAL_BUDGET_MILLIS = 6.0;
\tstatic final double BACKLOG_BUDGET_MILLIS = 10.0;
\tstatic final double DEEP_BACKLOG_BUDGET_MILLIS = 16.0;
\tstatic final double CRITICAL_BACKLOG_BUDGET_MILLIS = 24.0;
\tstatic final double EMERGENCY_BACKLOG_BUDGET_MILLIS = 32.0;
\tstatic final int BACKLOG_QUEUE_DEPTH = 256;
\tstatic final int DEEP_BACKLOG_QUEUE_DEPTH = 768;
\tstatic final int CRITICAL_BACKLOG_QUEUE_DEPTH = 1536;
\tstatic final int EMERGENCY_BACKLOG_QUEUE_DEPTH = 2400;
\tstatic final long STALE_QUEUE_NANOS = 250_000_000L;
\tstatic final long DEEP_STALE_QUEUE_NANOS = 1_000_000_000L;
\tstatic final long CRITICAL_STALE_QUEUE_NANOS = 3_000_000_000L;
\tstatic final long EMERGENCY_STALE_QUEUE_NANOS = 8_000_000_000L;"""),
 ("drain elderly packets without protocol reordering",
  """\tstatic double budgetMillis(final int queueDepth, final long oldestFrameNanos) {
\t\tif(queueDepth >= DEEP_BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= DEEP_STALE_QUEUE_NANOS) {
\t\t\treturn DEEP_BACKLOG_BUDGET_MILLIS;
\t\t}
\t\tif(queueDepth >= BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= STALE_QUEUE_NANOS) {
\t\t\treturn BACKLOG_BUDGET_MILLIS;
\t\t}
\t\treturn NORMAL_BUDGET_MILLIS;
\t}""",
  """\tstatic double budgetMillis(final int queueDepth, final long oldestFrameNanos) {
\t\t// Do not starve entity movement / world time behind a huge terrain burst.
\t\t// These are bounded *render-thread* time slices, not raw packet counts.
\t\t// Keep the original FIFO to preserve vanilla chunk/entity dependencies.
\t\tif(queueDepth >= EMERGENCY_BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= EMERGENCY_STALE_QUEUE_NANOS) {
\t\t\treturn EMERGENCY_BACKLOG_BUDGET_MILLIS;
\t\t}
\t\tif(queueDepth >= CRITICAL_BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= CRITICAL_STALE_QUEUE_NANOS) {
\t\t\treturn CRITICAL_BACKLOG_BUDGET_MILLIS;
\t\t}
\t\tif(queueDepth >= DEEP_BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= DEEP_STALE_QUEUE_NANOS) {
\t\t\treturn DEEP_BACKLOG_BUDGET_MILLIS;
\t\t}
\t\tif(queueDepth >= BACKLOG_QUEUE_DEPTH || oldestFrameNanos >= STALE_QUEUE_NANOS) {
\t\t\treturn BACKLOG_BUDGET_MILLIS;
\t\t}
\t\treturn NORMAL_BUDGET_MILLIS;
\t}""")
])
print("Bounded web-only inbound backpressure patched; vanilla packet order unchanged.")

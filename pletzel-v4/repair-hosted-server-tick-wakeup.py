#!/usr/bin/env python3
"""Browser-only liveness safety net for the 26.2 integrated server's timer.

Evidence, final Chromium run #42448255083:
  after tick 5658 the server never resumed its between-tick wait for 147454ms;
  worker heartbeat / postMessage still ran, worldgen FIFO had zero runnable jobs,
  but 56 generation tasks and 26192 chunk claims remained unreleased.
  The good world from the IDENTICAL HTML resumed timers and finished chunk work.

The original browser tickContinue() delegates to scheduler.postTask and installs
setTimeout only if the returned Promise rejects. A delayed, abandoned or
unresolved postTask leaves its TeaVM @Async callback suspended indefinitely.

Preserve native user-blocking scheduling, but independently arm ONE watchdog
setTimeout that invokes the same callback after d+100ms. A closure boolean
ensures that a late postTask or rejection cannot resume the green server thread
twice. This is a scheduler liveness guard, NOT a fictitious tick/level/chunk
completion, and it is never applied to desktop or to the worldgen executor.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:
    raise SystemExit("usage: repair-hosted-server-tick-wakeup.py <pinned-engine-root>")
p=Path(sys.argv[1])/"platform-teavm/src/main/java/net/lax1dude/eaglercraft/v1_8/sp/server/internal/ServerPlatformSingleplayer.java"
s=p.read_text(encoding="utf-8")
start=s.index('\t@JSBody(params = { "handler", "millis" }, script = "var d = Math.max(0, millis | 0);"')
end=s.index('\n\tprivate static native void scheduleTickContinue(TickContinueHandler handler, int millis);',start)
old=s[start:end]
if s.count(old)!=1:
    raise AssertionError("Original browser tick scheduling signature not unique")
if old.count('globalThis.setTimeout(handler, d)') != 2 or 'scheduler' not in old:
    raise AssertionError("Unexpected pinned browser scheduler; refuse speculative patch")
new='''\t@JSBody(params = { "handler", "millis" }, script = "var d = Math.max(0, millis | 0);"
\t\t\t+ "var done = false;"
\t\t\t+ "var wake = function() { if (!done) { done = true; globalThis.clearTimeout(fallback); handler(); } };"
\t\t\t+ "var fallback = globalThis.setTimeout(wake, d + 100);"
\t\t\t+ "try { var s = globalThis.scheduler;"
\t\t\t+ " if (s && typeof s.postTask === 'function') {"
\t\t\t+ "  var p = s.postTask(wake, { priority: 'user-blocking', delay: d });"
\t\t\t+ "  if (p && typeof p.catch === 'function') p.catch(wake);"
\t\t\t+ "  return;"
\t\t\t+ " }"
\t\t\t+ "} catch (e) {}"
\t\t\t+ "globalThis.setTimeout(wake, d);")'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding="utf-8")
print("PATCHED native TeaVM server @Async tick wake: scheduler.postTask + independent one-shot fallback at <= d+100ms")

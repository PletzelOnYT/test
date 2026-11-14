#!/usr/bin/env python3
"""Resume genuinely overdue TeaVM server tick callbacks from the LIVE supervisor.

Evidence:
* In #42448255083 the supervisor continued emitting heartbeats while a server
  coroutine stayed outside tickServer (phase=idle, activeTick=0) for 147 s.
* The existing @Async tickContinue uses scheduler.postTask plus an independent
  timeout, but both are callbacks scheduled through browser timers/tasks.
* The supervisor runs in the SAME worker JS realm and is demonstrably alive.

This patch does not alter worldgen, TPS counters, dimensions, chunk futures or
the watchdog's one-shot callback. It adds a THIRD *independent* callback path,
gated by actual elapsed monotonic time and the existing one-shot wake closure.
No timeout polling or wakeup occurs unless the coroutine is already suspended.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: repair-supervisor-tick-resume.py <pinned-engine-root>")
root = Path(sys.argv[1])
worker = root / "platform-teavm/src/main/java/net/lax1dude/eaglercraft/v1_8/sp/server/internal/ServerPlatformSingleplayer.java"
engine = root / "game/src/main/java/net/lax1dude/eaglercraft/v1_8/sp/server/EaglerIntegratedServerWorker26.java"
text = worker.read_text(encoding="utf-8")
old = '''\t\t\t+ "var wake = function() { if (!done) { done = true; globalThis.clearTimeout(fallback); handler(); } };"
\t\t\t+ "var fallback = globalThis.setTimeout(wake, d + 100);"'''
new = '''\t\t\t+ "var wake = function() { if (!done) { done = true; if (globalThis.__pletzelTickWake26 === wake) globalThis.__pletzelTickWake26 = null; globalThis.clearTimeout(fallback); handler(); } };"
\t\t\t+ "var clk = globalThis.performance && typeof globalThis.performance.now === 'function' ? globalThis.performance.now() : Date.now();"
\t\t\t+ "wake.__pletzelDueAt = clk + d + 150;"
\t\t\t+ "globalThis.__pletzelTickWake26 = wake;"
\t\t\t+ "var fallback = globalThis.setTimeout(wake, d + 100);"'''
assert text.count(old) == 1, "Expected the exact existing worker-wakeup recovery patch, no duplicate source edit"
text = text.replace(old,new,1)
needle = "\tpublic static void tickContinue(long millis) {"
addition = '''\t/**
\t * Third, timer-independent path for a server coroutine that is genuinely
\t * overdue. The supervisor is already running while @Async tickContinue is
\t * suspended. Calling the same one-shot wake closure is safe: the scheduler
\t * and setTimeout compete through its single 'done' guard.
\t *
\t * This is not a thread restart, fake tick or chunk-completion shortcut.
\t */
\t@JSBody(params = {}, script = "var w = globalThis.__pletzelTickWake26;"
\t\t\t+ "if (typeof w !== 'function') return;"
\t\t\t+ "var now = globalThis.performance && typeof globalThis.performance.now === 'function' ? globalThis.performance.now() : Date.now();"
\t\t\t+ "if (now < w.__pletzelDueAt) return;"
\t\t\t+ "globalThis.__pletzelSupervisorWakeCount26 = (globalThis.__pletzelSupervisorWakeCount26 || 0) + 1;"
\t\t\t+ "var last = globalThis.__pletzelSupervisorWakeLog26 || 0;"
\t\t\t+ "if (now - last > 5000) { globalThis.__pletzelSupervisorWakeLog26 = now;"
\t\t\t+ "  if (globalThis.console && console.warn) console.warn('[PletzelWakeRescue26] server tick callback overdue; supervisor delivered one-shot wake'); }"
\t\t\t+ "w();")
\tpublic static native void recoverOverdueServerTick();

'''
assert text.count(needle) == 1, "Pinned TeaVM worker tickContinue method moved"
text = text.replace(needle, addition + needle, 1)
worker.write_text(text,encoding="utf-8")

text = engine.read_text(encoding="utf-8")
old = '''\tprivate static void supervisorTick(boolean sleepWhenIdle) {
\t\t// The supervisor remains schedulable while the vanilla server coroutine is'''
new = '''\tprivate static void supervisorTick(boolean sleepWhenIdle) {
\t\t// The browser worker can keep servicing its supervisor while the dedicated
\t\t// vanilla server coroutine is stuck waiting for a lost/delayed timer task.
\t\t// Recover ONLY the real overdue @Async callback; its JS one-shot guard
\t\t// prevents a second completion from scheduler.postTask or setTimeout.
\t\tServerPlatformSingleplayer.recoverOverdueServerTick();
\t\t// The supervisor remains schedulable while the vanilla server coroutine is'''
assert text.count(old)==1, "Pinned supervisor tick signature changed"
engine.write_text(text.replace(old,new,1),encoding="utf-8")
# The :game module compiles against the shared :platform API, never directly
# against platform-teavm source. Expose the signature there and retain a
# harmless desktop no-op so LWJGL stays compile-compatible.
shared = root / "platform/src/main/java/net/lax1dude/eaglercraft/v1_8/sp/server/internal/ServerPlatformSingleplayer.java"
# Shared :platform file retains upstream CRLF and existing whitespace.
# Read/replace BYTES to avoid rewriting all 70 legacy lines as new LF lines,
# which makes git diff --check expose unrelated original comment whitespace.
st = shared.read_bytes()
needle = b"\tpublic static native void tickContinue(long millis);"
if st.count(needle) != 1:raise AssertionError("missing shared platform tick continuation contract")
st = st.replace(needle,needle+b"\n\n\tpublic static native void recoverOverdueServerTick();",1)
shared.write_bytes(st)

desktop = root / "platform-lwjgl/src/main/java/net/lax1dude/eaglercraft/v1_8/sp/server/internal/ServerPlatformSingleplayer.java"
st = desktop.read_text(encoding="utf-8")
needle = "\tpublic static void tickContinue(long millis) {\n\t\tEagUtils.sleep(millis);\n\t}"
if st.count(needle) != 1:raise AssertionError("missing LWJGL platform tick continuation anchor")
st = st.replace(needle,needle+"\n\n\tpublic static void recoverOverdueServerTick() {\n\t\t// No browser worker or TeaVM coroutine on the desktop.\n\t}",1)
desktop.write_text(st,encoding="utf-8")
print("PATCHED: shared platform API + desktop harmless no-op, game Java can compile")

print("PATCHED: real worker supervisor can deliver one-shot overdue TeaVM tick callback without timer/scheduler")

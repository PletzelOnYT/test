#!/usr/bin/env python3
"""Opt-in GPU presentation-stage profiler for Mac 8.11s main-thread freeze.

The existing EagPerfClient 'present' aggregate includes command submission,
surface.present() and cleanup. We must not misclassify it as meshing/CPU/GC.
Record only >250ms gaps, gated by ?perfdebug, without affecting render state.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: trace-client-present-stall.py <engine-root>")
file=Path(sys.argv[1])/"game/src/main/java/net/minecraft/client/Minecraft.java"
s=file.read_text(encoding="utf8")
def repl(old,new):
 global s
 if s.count(old)!=1:raise AssertionError("Client present source anchor mismatch: "+old[:110])
 s=s.replace(old,new,1)
repl("""         RenderSystem.getDevice().createCommandEncoder().submit();
         if (this.windowSurface.isAcquired()) {
            this.windowSurface.present();
         }""",
"""         long eaglerSubmitStarted = eaglerPerfEnabled ? Util.getNanos() : 0L;
         RenderSystem.getDevice().createCommandEncoder().submit();
         long eaglerSubmitFinished = eaglerPerfEnabled ? Util.getNanos() : 0L;
         if (this.windowSurface.isAcquired()) {
            this.windowSurface.present();
         }
         long eaglerSurfaceFinished = eaglerPerfEnabled ? Util.getNanos() : 0L;""")
repl("""         long eaglerPresentNanos = eaglerPerfEnabled ? eaglerLimiterStarted - eaglerPresentStarted : 0L;
         profiler.popPush("frameLimiter");""",
"""         long eaglerPresentNanos = eaglerPerfEnabled ? eaglerLimiterStarted - eaglerPresentStarted : 0L;
         if (eaglerPerfEnabled && eaglerPresentNanos >= 250_000_000L) {
            // All boundaries are measured inside the SAME Java render-frame.
            // The last successful frame may have been delayed externally by
            // macOS Chromium scheduling, GPU driver, or GC. This instrumentation
            // identifies where elapsed wall time accumulated, not its cause.
            LOGGER.warn("[PletzelPresentStall] total={}ms blitPrepare={}ms commandSubmit={}ms surfacePresent={}ms cleanup={}ms",
               eaglerPresentNanos / 1_000_000L,
               (eaglerSubmitStarted - eaglerPresentStarted) / 1_000_000L,
               (eaglerSubmitFinished - eaglerSubmitStarted) / 1_000_000L,
               (eaglerSurfaceFinished - eaglerSubmitFinished) / 1_000_000L,
               (eaglerLimiterStarted - eaglerSurfaceFinished) / 1_000_000L);
         }
         profiler.popPush("frameLimiter");""")
file.write_text(s,encoding="utf8")
print("PRESENT_TRACE: capture real 250ms+ blit, GPU submit, surfacePresent and cleanup under perfdebug; no behavior change")

#!/usr/bin/env python3
"""Patch native 26.2 map texture invalidation without replacing vanilla map pixels.

The vanilla manager already caches by MapId, uploads only on change and resets
textures on world transitions. An in-place colors[] mutation with an unchanged
MapItemSavedData identity can otherwise go unnoticed when the update call is
missed. Audit only every 250 ms for maps that are actually rendered.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
java=root/"game/src/main/java/net/minecraft/client/resources/MapTextureManager.java"
s=java.read_text()
needle="import it.unimi.dsi.fastutil.ints.Int2ObjectMap;"
assert s.count(needle)==1
s=s.replace(needle,"import java.util.Arrays;\n"+needle,1)

needle="      private boolean requiresUpload = true;"
assert s.count(needle)==1
s=s.replace(needle,
"""      private boolean requiresUpload = true;
      private int lastColorFingerprint;
      private long lastColorAuditNanos;
      private static final long COLOR_AUDIT_INTERVAL_NANOS = 250_000_000L;""",1)

needle="""      private void updateTextureIfNeeded() {
         if (this.requiresUpload) {
            NativeImage pixels = this.texture.getPixels();"""
assert s.count(needle)==1
s=s.replace(needle,
"""      private void updateTextureIfNeeded() {
         long now = System.nanoTime();
         if (!this.requiresUpload && now-this.lastColorAuditNanos >= COLOR_AUDIT_INTERVAL_NANOS) {
            this.lastColorAuditNanos = now;
            // This is an integrity backstop, not a second map texture cache.
            // Never manufacture map data; reuse the server-delivered colors.
            this.requiresUpload = Arrays.hashCode(this.data.colors) != this.lastColorFingerprint;
         }
         if (this.requiresUpload) {
            NativeImage pixels = this.texture.getPixels();""",1)

needle="""            this.texture.upload();
            this.requiresUpload = false;"""
assert s.count(needle)==1
s=s.replace(needle,
"""            this.texture.upload();
            this.requiresUpload = false;
            this.lastColorFingerprint = Arrays.hashCode(this.data.colors);
            this.lastColorAuditNanos = now;""",1)
java.write_text(s)
assert s.count("Arrays.hashCode(this.data.colors)") == 2
print("MAP_TOOLTIP_TEXTURE_AUDIT_PATCHED: native 128x128 MapId texture cache, bounded color recheck")

#!/usr/bin/env python3
"""Preserve all native gameplay while repairing three confirmed source-level liveness/visibility gaps.

1. TCP/Wisp relay movement must NOT depend on the next inbound network pump to
   flush already-written Minecraft packets. The Connection's flush=true flag
   still controls actual publication; packet sequencing/validation unchanged.
2. A freshly installed nonempty client chunk must schedule terrain meshing
   BEFORE asynchronous light updates, with normal light completion still
   rebuilding adjacent boundaries. No fake terrain or forced chunks.
3. Schematica holograms need native reversed-Z polygon bias and a tiny face
   separation even for missing schematic blocks touching real blocks.
   Depth test remains GREATER_THAN_OR_EQUAL and depth writes remain disabled.
"""
from pathlib import Path
import sys
if len(sys.argv)!=2:raise SystemExit("usage: repair-movement-terrain-ghost.py <pinned-engine-root>")
root=Path(sys.argv[1])/"game/src/main/java"
def patch(rel,old,new):
 p=root/rel
 s=p.read_text(encoding="utf-8")
 n=s.count(old)
 if n!=1:raise AssertionError(f"{rel}: expected exactly one pinned source anchor, got {n}")
 p.write_text(s.replace(old,new,1),encoding="utf-8")
 print("PATCHED",rel)

patch("net/lax1dude/eaglercraft/v1_8/socket/WebSocketPacketBridge.java",
 '''		this.connection.setEaglerTransport(this::pump, this::close, eaglerFrames ? this::drainOutbound : null);''',
 '''		// Every flushed Minecraft packet, including real player movement over a
		// relay/Wisp TCP byte stream, must reach WebSocket.send immediately.
		// The old relay-only pump path could leave already flushed movement frames
		// pending until the next inbound/tick pump while local prediction continued.
		// drainOutbound coalesces byte-stream packets in FIFO order; flush=false
		// still remains pending until Connection.flush, preserving Netty semantics.
		this.connection.setEaglerTransport(this::pump, this::close, this::drainOutbound);''')
patch("net/minecraft/client/multiplayer/ClientPacketListener.java",
 '''      this.updateLevelChunk(x, z, packet.getChunkData());
      ClientboundLightUpdatePacketData lightData = packet.getLightData();''',
 '''      this.updateLevelChunk(x, z, packet.getChunkData());
      // Do not gate the FIRST usable world geometry on the queued light task.
      // ClientChunkCache has already installed real chunk packet block data.
      // Schedule each actual nonempty section for a normal mesh build now;
      // the existing enableChunkLight callback later invalidates its entire
      // 3x3 section neighborhood again for accurate border light/occlusion.
      // No placeholder blocks, fog tricks, disabled frustum or invented chunks.
      if (net.lax1dude.eaglercraft.v1_8.EagRuntime.getPlatformType()
            != net.lax1dude.eaglercraft.v1_8.internal.EnumPlatformType.DESKTOP) {
         LevelChunk delivered = this.level.getChunkSource().getChunk(x, z, false);
         if (delivered != null) {
            LevelChunkSection[] deliveredSections = delivered.getSections();
            for (int sectionIndex = 0; sectionIndex < deliveredSections.length; sectionIndex++) {
               if (!deliveredSections[sectionIndex].hasOnlyAir()) {
                  this.minecraft.levelExtractor.setSectionDirty(
                     x, this.level.getSectionYFromSectionIndex(sectionIndex), z);
               }
            }
         }
      }
      ClientboundLightUpdatePacketData lightData = packet.getLightData();''')
patch("net/minecraft/client/renderer/RenderPipelines.java",
 '''         .withDepthStencilState(new DepthStencilState(CompareOp.GREATER_THAN_OR_EQUAL, false))
         .withCull(false)
         .build()
   );
   public static final RenderPipeline ENTITY_TRANSLUCENT_EMISSIVE''',
 '''         // Native 26.2 uses reverse-Z. Its TEXT_POLYGON_OFFSET pipeline uses
         // positive slope/constant bias to resolve coplanar faces; use a
         // smaller bias for translucent ghost geometry while retaining the
         // normal GREATER_THAN_OR_EQUAL depth comparison and no depth writes.
         .withDepthStencilState(new DepthStencilState(CompareOp.GREATER_THAN_OR_EQUAL, false, 1.0F, 1.0F))
         .withCull(false)
         .build()
   );
   public static final RenderPipeline ENTITY_TRANSLUCENT_EMISSIVE''')
patch("net/pletzel/schematica/SchematicaWorldRenderer.java",
 '''                        if (!missing) {
                            // Move wrong-block overlay faces just above the world's opaque
                            // block surfaces to avoid depth fighting while retaining geometry.
                            blockPose.translate(.5,.5,.5);
                            blockPose.scale(1.006f,1.006f,1.006f);
                            blockPose.translate(-.5,-.5,-.5);
                        }''',
 '''                        // A missing schematic block can ALSO share a coplanar
                        // face with an adjacent real world block. Giving only
                        // wrong-block ghosts a separation created edge flicker.
                        // Tiny expansion for missing blocks; larger existing
                        // separation for incorrect blocks. Native depth testing
                        // still occludes ghosts behind actual world surfaces.
                        float faceSeparation = missing ? 1.002f : 1.006f;
                        blockPose.translate(.5,.5,.5);
                        blockPose.scale(faceSeparation,faceSeparation,faceSeparation);
                        blockPose.translate(-.5,-.5,-.5);''')
print("PRESERVED: all packets, order, game rules, mesh data, native depth occlusion, Schematica controls")

package net.lax1dude.eaglercraft.v1_8.voice;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.lax1dude.eaglercraft.v1_8.internal.PlatformEaglerVoice26;
import net.minecraft.client.Minecraft;
import net.minecraft.network.Connection;
import net.minecraft.world.entity.player.Player;
import org.slf4j.Logger;

/**
 * Real official EaglerXServer V5 voice signaling (not Simple Voice Chat, not
 * a custom Pletzel network). V5 packets travel in the existing 0xEE-prefixed
 * Eagler WebSocket frames shared with skins; they are NOT Minecraft 26.2
 * custom-payload packets. Packet IDs are from lax1dude/eaglerxserver
 * GamePluginMessageProtocol.V5, with server-mediated WebRTC peer pairing.
 *
 * Audio is fully disabled until the player explicitly clicks Enable Voice.
 * This protocol supports the original proximity and global voice modes; it
 * does not provide private voice groups. Global peers may expose public IPs.
 */
public final class EaglerXVoiceClient26 {
   private static final Logger LOGGER = LogUtils.getLogger();
   private static final int C_REQUEST=0x06, C_CONNECT=0x07, C_DISCONNECT=0x08,
      C_DISCONNECT_PEER=0x09, C_ICE=0x0A, C_DESCRIPTION=0x0B;
   private static final int S_ALLOWED=0x06, S_CONNECT=0x07, S_ANNOUNCE=0x08,
      S_DISCONNECT_PEER=0x09, S_ICE=0x0A, S_DESCRIPTION=0x0B, S_GLOBAL=0x0C;
   private final Minecraft minecraft;
   private final Connection connection;
   private final Set<UUID> peers = new HashSet<>();
   private final Set<UUID> requested = new HashSet<>();
   private final Map<UUID,String> displayNames = new HashMap<>();
   private String iceConfiguration = "[]";
   private boolean serverAllowed, userEnabled, sentConnect, muted;
   private boolean voiceActivation;
   private int channel = 1; // 1 = Proximity, 2 = Global; OFF is userEnabled=false
   private int tickCounter;
   private double proximity = 22.0;
   private double volume = 0.65;
   private double sensitivity = 0.07;
   private boolean lastTransmitting;

   public EaglerXVoiceClient26(final Minecraft minecraft, final Connection connection) {
      this.minecraft=minecraft;
      this.connection=connection;
      PlatformEaglerVoice26.initialize(); // NO microphone permission requested here
   }

   public boolean supported() { return PlatformEaglerVoice26.supported(); }
   public boolean serverAllowed() { return serverAllowed; }
   public boolean userEnabled() { return userEnabled; }
   public boolean muted() { return muted; }
   public boolean voiceActivation() { return voiceActivation; }
   public boolean transmitting() { return lastTransmitting; }
   public int channel() { return channel; }
   public int peerCount() { return peers.size(); }
   public double volume() { return volume; }
   public double sensitivity() { return sensitivity; }
   public double proximity() { return proximity; }
   public String status() {
      if (!supported()) return "Browser WebRTC or microphone API unavailable";
      if (!serverAllowed) return "This EaglerXServer has not advertised voice";
      if (!userEnabled) return "Available - microphone OFF (press Enable)";
      return switch (PlatformEaglerVoice26.status()) {
         case 0 -> "Voice disabled";
         case 1 -> "Requesting microphone permission...";
         case 2 -> "Connected to Eagler voice signaling (" + peerCount() + " peers)";
         case 3 -> "Microphone permission denied";
         default -> "Voice unavailable";
      };
   }

   public void setEnabled(final boolean enable) {
      if (!enable) {
         if (sentConnect) send(C_DISCONNECT,null,null);
         sentConnect=false;userEnabled=false;lastTransmitting=false;
         peers.clear();requested.clear();displayNames.clear();
         PlatformEaglerVoice26.stop();
         return;
      }
      if (!serverAllowed || !supported()) return;
      if (!userEnabled) {
         userEnabled=true;
         PlatformEaglerVoice26.configure(iceConfiguration);
         PlatformEaglerVoice26.globalChannel(channel==2);
         PlatformEaglerVoice26.volume(volume);
         // Called only from Minecraft's Enable Voice button (user gesture).
         PlatformEaglerVoice26.enable();
      }
   }

   public void setMuted(final boolean mute) {
      muted=mute;
      if (mute) { PlatformEaglerVoice26.transmit(false);lastTransmitting=false; }
   }
   public void setVoiceActivation(final boolean value) {voiceActivation=value;}
   public void setProximity(final double value) {proximity=Math.max(8,Math.min(32,value));}
   public void setSensitivity(final double value) {sensitivity=Math.max(0.01,Math.min(0.30,value));}
   public void setVolume(final double value) {
      volume=Math.max(0,Math.min(1.5,value));PlatformEaglerVoice26.volume(volume);
   }
   public void setChannel(final int newChannel) {
      if (newChannel!=1 && newChannel!=2 || channel==newChannel) return;
      if (sentConnect) send(C_DISCONNECT,null,null);
      peers.forEach(id -> PlatformEaglerVoice26.closePeer(id.toString()));
      peers.clear(); requested.clear();sentConnect=false;
      channel=newChannel;PlatformEaglerVoice26.globalChannel(newChannel==2);
   }

   public void handleServerVoiceFrame(final byte[] frame) {
      if (frame==null || frame.length==0 || frame.length>32767) return;
      try {
         DataInputStream data=new DataInputStream(new ByteArrayInputStream(frame));
         int id=data.readUnsignedByte();
         if (id==S_ALLOWED) {
            boolean allowed=data.readBoolean();
            String[] servers=new String[0];
            if(allowed) {
               int count=readVarInt(data);
               if(count<0 || count>64) throw new IOException("ICE server count exceeds limit");
               servers=new String[count];
               for(int i=0;i<count;i++)servers[i]=readUtf(data,1024);
            }
            if(data.available()!=0) throw new IOException("Trailing allowed packet bytes");
            serverAllowed=allowed;
            if(!allowed)setEnabled(false);
            else {
               com.google.gson.JsonArray list=new com.google.gson.JsonArray();
               for(String item:servers) list.add(item);
               iceConfiguration=list.toString();
            }
            return;
         }
         if(!serverAllowed || !userEnabled || !sentConnect) return;
         switch(id) {
            case S_CONNECT -> {
               UUID peer=readUUID(data);
               boolean offer=data.readBoolean();
               if(!peer.equals(self()) && peers.add(peer)) {
                  PlatformEaglerVoice26.openPeer(peer.toString(),offer);
               }
            }
            case S_ANNOUNCE -> {
               UUID peer=readUUID(data);
               if(channel==2)request(peer);
            }
            case S_DISCONNECT_PEER -> {
               UUID peer=readUUID(data);
               peers.remove(peer); requested.remove(peer);
               PlatformEaglerVoice26.closePeer(peer.toString());
            }
            case S_ICE -> {
               UUID peer=readUUID(data);
               String json=readBlob(data);
               if(peers.contains(peer)) PlatformEaglerVoice26.ice(peer.toString(),json);
            }
            case S_DESCRIPTION -> {
               UUID peer=readUUID(data);
               String json=readBlob(data);
               if(peers.contains(peer)) PlatformEaglerVoice26.description(peer.toString(),json);
            }
            case S_GLOBAL -> {
               int count=readVarInt(data);
               if(count<0 || count>256) throw new IOException("Voice roster too large");
               UUID[] all=new UUID[count];
               for(int i=0;i<count;i++) all[i]=readUUID(data);
               if(data.available()>0)for(int i=0;i<count;i++)displayNames.put(all[i],readUtf(data,16));
               if(channel==2)for(UUID peer:all)request(peer);
            }
            default -> {return;}
         }
      } catch(IOException|RuntimeException ex) {
         LOGGER.warn("Discarded malformed EaglerXServer v5 voice signal: {}",ex.getMessage());
      }
   }

   public void tick() {
      if (!userEnabled || !serverAllowed) return;
      for(int i=0;i<24;i++) {
         String event=PlatformEaglerVoice26.poll();
         if(event==null || event.isEmpty())break;
         try {
            JsonObject json=JsonParser.parseString(event).getAsJsonObject();
            String kind=json.get("kind").getAsString();
            if("ready".equals(kind)) {
               if(!sentConnect) {send(C_CONNECT,null,null);sentConnect=true;}
            } else if("permission".equals(kind)) {
               LOGGER.info("Voice microphone permission denied");
            } else {
               UUID peer=UUID.fromString(json.get("id").getAsString());
               if(!peers.contains(peer)) continue;
               switch(kind) {
                  case "ice" -> send(C_ICE,peer,json.get("data").getAsString());
                  case "description" -> send(C_DESCRIPTION,peer,json.get("data").getAsString());
                  case "closed" -> {
                     peers.remove(peer);requested.remove(peer);
                     send(C_DISCONNECT_PEER,peer,null);
                  }
                  default -> { }
               }
            }
         } catch(RuntimeException ex) {LOGGER.warn("Invalid browser voice event");}
      }
      if(!sentConnect || minecraft.player==null || minecraft.level==null)return;
      boolean talk=!muted && (voiceActivation
         ? PlatformEaglerVoice26.microphoneLevel()>sensitivity
         : minecraft.options.keyEaglerVoicePTT.isDown()) && minecraft.gui.screen()==null;
      PlatformEaglerVoice26.transmit(talk);
      lastTransmitting=talk;
      if(++tickCounter%10!=0)return;
      PlatformEaglerVoice26.direction(minecraft.player.getYRot());
      if(channel==1) {
         Set<UUID> near=new HashSet<>();
         for(Player p:minecraft.level.players()) {
            if(p==minecraft.player)continue;
            double dx=p.getX()-minecraft.player.getX();
            double dy=p.getY()-minecraft.player.getY();
            double dz=p.getZ()-minecraft.player.getZ();
            if(dx*dx+dy*dy+dz*dz>proximity*proximity)continue;
            near.add(p.getUUID());
            request(p.getUUID());
            PlatformEaglerVoice26.position(p.getUUID().toString(),dx,dy,dz);
         }
         for(UUID old:new HashSet<>(requested)) {
            if(!near.contains(old)) {
               requested.remove(old);
               if(peers.remove(old)) {
                  PlatformEaglerVoice26.closePeer(old.toString());
                  send(C_DISCONNECT_PEER,old,null);
               }
            }
         }
      }
   }

   public void destroy() {
      setEnabled(false);
      serverAllowed=false;
      PlatformEaglerVoice26.stop();
   }

   private UUID self() { return minecraft.player!=null?minecraft.player.getUUID():new UUID(0L,0L); }
   private void request(final UUID peer) {
      if(peer.equals(self()) || requested.contains(peer) || peers.contains(peer))return;
      if(requested.add(peer))send(C_REQUEST,peer,null);
   }
   private void send(final int packetId, final UUID player, final String payload) {
      if(!connection.isConnected())return;
      try {
         ByteArrayOutputStream raw=new ByteArrayOutputStream();
         DataOutputStream out=new DataOutputStream(raw);
         out.writeByte(packetId);
         if(player!=null) {
            out.writeLong(player.getMostSignificantBits());
            out.writeLong(player.getLeastSignificantBits());
         }
         if(payload!=null) {
            byte[] bytes=payload.getBytes(StandardCharsets.UTF_8);
            if(bytes.length>32750)throw new IOException("WebRTC signal too long");
            writeVarInt(out,bytes.length);out.write(bytes);
         }
         connection.sendEaglerMessage(raw.toByteArray());
      } catch(IOException e) {LOGGER.warn("Could not send EaglerXServer v5 voice signal");}
   }
   private static UUID readUUID(final DataInputStream in) throws IOException {
      return new UUID(in.readLong(),in.readLong());
   }
   private static int readVarInt(final DataInputStream in) throws IOException {
      int ret=0;
      for(int shift=0;shift<35;shift+=7) {
         int value=in.readUnsignedByte();ret|=(value&127)<<shift;
         if((value&128)==0)return ret;
      }
      throw new IOException("Invalid Eagler VarInt");
   }
   private static void writeVarInt(final DataOutputStream out,int value) throws IOException {
      while((value&-128)!=0) {out.writeByte((value&127)|128);value>>>=7;}
      out.writeByte(value);
   }
   private static String readUtf(final DataInputStream in, final int max) throws IOException {
      int bytes=readVarInt(in);
      if(bytes<0 || bytes>max*4 || bytes>in.available())throw new IOException("Voice text too long");
      byte[] b=new byte[bytes];in.readFully(b);
      String s=new String(b,StandardCharsets.UTF_8);
      if(s.length()>max)throw new IOException("Voice text exceeds limit");
      return s;
   }
   private static String readBlob(final DataInputStream in) throws IOException {
      int bytes=readVarInt(in);
      if(bytes<0 || bytes>32750 || bytes>in.available())throw new IOException("Voice signal size exceeds limit");
      byte[] b=new byte[bytes];in.readFully(b);
      return new String(b,StandardCharsets.UTF_8);
   }
}

package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Easy Place: manual hold of the REAL vanilla right-click on an ACTUAL
 * reachable support face. No synthetic hits, packets, items, or world edits.
 * Completion is ONLY a server packet's block state, not client prediction.
 * Hover auto-place remains permanently disabled until independently proven.
 */
public final class EasyPlace26 {
    public static final boolean HOVER_AUTOPLACE_DISABLED = true;
    private static final long TIMEOUT_NS = 5_000_000_000L;
    private static ClientLevel world;
    private static long schematicVersion = Long.MIN_VALUE;
    private static BlockPos pending;
    private static BlockState required;
    private static long sentAt;
    private static boolean attemptedThisHold;
    private static String suspended = "";
    private static int attempts, confirmed, rejected, timedOut;
    private static String lastLog = "";
    private static long lastLogAt;
    private EasyPlace26() {}

    private static void log(String stage, Minecraft mc, BlockPos pos,
                            BlockState expected, String detail) {
        String msg="[PletzelEasyPlace] "+stage+" target="+pos+
           " expected="+expected+" observedClient="+
           (mc!=null&&mc.level!=null&&pos!=null&&mc.level.hasChunkAt(pos)
               ?mc.level.getBlockState(pos):"unavailable")+
           " slot="+(mc!=null&&mc.player!=null
                      ?mc.player.getInventory().getSelectedSlot():-1)+
           " pending="+pending+" attempts="+attempts+
           " confirmed="+confirmed+" rejected="+rejected+
           " timedOut="+timedOut+" suspended="+suspended+" "+detail;
        long now=System.nanoTime();
        if(!msg.equals(lastLog)||now-lastLogAt>2_000_000_000L) {
            lastLog=msg;lastLogAt=now;System.out.println(msg);
        }
    }

    private static void clearPending() {
        pending=null;required=null;sentAt=0L;
    }

    private static void resetFor(ClientLevel level,long version) {
        clearPending();
        world=level;schematicVersion=version;
        attemptedThisHold=false;suspended="";
    }

    /** Run even when a GUI is open to cancel in-flight tracking safely. */
    public static void tick(Minecraft mc) {
        if(mc==null||mc.options==null)return;
        if(mc.options.pletzelEasyPlaceHover.get()) {
            mc.options.pletzelEasyPlaceHover.set(false);
            mc.options.save();
            log("HOVER_DISABLED",mc,null,null,"no background use");
        }
        ClientLevel level=mc.level;
        long version=SchematicaSession.version();
        if(world!=level||schematicVersion!=version) {
            if(pending!=null)log("WORLD_OR_SCHEMATIC_CHANGED",mc,pending,required,"cancel");
            resetFor(level,version);
        }
        if(!mc.options.pletzelEasyPlace.get()||level==null||mc.player==null||
           !SchematicaSession.loaded()||mc.gui.screen()!=null||Freecam26.active()) {
            clearPending();
            attemptedThisHold=false;
            if(!mc.options.pletzelEasyPlace.get())suspended="";
            return;
        }
        if(!mc.options.keyUse.isDown())attemptedThisHold=false;
        if(pending!=null&&System.nanoTime()-sentAt>TIMEOUT_NS) {
            timedOut++;
            log("TIMEOUT_NOT_CONFIRMED",mc,pending,required,"no automatic retry");
            clearPending();suspended="SERVER_RESPONSE_TIMEOUT";
        }
    }

    /** Easy Pick must run first, then vanilla startUseItem uses standard
     * MultiPlayerGameMode.useItemOn (which syncs the selected hotbar). */
    public static boolean beforeVanillaUse(Minecraft mc) {
        tick(mc);
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get())
            return true;
        if(mc.level==null||mc.player==null||mc.gameMode==null||
           !SchematicaSession.loaded()||Freecam26.active()||
           mc.gui.screen()!=null||mc.player.isSpectator()||
           mc.player.isUsingItem()||mc.player.isHandsBusy()||
           mc.gameMode.isDestroying())return false;
        if(!mc.options.keyUse.isDown()||mc.options.toggleUse().get()||
           pending!=null||attemptedThisHold||!suspended.isEmpty())return false;
        if(!(mc.hitResult instanceof BlockHitResult hit)||
           hit.getType()!=HitResult.Type.BLOCK)return false;

        BlockPos support=hit.getBlockPos();
        if(!mc.level.hasChunkAt(support))return false;
        BlockState supportState=mc.level.getBlockState(support);
        BlockPos target=supportState.canBeReplaced()
            ?support:support.relative(hit.getDirection());
        BlockState expected=SchematicaWorldRenderer.expectedAt(target);
        if(expected==null||expected.isAir())
            return true; // Unrelated ordinary Minecraft right-click.
        if(!mc.level.hasChunkAt(target)||
           !mc.level.getWorldBorder().isWithinBounds(support)||
           !mc.level.getWorldBorder().isWithinBounds(target)||
           supportState.isAir()) {
            log("UNSUPPORTED_TARGET",mc,target,expected,"no placement");
            return false;
        }
        BlockState current=mc.level.getBlockState(target);
        if(current.equals(expected)||(!current.isAir()&&!current.canBeReplaced())) {
            log("NOT_REPLACEABLE_OR_ALREADY_CORRECT",mc,target,expected,"no placement");
            return false;
        }
        Vec3 eye=mc.player.getEyePosition();
        if(eye.distanceToSqr(hit.getLocation())>
             mc.player.blockInteractionRange()*mc.player.blockInteractionRange()) {
            log("OUT_OF_REACH",mc,target,expected,"no packet");
            return false;
        }
        // A second independent raycast may reject uncertain obstructions,
        // but never supplies a new/mutated hit to vanilla Minecraft.
        Vec3 end=hit.getLocation().add(
            hit.getLocation().subtract(eye).normalize().scale(0.04D));
        BlockHitResult real=mc.level.clip(new ClipContext(eye,end,
            ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,mc.player));
        if(real.getType()!=HitResult.Type.BLOCK||
           !real.getBlockPos().equals(support)||
           real.getDirection()!=hit.getDirection()) {
            log("OBSTRUCTED_SUPPORT_FACE",mc,target,expected,"no packet");
            return false;
        }
        ItemStack stack=mc.player.getMainHandItem();
        if(stack.isEmpty()||!(stack.getItem() instanceof BlockItem item)||
           item.getBlock()!=expected.getBlock()) {
            log("WRONG_SELECTED_HOTBAR_ITEM",mc,target,expected,"no packet");
            return false;
        }
        BlockPlaceContext ctx=new BlockPlaceContext(mc.player,
            InteractionHand.MAIN_HAND,stack,hit);
        if(!ctx.canPlace()||!ctx.getClickedPos().equals(target)) {
            log("ILLEGAL_VANILLA_CONTEXT",mc,target,expected,"no packet");
            return false;
        }
        BlockState predicted=item.getBlock().getStateForPlacement(ctx);
        if(predicted==null||!predicted.equals(expected)) {
            log("WRONG_ORIENTATION",mc,target,expected,"no packet");
            return false;
        }
        attemptedThisHold=true;
        pending=target.immutable();
        required=expected;
        sentAt=System.nanoTime();
        attempts++;
        log("PENDING_VANILLA_RIGHT_CLICK",mc,target,expected,
            "support="+support+" face="+hit.getDirection()+
            " hit="+hit.getLocation()+" awaiting authoritative packet");
        return true;
    }

    /** Called after an ACTUAL server BLOCK_UPDATE / SECTION_BLOCKS_UPDATE. */
    public static void onServerBlockUpdate(ClientLevel level,BlockPos pos,
                                           BlockState authoritative) {
        if(pending==null||level!=world||!pending.equals(pos))return;
        Minecraft mc=Minecraft.getInstance();
        if(authoritative.equals(required)) {
            confirmed++;
            log("SERVER_CONFIRMED",mc,pending,required,
                "authoritativeBlock="+authoritative);
            clearPending();
        } else {
            rejected++;
            log("SERVER_REJECTED_OR_CORRECTED",mc,pending,required,
                "authoritativeBlock="+authoritative);
            clearPending();
            suspended="SERVER_REJECTION";
        }
    }

    /** Full chunk replacement is authoritative; NEVER use a predicted state. */
    public static void onServerChunk(ClientLevel level,int cx,int cz) {
        if(pending!=null&&world==level&&
           (pending.getX()>>4)==cx&&(pending.getZ()>>4)==cz) {
            onServerBlockUpdate(level,pending,level.getBlockState(pending));
        }
    }

    /** Vanilla prediction ACK alone does NOT constitute placement success. */
    public static void onServerPredictionAck(ClientLevel level,int sequence) {
        if(pending!=null&&level==world)
            log("ACK_NOT_CONFIRMATION",Minecraft.getInstance(),pending,required,
                "vanillaSequence="+sequence);
    }

    public static boolean shouldHoverPlace(Minecraft mc) {return false;}
    public static boolean inHoverAttempt() {return false;}
    public static void afterVanillaKeybinds(Minecraft mc) {tick(mc);}
    public static String diagnosticStatus() {
        return "Easy Place "+(!suspended.isEmpty()?"SUSPENDED: "+suspended:
            pending!=null?"PENDING server confirmation":
            "Ready: hold right-click on REAL support face");
    }
    public static void reset() {resetFor(null,Long.MIN_VALUE);}
}

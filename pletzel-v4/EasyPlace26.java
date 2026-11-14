package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
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
    public static final boolean HOVER_AUTOPLACE_DISABLED = false;
    private static final long TIMEOUT_NS = 5_000_000_000L;
    private static ClientLevel world;
    private static long schematicVersion = Long.MIN_VALUE;
    private static BlockPos pending;
    private static BlockState required;
    private static long sentAt;
    private static BlockPos pendingSupport;
    private static net.minecraft.core.Direction pendingFace;
    private static int pendingSequence = -1;
    private static boolean predictionAcked;
    private static BlockState observedByServer;
    // Keep unknown/corrected placement visibly unconfirmed even after a
    // timeout/rejection until vanilla prediction reconciliation catches up.
    private static BlockPos unresolvedVisual;
    private static BlockState correctionServerState;
    private static final java.util.LinkedHashSet<BlockPos> rejectedTargets = new java.util.LinkedHashSet<>();
    private static boolean previouslyEnabled;
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
           " pending="+pending+" sequence="+pendingSequence+
           " predictionAck="+predictionAcked+" serverObserved="+observedByServer+
           " attempts="+attempts+
           " confirmed="+confirmed+" rejected="+rejected+
           " timedOut="+timedOut+" suspended="+suspended+" "+detail;
        long now=System.nanoTime();
        if(!msg.equals(lastLog)||now-lastLogAt>2_000_000_000L) {
            lastLog=msg;lastLogAt=now;System.out.println(msg);
        }
    }

    private static void clearPending() {
        pending=null;required=null;sentAt=0L;
        pendingSupport=null;pendingFace=null;
        pendingSequence=-1;predictionAcked=false;observedByServer=null;
    }

    private static void resetFor(ClientLevel level,long version) {
        clearPending();
        world=level;schematicVersion=version;
        rejectedTargets.clear();suspended="";
        unresolvedVisual=null;correctionServerState=null;
    }

    /** Run even when a GUI is open to cancel in-flight tracking safely. */
    public static void tick(Minecraft mc) {
        if(mc==null||mc.options==null)return;
        ClientLevel level=mc.level;
        long version=SchematicaSession.version();
        if(world!=level||schematicVersion!=version) {
            if(pending!=null)log("WORLD_OR_SCHEMATIC_CHANGED",mc,pending,required,"cancel");
            resetFor(level,version);
        }
        boolean enabled=mc.options.pletzelEasyPlace.get();
        if(enabled&&!previouslyEnabled) {
            rejectedTargets.clear();suspended="";
            unresolvedVisual=null;correctionServerState=null;
        }
        previouslyEnabled=enabled;
        if(!mc.options.pletzelEasyPlace.get()||level==null||mc.player==null||
           !SchematicaSession.loaded()||mc.gui.screen()!=null||Freecam26.active()) {
            if(pending!=null) {
                unresolvedVisual=pending;
                correctionServerState=null;
                // Opening a GUI or switching into Freecam while an action is
                // outstanding must not silently allow a new placement.
                if(mc.options.pletzelEasyPlace.get()&&level!=null)
                    suspended="INTERRUPTED_CONTEXT_OR_GUI";
                log("INTERRUPTED_PENDING",mc,pending,required,
                    "stopped; user must explicitly toggle Easy Place OFF/ON");
            }
            clearPending();
            if(!mc.options.pletzelEasyPlace.get()) {
                suspended="";
                rejectedTargets.clear();
            }
            return;
        }
        if(pending!=null&&predictionAcked&&observedByServer!=null)
            finalizeIfBothVerified(level);
        if(pending!=null&&System.nanoTime()-sentAt>TIMEOUT_NS) {
            timedOut++;
            log("TIMEOUT_NOT_CONFIRMED",mc,pending,required,"no automatic retry");
            unresolvedVisual=pending;
            correctionServerState=observedByServer;
            rejectedTargets.add(pending);
            clearPending();suspended="SERVER_RESPONSE_TIMEOUT";
        }
    }

    /** ON: assistant owns schematic placement, never regular off-schematic clicks.
     * Shift+right-click is the explicit vanilla manual-use override.
     * Multiplayer is never assisted until dedicated-server safety is verified.
     */
    public static boolean beforeVanillaUse(Minecraft mc) {
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get())return true;
        if(mc.isMultiplayerServer())return true;
        if(mc.player!=null&&mc.player.isSecondaryUseActive())return true;
        return !SchematicaSession.loaded();
    }

    /** Called exclusively from the VANILLA MultiPlayerGameMode prediction
     * lambda for the actual matching main-hand item-use. No custom packet. */
    public static void onVanillaSequence(Minecraft mc,int sequence,
                                          InteractionHand hand,BlockHitResult hit) {
        if(pending==null||mc==null||mc.level!=world||
           hand!=InteractionHand.MAIN_HAND||pendingSupport==null||
           !pendingSupport.equals(hit.getBlockPos())||
           pendingFace!=hit.getDirection()||pendingSequence>=0)return;
        pendingSequence=sequence;
        log("VANILLA_PACKET_SEQUENCE",mc,pending,required,
            "sequence="+sequence+" clicked="+hit.getBlockPos());
    }

    private static void finalizeIfBothVerified(ClientLevel level) {
        if(pending==null||!predictionAcked||observedByServer==null)return;
        Minecraft mc=Minecraft.getInstance();
        if(!observedByServer.equals(required)) {
            rejected++;
            log("SERVER_REJECTED_OR_CORRECTED",mc,pending,required,
                "authoritativeBlock="+observedByServer);
            unresolvedVisual=pending;
            correctionServerState=observedByServer;
            rejectedTargets.add(pending);
            clearPending();
        } else if(level.getBlockState(pending).equals(required)) {
            // A server update + the matching vanilla ACK reconciled the local
            // prediction. Neither local prediction nor ACK alone can pass.
            confirmed++;
            log("SERVER_CONFIRMED_AND_RECONCILED",mc,pending,required,
                "authoritative="+observedByServer+" sequence="+pendingSequence);
            clearPending();
        } else {
            log("WAITING_FOR_CLIENT_RECONCILIATION",mc,pending,required,
                "authoritative="+observedByServer);
        }
    }

    /** Only an actual received server packet may set server-observed state.
     * The packet may arrive before or after its prediction ACK. */
    public static void onServerBlockUpdate(ClientLevel level,BlockPos pos,
                                           BlockState authoritative) {
        if(level!=world)return;
        if(unresolvedVisual!=null&&unresolvedVisual.equals(pos)) {
            correctionServerState=authoritative;
        }
        if(pending==null||!pending.equals(pos))return;
        observedByServer=authoritative;
        log("SERVER_BLOCK_UPDATE_RECEIVED",Minecraft.getInstance(),pending,
            required,"authoritative="+authoritative);
        if(!authoritative.equals(required)) {
            rejected++;
            log("SERVER_REJECTED_OR_CORRECTED",Minecraft.getInstance(),
                pending,required,"authoritativeBlock="+authoritative);
            unresolvedVisual=pending;
            correctionServerState=authoritative;
            rejectedTargets.add(pending);
            clearPending();
        } else {
            finalizeIfBothVerified(level);
        }
    }

    /** A fresh chunk invalidates any earlier placement prediction. Its
     * post-apply ClientLevel state is NOT accepted as independent evidence:
     * a local predicted block might still be visible. Fail closed instead. */
    public static void onServerChunk(ClientLevel level,int cx,int cz) {
        if(pending!=null&&world==level&&
           (pending.getX()>>4)==cx&&(pending.getZ()>>4)==cz) {
            log("CHUNK_REPLACED_PENDING_NOT_CONFIRMED",
                Minecraft.getInstance(),pending,required,
                "no success inferred from client chunk state");
            unresolvedVisual=pending;
            correctionServerState=null;
            clearPending();
            suspended="CHUNK_REPLACED_DURING_PLACEMENT";
        }
    }

    /** Only an ACK covering this exact vanilla interaction sequence counts;
     * still requires authoritative target update and reconciled client world. */
    public static void onServerPredictionAck(ClientLevel level,int sequence) {
        if(pending==null||level!=world)return;
        if(pendingSequence>=0&&sequence>=pendingSequence) {
            predictionAcked=true;
            log("MATCHING_VANILLA_ACK",Minecraft.getInstance(),pending,required,
                "ackSequence="+sequence+" requires server block update");
            finalizeIfBothVerified(level);
        }
    }

    public static boolean shouldHoverPlace(Minecraft mc) {
        return mc!=null&&mc.options!=null&&mc.options.pletzelEasyPlace.get()&&
            mc.options.pletzelEasyPlaceHover.get()&&!mc.isMultiplayerServer();
    }
    public static boolean inHoverAttempt() {return false;}
    /** A schematic ghost is AIR, so vanilla hitResult cannot select it.
     * Walk only the player's REAL view ray; stop at solid obstructions.
     * As a fallback, aiming directly at a real support face also works.
     */
    private static BlockPos ghostTarget(Minecraft mc) {
        Vec3 eye=mc.player.getEyePosition();
        Vec3 ray=mc.player.getLookAngle();
        double range=mc.player.blockInteractionRange();
        BlockPos prior=null;
        for(double d=0.125D;d<=range;d+=0.125D) {
            BlockPos pos=BlockPos.containing(eye.add(ray.scale(d)));
            if(pos.equals(prior))continue;
            prior=pos;
            if(!mc.level.hasChunkAt(pos))return null;
            BlockState expected=SchematicaWorldRenderer.expectedAt(pos);
            if(expected!=null&&!expected.isAir())return pos;
            if(!mc.level.getBlockState(pos).getCollisionShape(mc.level,pos).isEmpty())break;
        }
        if(mc.hitResult instanceof BlockHitResult hit&&
           hit.getType()==HitResult.Type.BLOCK) {
            BlockPos support=hit.getBlockPos();
            if(!mc.level.hasChunkAt(support))return null;
            BlockPos target=mc.level.getBlockState(support).canBeReplaced()
                ?support:support.relative(hit.getDirection());
            BlockState expected=SchematicaWorldRenderer.expectedAt(target);
            if(expected!=null&&!expected.isAir())return target;
        }
        return null;
    }

    /** Find a physically visible, nonreplaceable real neighboring block and
     * have Minecraft itself raytrace the face. Never place through solids.
     */
    private static BlockHitResult supportHit(Minecraft mc,BlockPos target) {
        if(!mc.level.hasChunkAt(target)||
           !mc.level.getWorldBorder().isWithinBounds(target))return null;
        Vec3 eye=mc.player.getEyePosition();
        double reach=mc.player.blockInteractionRange();
        for(Direction side:Direction.values()) {
            BlockPos support=target.relative(side);
            if(!mc.level.hasChunkAt(support)||
               !mc.level.getWorldBorder().isWithinBounds(support))continue;
            BlockState supportState=mc.level.getBlockState(support);
            if(supportState.isAir()||supportState.canBeReplaced())continue;
            Vec3 face=Vec3.atCenterOf(target).add(
                0.5D*side.getStepX(),
                0.5D*side.getStepY(),
                0.5D*side.getStepZ());
            if(eye.distanceToSqr(face)>reach*reach)continue;
            Vec3 intoSupport=face.add(
                0.02D*side.getStepX(),
                0.02D*side.getStepY(),
                0.02D*side.getStepZ());
            BlockHitResult hit=mc.level.clip(new ClipContext(
                eye,intoSupport,ClipContext.Block.COLLIDER,
                ClipContext.Fluid.NONE,mc.player));
            if(hit.getType()==HitResult.Type.BLOCK&&
               hit.getBlockPos().equals(support)&&
               hit.getDirection()==side.getOpposite())return hit;
        }
        return null;
    }

    /** Independent Easy Pick: only pre-existing hotbar slots are selectable.
     * With Easy Pick OFF this checks exactly the currently held item.
     */
    private static boolean selectLegalItem(Minecraft mc,BlockPos target,
                                            BlockState wanted,BlockHitResult hit) {
        int selected=mc.player.getInventory().getSelectedSlot();
        boolean easyPick=mc.options.pletzelEasyPick.get();
        for(int i=easyPick?0:selected;i<(easyPick?9:selected+1);i++) {
            ItemStack stack=mc.player.getInventory().getItem(i);
            if(stack.isEmpty()||!(stack.getItem() instanceof BlockItem item)||
               item.getBlock()!=wanted.getBlock())continue;
            BlockPlaceContext ctx=new BlockPlaceContext(
                mc.player,InteractionHand.MAIN_HAND,stack,hit);
            if(!ctx.canPlace()||!ctx.getClickedPos().equals(target))continue;
            BlockState predicted=item.getBlock().getStateForPlacement(ctx);
            if(predicted==null||!predicted.equals(wanted))continue;
            if(i!=selected) {
                mc.player.getInventory().setSelectedSlot(i);
                System.out.println("[PletzelEasyPick] SELECT slot="+i+
                    " target="+target+" expected="+wanted.getBlock());
            }
            return true;
        }
        return false;
    }

    /** Activated on every game tick, NOT on right-click transitions.
     * After one authoritatively reconciled placement, a new ghost target
     * can be processed without releasing Right Click. No click at all is
     * needed in opt-in Hover. Shift+right-click bypasses assistance.
     */
    public static void afterVanillaKeybinds(Minecraft mc) {
        tick(mc);
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get()||
           mc.level==null||mc.player==null||mc.gameMode==null||
           !SchematicaSession.loaded()||Freecam26.active()||
           mc.gui.screen()!=null||mc.isMultiplayerServer())return;
        boolean hover=mc.options.pletzelEasyPlaceHover.get();
        if(!hover&&(!mc.options.keyUse.isDown()||
                    mc.options.toggleUse().get()))return;
        if(mc.player.isSecondaryUseActive()||mc.player.isSpectator()||
           mc.player.isUsingItem()||mc.player.isHandsBusy()||
           mc.gameMode.isDestroying()||pending!=null||
           !suspended.isEmpty())return;
        BlockPos target=ghostTarget(mc);
        if(target==null||rejectedTargets.contains(target))return;
        BlockState wanted=SchematicaWorldRenderer.expectedAt(target);
        if(wanted==null||wanted.isAir()||!mc.level.hasChunkAt(target))return;
        BlockState actual=mc.level.getBlockState(target);
        if(actual.equals(wanted)||(!actual.isAir()&&!actual.canBeReplaced()))return;
        BlockHitResult hit=supportHit(mc,target);
        if(hit==null) {
            log("NO_LEGAL_SUPPORT",mc,target,wanted,"no vanilla interaction");
            return;
        }
        if(!selectLegalItem(mc,target,wanted,hit)) {
            log("NO_CORRECT_HOTBAR_ITEM",mc,target,wanted,
                "EasyPick="+mc.options.pletzelEasyPick.get());
            return;
        }
        // Both support and target were checked using actual world states.
        // Vanilla BlockPlaceContext must agree on the EXACT schematic cell.
        BlockPlaceContext ctx=new BlockPlaceContext(
            mc.player,InteractionHand.MAIN_HAND,mc.player.getMainHandItem(),hit);
        if(!ctx.canPlace()||!ctx.getClickedPos().equals(target))return;
        pending=target.immutable();
        required=wanted;
        pendingSupport=hit.getBlockPos().immutable();
        pendingFace=hit.getDirection();
        pendingSequence=-1;
        predictionAcked=false;
        observedByServer=null;
        sentAt=System.nanoTime();
        attempts++;
        log("PENDING_VANILLA_RIGHT_CLICK",mc,target,wanted,
            "mode="+(hover?"HOVER":"CONTINUOUS_HOLD")+
            " support="+pendingSupport+" face="+pendingFace);
        // Native placement includes inventory-slot sync, vanilla prediction,
        // actual packet sequence and its ordinary server validation.
        // No blocks or packets are constructed or written by this helper.
        mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,hit);
    }
    /** Hologram renderer MUST NOT treat a locally predicted solid block as
     * complete while its authoritative server response is outstanding. */
    public static boolean isPlacementPending(BlockPos pos) {
        if(pos==null)return false;
        if(pending!=null&&pending.equals(pos))return true;
        if(unresolvedVisual!=null&&unresolvedVisual.equals(pos)) {
            // Once actual world equals server correction, normal ghost AIR /
            // correct-block rendering resumes. Never fake a solid block.
            Minecraft mc=Minecraft.getInstance();
            return correctionServerState==null||mc==null||mc.level==null||
                !mc.level.hasChunkAt(pos)||
                !mc.level.getBlockState(pos).equals(correctionServerState);
        }
        return false;
    }

    public static String diagnosticStatus() {
        return "Easy Place "+(!suspended.isEmpty()?"SUSPENDED: "+suspended:
            pending!=null?"PENDING server confirmation":
            "Ready: "+(Minecraft.getInstance().options.pletzelEasyPlaceHover.get()?
                "Hover a schematic ghost":"Hold right-click and aim at ghosts"));
    }
    public static void reset() {resetFor(null,Long.MIN_VALUE);}
}

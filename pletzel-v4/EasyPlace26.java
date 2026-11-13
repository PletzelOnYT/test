package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
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
 * Legitimate ghost-first selection, then independent *real* support-face
 * raycast. Never creates inventory, world blocks or packets. Minecraft's
 * existing startUseItem() handles the actual right-click and server sync.
 */
public final class EasyPlace26 {
    private static final class Plan {
        final BlockPos target;
        final BlockState required;
        final BlockHitResult realSupportHit;
        Plan(BlockPos pos,BlockState state,BlockHitResult hit) {
            target=pos; required=state; realSupportHit=hit;
        }
    }
    private static boolean autoPending,activeHoverAttempt;
    private static Plan hoveredPlan;
    private static BlockPos awaitingTarget;
    private static BlockState awaitingState;
    private static int awaitingTicks;
    private static HitResult originalHit;
    private static long lastAutoSignature=Long.MIN_VALUE;
    private static String lastDiagnostic="";
    private static long lastDiagnosticTime;
    private EasyPlace26(){}

    private static void diagnostic(String stage, BlockPos target, Minecraft mc) {
        long now=System.nanoTime();
        String message="[PletzelEasyPlace] BLOCKED stage="+stage+
            " target="+target+" enabled="+mc.options.pletzelEasyPlace.get()+
            " hover="+mc.options.pletzelEasyPlaceHover.get()+
            " held="+(mc.player==null?"none":mc.player.getMainHandItem().getItem())+
            " pick="+mc.options.pletzelEasyPick.get();
        // Show the FIRST specific rejection while targeting; throttle repeats.
        if(!message.equals(lastDiagnostic)||now-lastDiagnosticTime>1_500_000_000L) {
            lastDiagnostic=message;lastDiagnosticTime=now;
            System.out.println(message);
        }
    }

    /** Raycast the transparent schematic in camera space, not the real-world
     *  block hit. This also works when Minecraft.hitResult is a MISS because
     *  ghosts do not collide and the player has not placed a support yet. */
    private static BlockPos aimedGhost(Minecraft mc) {
        if(mc==null||mc.level==null||mc.player==null||mc.gui.screen()!=null||
           mc.player.isSpectator()||Freecam26.active()||
           !SchematicaSession.loaded())return null;
        Vec3 eye=mc.player.getEyePosition();
        Vec3 direction=mc.player.getLookAngle();
        double reach=mc.player.blockInteractionRange();
        if(reach<=0.0)return null;
        BlockPos previous=null;
        for(double distance=0.12;distance<=reach;distance+=0.125) {
            Vec3 cursor=eye.add(direction.scale(distance));
            BlockPos position=BlockPos.containing(cursor);
            if(position.equals(previous))continue;
            previous=position;
            if(!mc.level.hasChunkAt(position))return null;
            BlockState required=SchematicaWorldRenderer.expectedAt(position);
            if(required==null||required.isAir())continue;
            // A real nearer wall occludes the ghost. Do not place through it.
            BlockHitResult first=mc.level.clip(new ClipContext(eye,cursor,
                ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,mc.player));
            if(first.getType()==HitResult.Type.BLOCK &&
               !first.getBlockPos().equals(position) &&
               eye.distanceToSqr(first.getLocation())+0.01 <
               eye.distanceToSqr(cursor)) {
                diagnostic("BLOCKED_BY_REAL_WALL",position,mc);
                return null;
            }
            return position;
        }
        if(mc.options!=null&&mc.options.pletzelEasyPlace.get())
            diagnostic("NO_SCHEMATIC_GHOST_UNDER_CROSSHAIR",null,mc);
        return null;
    }

    /** Predict exact vanilla block state with the ITEM actually available,
     *  not only a block registry ID. Test all nine hotbar slots only when Easy
     *  Pick is explicitly enabled. */
    private static boolean itemCanPlace(Minecraft mc,BlockPos target,
                                         BlockState required,BlockHitResult hit) {
        int start=mc.options.pletzelEasyPick.get()?0:mc.player.getInventory().getSelectedSlot();
        int end=mc.options.pletzelEasyPick.get()?9:start+1;
        for(int i=start;i<end;i++) {
            ItemStack stack=mc.player.getInventory().getItem(i);
            if(stack.isEmpty()||!(stack.getItem() instanceof BlockItem item)||
               item.getBlock()!=required.getBlock())continue;
            BlockPlaceContext context=new BlockPlaceContext(mc.player,
                 InteractionHand.MAIN_HAND,stack,hit);
            if(!context.canPlace()||!context.getClickedPos().equals(target))continue;
            BlockState predicted=item.getBlock().getStateForPlacement(context);
            if(predicted!=null&&predicted.equals(required))return true;
        }
        return false;
    }

    /** Every accepted face corresponds to a real loaded Minecraft block
     *  reached by the client's ordinary collision raycast. No virtual
     *  BlockHitResult or fake support surface is ever sent to a server. */
    private static Plan plan(Minecraft mc,BlockPos target) {
        if(target==null)return null;
        BlockState required=SchematicaWorldRenderer.expectedAt(target);
        if(required==null)return null;
        BlockState world=mc.level.getBlockState(target);
        if(world.equals(required)){diagnostic("ALREADY_CORRECT",target,mc);return null;}
        if(!world.isAir()&&!world.canBeReplaced()) {
            diagnostic("MINE_WRONG_REAL_BLOCK_FIRST",target,mc);return null;
        }
        if(!mc.level.getWorldBorder().isWithinBounds(target)) {
            diagnostic("WORLD_BORDER",target,mc);return null;
        }
        Vec3 eye=mc.player.getEyePosition();
        double reach=mc.player.blockInteractionRange();
        boolean sawRealFace=false;
        boolean hadMatchingItem=false;
        for(Direction offset:Direction.values()) {
            BlockPos support=target.relative(offset);
            if(!mc.level.hasChunkAt(support))continue;
            BlockState supportState=mc.level.getBlockState(support);
            if(supportState.isAir()||supportState.canBeReplaced())continue;
            Direction exposed=offset.getOpposite();
            Vec3 contact=Vec3.atCenterOf(support).add(
                exposed.getStepX()*0.4999D,
                exposed.getStepY()*0.4999D,
                exposed.getStepZ()*0.4999D);
            // Trace strictly to a genuine collision surface. No through-wall
            // placement even when the ghost itself is visible.
            Vec3 to=contact.add(contact.subtract(eye).normalize().scale(0.035D));
            BlockHitResult hit=mc.level.clip(new ClipContext(eye,to,
                ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,mc.player));
            if(hit.getType()!=HitResult.Type.BLOCK ||
               !hit.getBlockPos().equals(support) ||
               hit.getDirection()!=exposed ||
               eye.distanceToSqr(hit.getLocation())>reach*reach)continue;
            sawRealFace=true;
            if(!itemCanPlace(mc,target,required,hit))continue;
            hadMatchingItem=true;
            return new Plan(target,required,hit);
        }
        diagnostic(!sawRealFace?"NO_REACHABLE_REAL_SUPPORT_FACE":
                   !hadMatchingItem?"MISSING_ITEM_OR_INVALID_BLOCK_ORIENTATION":
                   "NO_LEGAL_FACE",target,mc);
        return null;
    }

    public static boolean beforeVanillaUse(Minecraft mc) {
        boolean hover=autoPending;
        autoPending=false;
        activeHoverAttempt=hover;
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get())return !hover;
        if(Freecam26.active())return false;
        if(!SchematicaSession.loaded()||mc.options.toggleUse().get())return !hover;
        if(mc.level==null||mc.player==null||mc.player.isHandsBusy()||
           mc.player.isUsingItem())return !hover;
        if(!hover&&!mc.options.keyUse.isDown())return true;
        BlockPos ghost=aimedGhost(mc);
        if(ghost==null)return !hover; // other manual vanilla interactions work
        Plan candidate=hover&&hoveredPlan!=null&&
            hoveredPlan.target.equals(ghost)?hoveredPlan:plan(mc,ghost);
        hoveredPlan=null;
        if(candidate==null)return false;
        // The hit is an authentic ClientLevel.clip() result on a REAL support
        // block. Put it through the unmodified Minecraft.startUseItem path.
        originalHit=mc.hitResult;
        mc.hitResult=candidate.realSupportHit;
        if(awaitingTarget==null||!awaitingTarget.equals(candidate.target)) {
            awaitingTarget=candidate.target;
            awaitingState=candidate.required;
            awaitingTicks=0;
        }
        System.out.println("[PletzelEasyPlace] VANILLA_ATTEMPT mode="+
            (hover?"hover":"hold")+" target="+candidate.target+
            " support="+candidate.realSupportHit.getBlockPos()+
            " face="+candidate.realSupportHit.getDirection()+
            " expected="+candidate.required.getBlock()+
            " item="+mc.player.getMainHandItem().getItem());
        return true;
    }

    public static boolean inHoverAttempt() {return activeHoverAttempt;}

    /** Called from Minecraft.handleKeybinds() *after* vanilla use processing.
     *  The ordinary crosshair hit is restored before the game is rendered. */
    public static void afterVanillaKeybinds(Minecraft mc) {
        if(originalHit!=null) {
            mc.hitResult=originalHit;
            originalHit=null;
        }
        activeHoverAttempt=false;
        if(awaitingTarget!=null&&mc.level!=null) {
            if(mc.level.getBlockState(awaitingTarget).equals(awaitingState)) {
                System.out.println("[PletzelEasyPlace] CLIENT_WORLD_MATCHED target="+awaitingTarget+
                    " (server confirmation requires authoritative feedback)");
                awaitingTarget=null;awaitingState=null;
            } else if(++awaitingTicks>50) {
                System.out.println("[PletzelEasyPlace] NOT_CONFIRMED target="+awaitingTarget+
                    " expected="+awaitingState.getBlock()+
                    " actual="+mc.level.getBlockState(awaitingTarget).getBlock());
                awaitingTarget=null;awaitingState=null;
            }
        }
    }

    /** Hover uses the exact SAME four-tick vanilla cooldown and real use.
     *  A target is never retried in a loop just because its server response
     *  is delayed or denied. Retarget or modify the world to allow retry. */
    public static boolean shouldHoverPlace(Minecraft mc) {
        autoPending=false;
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get()||
           !mc.options.pletzelEasyPlaceHover.get()||Freecam26.active()||
           mc.player==null||mc.options.keyUse.isDown())return false;
        BlockPos ghost=aimedGhost(mc);
        if(ghost==null) {
            lastAutoSignature=Long.MIN_VALUE;hoveredPlan=null;
            return false;
        }
        BlockState world=mc.level.getBlockState(ghost);
        long signature=ghost.asLong()^(SchematicaSession.version()<<19)^
            ((long)world.hashCode()<<37)^
            ((long)mc.player.getInventory().getSelectedSlot()<<45);
        if(signature==lastAutoSignature)return false;
        if(awaitingTarget!=null&&awaitingTarget.equals(ghost) &&
           !mc.level.getBlockState(ghost).equals(awaitingState))
            return false; // pending server state: no packet spam
        Plan attempt=plan(mc,ghost);
        if(attempt==null)return false;
        lastAutoSignature=signature;
        hoveredPlan=attempt;
        autoPending=true;
        return true;
    }

    public static void reset() {
        autoPending=false;activeHoverAttempt=false;hoveredPlan=null;
        originalHit=null;awaitingTarget=null;awaitingState=null;
        lastAutoSignature=Long.MIN_VALUE;
    }
}

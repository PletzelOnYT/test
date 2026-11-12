package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Easy Place uses ONLY the real vanilla pick hit, the real support face and
 * Minecraft.startUseItem(). No fake BlockHitResult, spoofed placement packet,
 * remote chunk access, world block writes or extended reach are permitted.
 *
 * This is deliberately conservative: a ghost floating in air without a
 * vanilla-hittable support block cannot be placed by Easy Place.
 */
public final class EasyPlace26 {
    private static boolean autoPending;
    private static boolean activeHoverAttempt;
    private static long lastAutoSignature=Long.MIN_VALUE;
    private static long lastDiagnostic;
    private EasyPlace26() {}

    private static BlockPos candidate(Minecraft mc) {
        if(mc==null||mc.level==null||mc.player==null||mc.options==null||
           mc.gui.screen()!=null||mc.player.isSpectator()||Freecam26.active()||
           !SchematicaSession.loaded()||!mc.options.pletzelEasyPlace.get())return null;
        if(!(mc.hitResult instanceof BlockHitResult hit))return null;
        BlockPos clicked=hit.getBlockPos();
        if(!mc.level.hasChunkAt(clicked))return null;
        BlockPos next=clicked.relative(hit.getDirection());
        BlockPos target=next;
        BlockState required=SchematicaWorldRenderer.expectedAt(target);
        if(required==null&&mc.level.getBlockState(clicked).canBeReplaced()) {
            required=SchematicaWorldRenderer.expectedAt(clicked);
            target=clicked;
        }
        if(required==null||!mc.level.hasChunkAt(target)||
           mc.level.getBlockState(target).equals(required))return null;
        // Never place a block into a different solid block; normal players
        // have to mine the wrong block first.
        if(!mc.level.getBlockState(target).isAir() &&
           !mc.level.getBlockState(target).canBeReplaced())return null;

        Vec3 eye=mc.player.getEyePosition();
        Vec3 impact=hit.getLocation();
        // Vanilla raycast has already enforced the physical LOS/reach to its
        // real-world hit. Require the schematic ghost to intersect that same
        // ray before or at the real support hit.
        AABB ghost=new AABB(target).inflate(0.001D);
        if(ghost.clip(eye,impact).isEmpty()&&!ghost.contains(impact))return null;
        return target;
    }

    public static boolean beforeVanillaUse(Minecraft mc) {
        boolean hover=autoPending; autoPending=false;
        activeHoverAttempt=hover;
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get())return true;
        if(!SchematicaSession.loaded()||Freecam26.active()||mc.options.toggleUse().get())return false;
        if(mc.player==null||mc.player.isUsingItem()||mc.player.isHandsBusy())return false;
        if(!hover && (!mc.options.keyUse.isDown() || mc.options.toggleUse().get()))return false;
        BlockPos target=candidate(mc);
        if(target==null)return false;
        BlockState required=SchematicaWorldRenderer.expectedAt(target);
        if(required==null)return false;
        if(!(mc.hitResult instanceof BlockHitResult hit))return false;
        // When Easy Pick is enabled it selects the legitimate hotbar item
        // before vanilla startUseItem. Otherwise require the already-held
        // item to predict the exact expected vanilla block state.
        if(!mc.options.pletzelEasyPick.get()) {
            ItemStack held=mc.player.getMainHandItem();
            if(!(held.getItem() instanceof BlockItem item)||
               item.getBlock()!=required.getBlock())return false;
            BlockPlaceContext context=new BlockPlaceContext(mc.player,InteractionHand.MAIN_HAND,held,hit);
            if(!context.canPlace()||!context.getClickedPos().equals(target))return false;
            BlockState predicted=item.getBlock().getStateForPlacement(context);
            if(predicted==null||!predicted.equals(required))return false;
        }
        long now=System.nanoTime();
        if(now-lastDiagnostic>1000000000L) {
            lastDiagnostic=now;
            System.out.println("[PletzelEasyPlace] VANILLA_ATTEMPT target="+target+
                " mode="+(hover?"hover":"hold")+" expected="+required.getBlock());
        }
        return true;
    }

    public static boolean autoPending() { return autoPending; }
    public static boolean inHoverAttempt() { return activeHoverAttempt; }

    /**
     * Called from Minecraft.handleKeybinds AFTER physical input was handled.
     * At most one attempt per physical ghost target and schematic version.
     * A target is eligible again after aiming elsewhere, a source move,
     * or after the world actually changes.
     */
    public static boolean shouldHoverPlace(Minecraft mc) {
        autoPending=false;
        if(mc==null||mc.options==null||!mc.options.pletzelEasyPlace.get()||
           !mc.options.pletzelEasyPlaceHover.get()||Freecam26.active()||
           mc.player==null)return false;
        if(mc.options.keyUse.isDown())return false; // normal physical input owns this tick
        BlockPos target=candidate(mc);
        if(target==null){lastAutoSignature=Long.MIN_VALUE;return false;}
        BlockState actual=mc.level.getBlockState(target);
        long signature=target.asLong() ^ (SchematicaSession.version()<<21) ^
            ((long)mc.player.getInventory().getSelectedSlot()<<45) ^
            ((long)actual.hashCode()<<12);
        if(signature==lastAutoSignature)return false;
        lastAutoSignature=signature;
        autoPending=true;
        return true;
    }

    public static void reset() {
        autoPending=false;activeHoverAttempt=false;lastAutoSignature=Long.MIN_VALUE;
    }
}

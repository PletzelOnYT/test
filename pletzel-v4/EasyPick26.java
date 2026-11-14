package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

/**
 * Optional legitimate hotbar selection before Minecraft.startUseItem().
 *
 * No packet creation, item stack mutation, client-world editing, block
 * placement, camera steering, or inventory transfers occur here. The only
 * gameplay mutation is Inventory.setSelectedSlot(i), the exact same native
 * client action used for physical 1-9 hotbar keypresses in handleKeybinds().
 * The unmodified Minecraft game mode performs its normal server-authoritative
 * selected-slot sync and placement/cooldown rules.
 *
 * A candidate is accepted ONLY if it has the exact required BlockItem and
 * vanilla getStateForPlacement predicts the expected oriented block state at
 * the actual hit face. Special block items whose placement behavior differs
 * from Block#getStateForPlacement may require manual placement, not guessing.
 */
public final class EasyPick26 {
    private static final long WARNING_COOLDOWN_NANOS=1500000000L;
    private static long lastWarnNanos;
    private EasyPick26() {}

    /**
     * Called exclusively before the vanilla Minecraft.startUseItem() body.
     * true: allow ordinary use/placement; false: block a wrong/repeated
     * placement at a known schematic cell. Never synthesizes a use input.
     */
    public static boolean beforeVanillaUse(final Minecraft mc) {
        if (mc == null || mc.options == null || !mc.options.pletzelEasyPick.get()) return true;
        if (!SchematicaSession.loaded() || Freecam26.active()) return true;
        // This is the existing, user-remappable Place Block binding. It must
        // be held. Never convert toggle-to-use into autonomous building.
        if (!mc.options.keyUse.isDown() || mc.options.toggleUse().get()) return true;
        if (mc.level == null || mc.player == null || mc.gui.screen() != null) return true;
        if (mc.player.isSpectator() || mc.player.isUsingItem() || mc.player.isHandsBusy()) return true;
        if (!(mc.hitResult instanceof BlockHitResult hit)) return true;

        BlockPos touched=hit.getBlockPos();
        if (!mc.level.hasChunkAt(touched)) return true;
        BlockPos adjacent=touched.relative(hit.getDirection());
        // The ordinary clicked adjacent cell is always considered first. A
        // replaceable clicked block (grass, snow etc.) may itself be the
        // vanilla placement destination.
        BlockState required=SchematicaWorldRenderer.expectedAt(adjacent);
        BlockPos target=adjacent;
        if (required == null && mc.level.getBlockState(touched).canBeReplaced()) {
            target=touched;
            required=SchematicaWorldRenderer.expectedAt(target);
        }
        if (required == null || !mc.level.hasChunkAt(target)) return true;
        if (mc.level.getBlockState(target).equals(required)) return false;

        int chosen=-1;
        int selected=mc.player.getInventory().getSelectedSlot();
        // Search EXACTLY the nine existing hotbar slots. Never look in or
        // modify main inventory, offhand, or creative inventory.
        for (int slot=0;slot<9;slot++) {
            ItemStack item=mc.player.getInventory().getItem(slot);
            if (item.isEmpty() || !(item.getItem() instanceof BlockItem blockItem)) continue;
            if (blockItem.getBlock()!=required.getBlock()) continue;
            BlockPlaceContext context=new BlockPlaceContext(mc.player, InteractionHand.MAIN_HAND,item,hit);
            if (!context.getClickedPos().equals(target) || !context.canPlace()) continue;
            BlockState predicted=blockItem.getBlock().getStateForPlacement(context);
            // No assumed stair orientation, slab half, waterlogging, etc.
            // The vanilla placement routine still decides whether it succeeds.
            if (predicted == null || !predicted.equals(required)) continue;
            if (slot==selected) return true;
            if (chosen<0) chosen=slot;
        }
        if (chosen>=0) {
            // Exact vanilla physical-number-key selection action, performed
            // before the unmodified startUseItem/MultiplayerGameMode path.
            mc.player.getInventory().setSelectedSlot(chosen);
            System.out.println("[PletzelEasyPick] SELECT slot="+chosen+
                " target="+target+" expected="+required.getBlock());
            return true;
        }
        // Prevent a different hotbar block from being placed at a known
        // schematic cell. Nothing is substituted or moved. Player remains
        // free to disable Easy Pick or manually change their aiming face.
        long now=System.nanoTime();
        if (now-lastWarnNanos>WARNING_COOLDOWN_NANOS) {
            lastWarnNanos=now;
            System.out.println("[PletzelEasyPick] MISSING target="+target+
                " expected="+required.getBlock()+" selected="+selected);
            // Log once per cooldown. This 26.2 LocalPlayer API does not
            // expose the old displayClientMessage(...) actionbar method.
        }
        return false;
    }
}

package net.pletzel.schematica;

import net.minecraft.client.Minecraft;

/**
 * EMERGENCY SAFETY LOCKOUT — 2026-11-13.
 *
 * The previous Easy Place implementation advanced pending blocks using local,
 * potentially predicted block state instead of an explicit server-authoritative
 * placement result. Repeated Hold actions could run while one was outstanding.
 * Automatic placement must remain unavailable until controlled server tests,
 * rejection handling, and correct synchronization are independently verified.
 *
 * This class never changes the crosshair hit, hotbar, client world, packet
 * stream, or vanilla input. Independent Easy Pick remains unchanged.
 */
public final class EasyPlace26 {
    public static final boolean SAFETY_LOCKOUT = true;
    private static boolean warned = false;
    private EasyPlace26() {}

    private static void enforceSafetyLockout(Minecraft mc) {
        if (mc == null || mc.options == null) return;
        boolean changed = false;
        if (mc.options.pletzelEasyPlace.get()) {
            mc.options.pletzelEasyPlace.set(false);
            changed = true;
        }
        if (mc.options.pletzelEasyPlaceHover.get()) {
            mc.options.pletzelEasyPlaceHover.set(false);
            changed = true;
        }
        if (changed) {
            mc.options.save();
            System.out.println("[PletzelEasyPlace] SAFETY_LOCKOUT: saved Easy Place=OFF, Hover=OFF; vanilla right-click remains enabled.");
        } else if (!warned) {
            warned = true;
            System.out.println("[PletzelEasyPlace] SAFETY_LOCKOUT: automatic placement disabled until server-confirmed multiplayer tests pass.");
        }
    }

    /** Permit the UNMODIFIED vanilla interaction; never forge a hit or use. */
    public static boolean beforeVanillaUse(Minecraft mc) {
        enforceSafetyLockout(mc);
        return true;
    }

    /** No automatic clicks from hover, even with a stale saved setting. */
    public static boolean shouldHoverPlace(Minecraft mc) {
        enforceSafetyLockout(mc);
        return false;
    }

    public static boolean inHoverAttempt() {
        return false;
    }

    /** Called each gameplay tick, so saved unsafe options are reset promptly. */
    public static void afterVanillaKeybinds(Minecraft mc) {
        enforceSafetyLockout(mc);
    }

    public static void reset() {
        // No synthetic interactions, pending placements or local block edits.
    }
}

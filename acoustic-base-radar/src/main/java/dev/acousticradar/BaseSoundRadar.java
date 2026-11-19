package dev.acousticradar;

import meteordevelopment.meteorclient.events.game.GameLeftEvent;
import meteordevelopment.meteorclient.events.packets.PacketEvent;
import meteordevelopment.meteorclient.events.render.Render3DEvent;
import meteordevelopment.meteorclient.events.world.PlaySoundEvent;
import meteordevelopment.meteorclient.events.world.TickEvent;
import meteordevelopment.meteorclient.renderer.ShapeMode;
import meteordevelopment.meteorclient.settings.BoolSetting;
import meteordevelopment.meteorclient.settings.IntSetting;
import meteordevelopment.meteorclient.settings.Setting;
import meteordevelopment.meteorclient.settings.SettingGroup;
import meteordevelopment.meteorclient.systems.modules.Module;
import meteordevelopment.meteorclient.utils.render.color.Color;
import meteordevelopment.orbit.EventHandler;
import net.minecraft.util.math.Box;
import net.minecraft.entity.Entity;
import net.minecraft.network.packet.s2c.play.PlaySoundS2CPacket;
import net.minecraft.network.packet.s2c.play.PlaySoundFromEntityS2CPacket;

public final class BaseSoundRadar extends Module {
    private final SettingGroup general = settings.getDefaultGroup();
    private final SettingGroup sounds = settings.createGroup("Sound Sources");
    private final SettingGroup visuals = settings.createGroup("Render");

    private final Setting<Boolean> listenPackets = general.add(new BoolSetting.Builder()
        .name("server-sound-packets")
        .description("Detect received server sound packets even if audio playback is culled.")
        .defaultValue(true).build());
    private final Setting<Boolean> listenPlayback = general.add(new BoolSetting.Builder()
        .name("played-sound-events")
        .description("Also detect locally played sounds, as in Saturn SoundLocator.")
        .defaultValue(true).build());

    private final Setting<Integer> lifetime = general.add(new IntSetting.Builder()
        .name("memory-minutes")
        .description("How long to remember individual detected sound blocks.")
        .defaultValue(4).range(1, 30).sliderRange(1, 30).build());
    private final Setting<Boolean> ignoreSelf = general.add(new BoolSetting.Builder()
        .name("ignore-nearby-sounds")
        .description("Optional local-sound suppression. Disabled by default so nearby chests still show.")
        .defaultValue(false).build());
    private final Setting<Integer> selfRadius = general.add(new IntSetting.Builder()
        .name("ignore-within")
        .description("When enabled, ignore sounds this close to you.")
        .defaultValue(4).range(1, 20).visible(ignoreSelf::get).build());
    private final Setting<Boolean> redAlerts = general.add(new BoolSetting.Builder()
        .name("red-alerts")
        .description("Notify when high-priority sound evidence is first detected.")
        .defaultValue(true).build());

    private final Setting<Boolean> containers = sounds.add(new BoolSetting.Builder()
        .name("storage")
        .description("Chest, barrel, ender chest and shulker-box operations.")
        .defaultValue(true).build());
    private final Setting<Boolean> villagers = sounds.add(new BoolSetting.Builder()
        .name("villagers")
        .description("Villager and wandering-trader sounds. Natural villages can trigger.")
        .defaultValue(true).build());
    private final Setting<Boolean> machines = sounds.add(new BoolSetting.Builder()
        .name("mechanisms")
        .description("Pistons, dispensers, droppers, crafters, buttons and note blocks.")
        .defaultValue(true).build());
    private final Setting<Boolean> workstations = sounds.add(new BoolSetting.Builder()
        .name("workstations")
        .description("Anvils, brewing, smithing, grindstones, furnaces, beacons, etc.")
        .defaultValue(true).build());
    private final Setting<Boolean> playerEvents = sounds.add(new BoolSetting.Builder()
        .name("player-actions")
        .description("Armor, item/XP pickup and player level-up sounds.")
        .defaultValue(true).build());
    private final Setting<Boolean> minecarts = sounds.add(new BoolSetting.Builder()
        .name("minecart-noises")
        .description("Minecart noises are weak evidence; hoppers themselves are silent.")
        .defaultValue(true).build());
    private final Setting<Boolean> animals = sounds.add(new BoolSetting.Builder()
        .name("farm-animals")
        .description("Ambient farm-animal sounds. Weakest evidence; off by default.")
        .defaultValue(false).build());

    private final Setting<Boolean> boxes = visuals.add(new BoolSetting.Builder()
        .name("render-source-blocks")
        .description("Highlight only the ONE world voxel that produced each sound.")
        .defaultValue(true).build());
    private final Setting<Integer> minimumTier = visuals.add(new IntSetting.Builder()
        .name("minimum-color-tier")
        .description("0 white, 1 light yellow, 2 yellow, 3 light orange, 4 orange, 5 red.")
        .defaultValue(0).range(0, 5).sliderRange(0, 5).build());
    private final Setting<Integer> opacity = visuals.add(new IntSetting.Builder()
        .name("fill-opacity").description("Transparency of each 1-block highlight.")
        .defaultValue(42).range(0, 180).sliderRange(0, 180).build());

    private static final int[][] PALETTE = {
        {255, 255, 255}, // 0: white - trivial activity
        {255, 255, 190}, // 1: pale yellow - common villager/minecart
        {255, 230, 72},  // 2: yellow - redstone interaction, workstations
        {255, 188, 83},  // 3: light orange - chest/piston/storage use
        {255, 115, 18},  // 4: orange - ender storage, crafting automation
        {255, 35, 35}    // 5: red - shulker-box activity or corroborated evidence
    };

    private final RadarScorer tracker = new RadarScorer();
    private long ticks;
    private long lastRedAlert = -2000;
    private String dimension = "";

    public BaseSoundRadar() {
        super(AcousticRadarAddon.CATEGORY, "base-sound-radar",
            "Highlights exact 1-block origins of received base-related sounds.");
    }

    @Override
    public void onActivate() { reset(); }

    @Override
    public void onDeactivate() { reset(); }

    private void reset() {
        tracker.clear();
        ticks = 0;
        lastRedAlert = -2000;
        dimension = "";
    }

    @EventHandler
    private void onGameLeft(GameLeftEvent event) { reset(); }

    @EventHandler
    private void onTick(TickEvent.Pre event) {
        if (mc.world == null) {
            if (tracker.size() > 0) reset();
            return;
        }
        String currentDimension = mc.world.getRegistryKey().getValue().toString();
        if (!dimension.equals(currentDimension)) {
            tracker.clear();
            dimension = currentDimension;
        }
        ticks++;
        if (ticks % 20 == 0) tracker.expire(ticks, lifetime.get() * 1200L);
    }

    /**
     * Server-originated sounds are captured before client audio-distance culling.
     * Only packets the server actually sent are visible; this is NOT a remote scan.
     * Packet handling may run on the network thread, so schedule main-thread access.
     */
    @EventHandler
    private void onPacket(PacketEvent.Receive event) {
        if (!listenPackets.get()) return;
        if (event.packet instanceof PlaySoundS2CPacket packet) {
            String soundId = packet.getSound().value().id().toString();
            double x = packet.getX(), y = packet.getY(), z = packet.getZ();
            mc.execute(() -> trackSound(soundId, x, y, z));
        } else if (event.packet instanceof PlaySoundFromEntityS2CPacket packet) {
            String soundId = packet.getSound().value().id().toString();
            int entityId = packet.getEntityId();
            mc.execute(() -> {
                if (mc.world == null) return;
                Entity entity = mc.world.getEntityById(entityId);
                if (entity != null) {
                    trackSound(soundId, entity.getX(), entity.getY(), entity.getZ());
                }
            });
        }
    }

    @EventHandler
    private void onSound(PlaySoundEvent event) {
        if (!listenPlayback.get() || event.sound == null) return;
        trackSound(event.sound.getId().toString(),
            event.sound.getX(), event.sound.getY(), event.sound.getZ());
    }

    private void trackSound(String soundId, double x, double y, double z) {
        if (mc.world == null || mc.player == null) return;
        RadarScorer.Signal signal = RadarScorer.classify(soundId);
        if (signal == null || !enabled(signal.kind())) return;
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)) return;
        if (ignoreSelf.get() && mc.player.squaredDistanceTo(x, y, z)
            < (double) selfRadius.get() * selfRadius.get()) return;

        // Both event paths use the same per-voxel/per-sound deduplicator.
        // No artificial maximum range: a remote packet is useful if received.
        int tier = tracker.add(soundId, x, y, z, ticks);
        if (tier == 5 && redAlerts.get() && ticks - lastRedAlert >= 1200L) {
            info("Strong sound evidence at " + (int) Math.floor(x) + ", "
                + (int) Math.floor(y) + ", " + (int) Math.floor(z)
                + " (" + soundId + "). Base not confirmed.");
            lastRedAlert = ticks;
        }
    }

    private boolean enabled(RadarScorer.Kind kind) {
        return switch (kind) {
            case STORAGE -> containers.get();
            case VILLAGER -> villagers.get();
            case AUTOMATION -> machines.get();
            case WORKSTATION -> workstations.get();
            case PLAYER -> playerEvents.get();
            case MINECART -> minecarts.get();
            case ANIMAL -> animals.get();
        };
    }

    @EventHandler
    private void onRender(Render3DEvent event) {
        if (!boxes.get() || mc.world == null || mc.player == null) return;
        for (RadarScorer.Marker marker : tracker.markers(
            ticks, lifetime.get() * 1200L, minimumTier.get())) {
            int[] rgb = PALETTE[marker.tier()];
            Color outline = new Color(rgb[0], rgb[1], rgb[2], 230);
            Color fill = new Color(rgb[0], rgb[1], rgb[2], opacity.get());
            // Exactly ONE block, using the actual sound-origin coordinates.
            // It does not guess a base footprint or merge neighboring voxels.
            Box block = new Box(marker.x(), marker.y(), marker.z(),
                                marker.x() + 1, marker.y() + 1, marker.z() + 1);
            event.renderer.box(block, fill, outline, ShapeMode.Both, 0);
        }
    }
}

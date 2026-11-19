package dev.acousticradar;

import meteordevelopment.meteorclient.events.game.GameLeftEvent;
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

public final class BaseSoundRadar extends Module {
    private final SettingGroup general = settings.getDefaultGroup();
    private final SettingGroup sounds = settings.createGroup("Sound Sources");
    private final SettingGroup visuals = settings.createGroup("Render");

    private final Setting<Integer> range = general.add(new IntSetting.Builder()
        .name("listen-radius").description("Maximum distance for received, positioned sounds.")
        .defaultValue(96).range(16, 256).sliderRange(16, 256).build());
    private final Setting<Integer> clusterRadius = general.add(new IntSetting.Builder()
        .name("cluster-radius").description("Horizontal distance for grouping likely shared locations.")
        .defaultValue(16).range(4, 40).sliderRange(4, 40).build());
    private final Setting<Integer> lifetime = general.add(new IntSetting.Builder()
        .name("memory-minutes").description("Maximum time to remember a location without new evidence.")
        .defaultValue(4).range(1, 20).sliderRange(1, 20).build());
    private final Setting<Boolean> ignoreSelf = general.add(new BoolSetting.Builder()
        .name("ignore-nearby-sounds").description("Avoid scoring sounds from your immediate position.")
        .defaultValue(true).build());
    private final Setting<Integer> selfRadius = general.add(new IntSetting.Builder()
        .name("ignore-within").description("Distance to ignore around your player.")
        .defaultValue(7).range(1, 20).visible(ignoreSelf::get).build());
    private final Setting<Boolean> alertRed = general.add(new BoolSetting.Builder()
        .name("red-alerts").description("Show a chat notice for very strong multi-source evidence.")
        .defaultValue(true).build());

    private final Setting<Boolean> containers = sounds.add(new BoolSetting.Builder()
        .name("containers").description("Chests, trapped chests, barrels and shulker boxes.")
        .defaultValue(true).build());
    private final Setting<Boolean> villagers = sounds.add(new BoolSetting.Builder()
        .name("villagers").description("Villagers and wandering traders (natural villages can trigger).")
        .defaultValue(true).build());
    private final Setting<Boolean> machines = sounds.add(new BoolSetting.Builder()
        .name("mechanisms").description("Pistons, droppers, dispensers, crafters and note blocks.")
        .defaultValue(true).build());
    private final Setting<Boolean> workstations = sounds.add(new BoolSetting.Builder()
        .name("workstations").description("Anvils, furnaces, brewing stands, grindstones and bells.")
        .defaultValue(true).build());
    private final Setting<Boolean> playerEvents = sounds.add(new BoolSetting.Builder()
        .name("player-actions").description("Item pickups, armor equip and level-up events.")
        .defaultValue(true).build());
    private final Setting<Boolean> animals = sounds.add(new BoolSetting.Builder()
        .name("farm-animals").description("Cow, sheep, chicken, pig and horse activity; weak evidence.")
        .defaultValue(false).build());

    private final Setting<Boolean> boxes = visuals.add(new BoolSetting.Builder()
        .name("render-boxes").description("Show a white-to-red cluster overlay in the world.")
        .defaultValue(true).build());
    private final Setting<Integer> markerSize = visuals.add(new IntSetting.Builder()
        .name("marker-width").description("Approximate marker width in blocks, not a base footprint.")
        .defaultValue(12).range(2, 40).sliderRange(2, 40).build());
    private final Setting<Integer> opacity = visuals.add(new IntSetting.Builder()
        .name("fill-opacity").description("0 means outlines only; 255 means fully opaque.")
        .defaultValue(35).range(0, 180).sliderRange(0, 180).build());

    private static final int[][] PALETTE = {
        {255, 255, 255}, // white: weakest
        {255, 255, 190}, // light yellow
        {255, 230, 72},  // yellow
        {255, 188, 83},  // light orange
        {255, 115, 18},  // orange
        {255, 35, 35}    // red: strongest
    };

    private final RadarScorer tracker = new RadarScorer();
    private long ticks;
    private long lastRedAlert = -2000;
    private String dimension = "";

    public BaseSoundRadar() {
        super(AcousticRadarAddon.CATEGORY, "base-sound-radar",
            "Saturn-style sound location plus ranked, fading base-activity markers.");
    }

    @Override
    public void onActivate() {
        reset();
    }

    @Override
    public void onDeactivate() {
        reset();
    }

    private void reset() {
        tracker.clear();
        ticks = 0;
        lastRedAlert = -2000;
        dimension = "";
    }

    @EventHandler
    private void onGameLeft(GameLeftEvent event) {
        reset();
    }

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
        if (ticks % 20 == 0) tracker.expire(ticks, lifetime.get() * 60L * 20L);
    }

    @EventHandler
    private void onPlaySound(PlaySoundEvent event) {
        if (mc.world == null || mc.player == null || event.sound == null) return;
        String soundId = event.sound.getId().toString();
        RadarScorer.Kind kind = RadarScorer.classify(soundId);
        if (kind == null || !enabled(kind)) return;

        double x = event.sound.getX();
        double y = event.sound.getY();
        double z = event.sound.getZ();
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)) return;

        double distanceSquared = mc.player.squaredDistanceTo(x, y, z);
        if (distanceSquared > range.get() * range.get()) return;
        if (ignoreSelf.get() && distanceSquared < selfRadius.get() * selfRadius.get()) return;

        int tier = tracker.add(soundId, kind, x, y, z, ticks, clusterRadius.get());
        if (tier == 5 && alertRed.get() && ticks - lastRedAlert >= 1200) {
            info("High acoustic evidence near X: " + Math.round(x)
                + " Y: " + Math.round(y) + " Z: " + Math.round(z)
                + ". This does not confirm a base.");
            lastRedAlert = ticks;
        }
    }

    private boolean enabled(RadarScorer.Kind kind) {
        return switch (kind) {
            case CONTAINER -> containers.get();
            case VILLAGER -> villagers.get();
            case MACHINE -> machines.get();
            case WORKSTATION -> workstations.get();
            case PLAYER -> playerEvents.get();
            case ANIMAL -> animals.get();
        };
    }

    @EventHandler
    private void onRender(Render3DEvent event) {
        if (!boxes.get() || mc.player == null) return;
        for (RadarScorer.Marker marker : tracker.markers(ticks)) {
            if (mc.player.squaredDistanceTo(marker.x(), marker.y(), marker.z())
                > (range.get() + 24.0) * (range.get() + 24.0)) continue;

            int[] rgb = PALETTE[marker.tier()];
            Color outline = new Color(rgb[0], rgb[1], rgb[2], 235);
            Color fill = new Color(rgb[0], rgb[1], rgb[2], opacity.get());
            double radius = markerSize.get() / 2.0;
            Box area = new Box(marker.x() - radius, marker.y() - 2,
                marker.z() - radius, marker.x() + radius,
                marker.y() + 5, marker.z() + radius);
            event.renderer.box(area, fill, outline, ShapeMode.Both, 0);
        }
    }
}

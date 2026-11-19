package dev.acousticradar;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Sound-origin markers. Only sounds actually received by Minecraft are known:
 * no packet spoofing, world scraping, arbitrary-distance acoustic inference,
 * or claims of probability calibration.
 *
 * Stores one exact 1-block voxel per observed emitter, not a large region.
 */
public final class RadarScorer {
    public enum Kind { STORAGE, VILLAGER, AUTOMATION, WORKSTATION, PLAYER, ANIMAL, MINECART }

    /** Priority is a heuristic evidence tier: 0 white -> 5 red. */
    public record Signal(Kind kind, int priority) {}

    /** Integer world-block origin, not a guessed center of a base. */
    public record Marker(int x, int y, int z, int tier, Kind kind,
                         int observations, int distinctSounds, String lastSound) {}

    private record BlockKey(int x, int y, int z) {}

    private static final class Observation {
        final BlockKey block;
        final Map<String, Long> lastSoundTick = new HashMap<>();
        final Set<String> differentSounds = new HashSet<>();
        final EnumSet<Kind> kinds = EnumSet.noneOf(Kind.class);
        long lastTick;
        int total;
        int strongest = -1;
        Kind strongestKind;
        String lastSound = "";
        boolean corroborated;

        Observation(BlockKey block, long tick) {
            this.block = block;
            this.lastTick = tick;
        }

        int tier(long now) {
            // Strongest individual sound determines base color. Different kinds
            // or different sound IDs may elevate by ONE tier each.
            int diversityBonus = differentSounds.size() >= 2 ? 1 : 0;
            int corroborationBonus = corroborated ? 1 : 0;
            int agePenalty = (int) (Math.max(0, now - lastTick) / 1200L);
            return clamp(strongest + diversityBonus + corroborationBonus - agePenalty);
        }
    }

    private static final int MAX_MARKERS = 1024;
    private final Map<BlockKey, Observation> blocks = new HashMap<>();

    public void clear() { blocks.clear(); }

    public int size() { return blocks.size(); }

    /** Tracks a received sound at its integer source voxel; returns -1 if suppressed. */
    public int add(String soundId, double x, double y, double z, long tick) {
        Signal signal = classify(soundId);
        if (signal == null || !Double.isFinite(x) || !Double.isFinite(y)
            || !Double.isFinite(z)) return -1;
        // Avoid invalid coordinates / integer overflow from unusual sound mods.
        if (Math.abs(x) > 30_000_000 || Math.abs(z) > 30_000_000 || Math.abs(y) > 1_000_000) {
            return -1;
        }

        BlockKey key = new BlockKey((int) Math.floor(x), (int) Math.floor(y),
                                    (int) Math.floor(z));
        Observation o = blocks.get(key);
        if (o == null) {
            if (blocks.size() >= MAX_MARKERS) evictOldest();
            o = new Observation(key, tick);
            blocks.put(key, o);
        }

        Long previous = o.lastSoundTick.get(soundId);
        long cooldown = signal.priority() <= 1 ? 100L : 12L;
        if (previous != null && tick - previous < cooldown) return -1;

        o.lastSoundTick.put(soundId, tick);
        if (o.differentSounds.size() < 16) o.differentSounds.add(soundId);
        o.kinds.add(signal.kind());
        o.total = Math.min(o.total + 1, Integer.MAX_VALUE);
        o.lastTick = tick;
        o.lastSound = soundId;

        if (signal.priority() > o.strongest) {
            o.strongest = signal.priority();
            o.strongestKind = signal.kind();
        }

        // Tight local corroboration, not a large merged hotspot. It improves
        // confidence of each *individual* source but NEVER moves its marker.
        if (signal.priority() >= 2) {
            for (Observation other : blocks.values()) {
                if (other == o || other.strongest < 2 ||
                    other.strongestKind == signal.kind() ||
                    tick - other.lastTick > 1600L) continue;
                int dx = other.block.x() - key.x();
                int dy = other.block.y() - key.y();
                int dz = other.block.z() - key.z();
                if (dx * dx + dy * dy + dz * dz <= 16) {
                    o.corroborated = true;
                    other.corroborated = true;
                }
            }
        }

        return o.tier(tick);
    }

    public List<Marker> markers(long tick, long ttlTicks, int minimumTier) {
        List<Marker> result = new ArrayList<>(blocks.size());
        for (Observation o : blocks.values()) {
            if (tick - o.lastTick > ttlTicks) continue;
            int tier = o.tier(tick);
            if (tier < minimumTier) continue;
            result.add(new Marker(o.block.x(), o.block.y(), o.block.z(),
                tier, o.strongestKind, o.total, o.differentSounds.size(), o.lastSound));
        }
        return result;
    }

    public void expire(long tick, long ttlTicks) {
        Iterator<Observation> iterator = blocks.values().iterator();
        while (iterator.hasNext()) {
            Observation o = iterator.next();
            if (tick - o.lastTick > ttlTicks) {
                iterator.remove();
                continue;
            }
            // Bound per-source duplicate-state memory on persistent voxels.
            o.lastSoundTick.entrySet().removeIf(e -> tick - e.getValue() > 200);
        }
    }

    private void evictOldest() {
        BlockKey oldestKey = null;
        long oldestTick = Long.MAX_VALUE;
        for (Map.Entry<BlockKey, Observation> entry : blocks.entrySet()) {
            if (entry.getValue().lastTick < oldestTick) {
                oldestKey = entry.getKey();
                oldestTick = entry.getValue().lastTick;
            }
        }
        if (oldestKey != null) blocks.remove(oldestKey);
    }

    private static int clamp(int tier) { return Math.max(0, Math.min(5, tier)); }

    /**
     * Scores sounds by their individual usefulness, rather than simply by volume.
     * Entities are approximate sound positions, not guaranteed physical blocks.
     */
    public static Signal classify(String id) {
        if (id == null || id.isEmpty()) return null;
        String s = id.startsWith("minecraft:") ? id.substring(10) : id;

        // A shulker-box opening is very strong evidence of player-made storage.
        if (starts(s, "block.shulker_box.")) {
            if (has(s, ".open", ".close")) return new Signal(Kind.STORAGE, 5);
        }
        if (starts(s, "block.ender_chest.")) {
            if (has(s, ".open", ".close")) return new Signal(Kind.STORAGE, 4);
        }
        if (starts(s, "block.chest.", "block.barrel.", "block.trapped_chest.")) {
            if (has(s, ".open", ".close", ".locked")) return new Signal(Kind.STORAGE, 3);
        }

        // Automatic machines: the most specific operation sounds rank highest.
        if (starts(s, "block.crafter.")) {
            if (has(s, ".craft", ".fail")) return new Signal(Kind.AUTOMATION, 4);
        }
        if (starts(s, "block.piston.", "block.dispenser.", "block.dropper.")) {
            if (has(s, ".extend", ".contract", ".dispense", ".fail", ".drop", ".launch")) {
                return new Signal(Kind.AUTOMATION, 3);
            }
        }
        if (starts(s, "block.iron_door.", "block.iron_trapdoor.",
            "block.lever.", "block.comparator.", "block.wooden_button.",
            "block.stone_button.", "block.note_block.", "block.tripwire.")) {
            if (has(s, ".open", ".close", ".click", ".attach", ".detach", "block.note_block.")) {
                return new Signal(Kind.AUTOMATION, 2);
            }
        }

        if (starts(s, "block.beacon.", "block.respawn_anchor.")) {
            if (has(s, ".activate", ".power_select", ".charge", ".set_spawn")) {
                return new Signal(Kind.WORKSTATION, 4);
            }
        }
        if (starts(s, "block.anvil.", "block.grindstone.", "block.stonecutter.",
            "block.smithing_table.", "block.brewing_stand.", "block.furnace.",
            "block.enchantment_table.")) {
            if (has(s, ".use", ".take_result", ".brew", ".crackle", ".place", ".craft")) {
                return new Signal(Kind.WORKSTATION, 2);
            }
        }

        if (starts(s, "entity.villager.", "entity.wandering_trader.")) {
            if (has(s, ".trade", ".yes", ".levelup", ".work_")) return new Signal(Kind.VILLAGER, 2);
            if (has(s, ".ambient", ".no", ".celebrate")) return new Signal(Kind.VILLAGER, 1);
        }
        if (starts(s, "entity.experience_orb.pickup", "entity.player.levelup",
            "item.armor.equip", "entity.item.pickup",
            "entity.fishing_bobber.retrieve")) {
            return new Signal(Kind.PLAYER, 2);
        }

        // Hopper-minecarts themselves do not emit a special hopper sound.
        if (starts(s, "entity.minecart.riding", "entity.minecart.inside")) {
            return new Signal(Kind.MINECART, 1);
        }
        if (starts(s, "entity.cow.", "entity.sheep.", "entity.chicken.",
            "entity.pig.", "entity.horse.")) {
            if (has(s, ".ambient", ".milk", ".shear", ".eat")) return new Signal(Kind.ANIMAL, 0);
        }
        return null;
    }

    private static boolean starts(String sound, String... prefixes) {
        for (String prefix : prefixes) if (sound.startsWith(prefix)) return true;
        return false;
    }

    private static boolean has(String sound, String... fragments) {
        for (String fragment : fragments) if (sound.contains(fragment)) return true;
        return false;
    }
}

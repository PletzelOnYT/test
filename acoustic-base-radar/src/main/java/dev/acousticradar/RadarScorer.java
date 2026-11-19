package dev.acousticradar;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * Pure-Java, session-local acoustic evidence aggregation.
 * A tier is a relative evidence ranking, NOT a calibrated probability of a base.
 */
public final class RadarScorer {
    public enum Kind {
        CONTAINER(14.0, 42.0), VILLAGER(6.0, 27.0),
        MACHINE(18.0, 43.0), WORKSTATION(11.0, 32.0),
        PLAYER(5.0, 19.0), ANIMAL(2.0, 10.0);

        final double weight;
        final double cap;
        Kind(double weight, double cap) {
            this.weight = weight;
            this.cap = cap;
        }
    }

    public record Marker(double x, double y, double z, int tier,
                         int soundCount, int categories, double evidence) {}

    private static final class Candidate {
        double x, y, z;
        long lastTick;
        int samples;
        final EnumSet<Kind> types = EnumSet.noneOf(Kind.class);
        final EnumMap<Kind, Double> credits = new EnumMap<>(Kind.class);

        Candidate(double x, double y, double z, long tick) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.lastTick = tick;
        }

        double score(long tick) {
            double sum = 0;
            for (double value : credits.values()) sum += value;
            // Evidence halves every 80 seconds without further sound activity.
            return sum * Math.pow(0.5, Math.max(0, tick - lastTick) / 1600.0);
        }
    }

    private final List<Candidate> clusters = new ArrayList<>();
    private final Map<String, Long> lastBySource = new HashMap<>();

    public void clear() {
        clusters.clear();
        lastBySource.clear();
    }

    public int size() {
        return clusters.size();
    }

    /** Returns the new tier, or -1 if a source is duplicate / outside radius. */
    public int add(String sound, Kind kind, double x, double y, double z,
                   long tick, double clusterRadius) {
        // Group repeating sound events by nearby approximate emitter location.
        String dedupe = kind + "/" + sound + "/" + Math.floor(x / 3.0)
            + "/" + Math.floor(y / 3.0) + "/" + Math.floor(z / 3.0);
        Long old = lastBySource.get(dedupe);
        if (old != null && tick - old < 22) return -1;
        lastBySource.put(dedupe, tick);

        Candidate target = null;
        double best = clusterRadius * clusterRadius;
        for (Candidate c : clusters) {
            double dx = x - c.x, dz = z - c.z;
            double horizontalSquared = dx * dx + dz * dz;
            if (Math.abs(y - c.y) <= 12 && horizontalSquared <= best) {
                best = horizontalSquared;
                target = c;
            }
        }
        if (target == null) {
            if (clusters.size() >= 120) {
                Candidate oldest = clusters.get(0);
                for (Candidate c : clusters) if (c.lastTick < oldest.lastTick) oldest = c;
                clusters.remove(oldest);
            }
            target = new Candidate(x, y, z, tick);
            clusters.add(target);
        }

        // Retain prior evidence only to the extent it has not decayed.
        double decay = Math.pow(0.5, Math.max(0, tick - target.lastTick) / 1600.0);
        for (Kind k : target.credits.keySet()) {
            target.credits.put(k, target.credits.get(k) * decay);
        }
        double previous = target.credits.getOrDefault(kind, 0.0);
        target.credits.put(kind, Math.min(kind.cap, previous + kind.weight));
        target.types.add(kind);
        target.samples++;
        target.lastTick = tick;

        // Slowly follow additional nearby sources without jumping to the player.
        double mix = target.samples == 1 ? 1.0 : 0.15;
        target.x += (x - target.x) * mix;
        target.y += (y - target.y) * mix;
        target.z += (z - target.z) * mix;
        return tier(target.score(tick), target.types.size());
    }

    public List<Marker> markers(long tick) {
        List<Marker> results = new ArrayList<>(clusters.size());
        for (Candidate c : clusters) {
            double score = c.score(tick);
            if (score >= 2.0) {
                results.add(new Marker(c.x, c.y, c.z,
                    tier(score, c.types.size()), c.samples, c.types.size(), score));
            }
        }
        return results;
    }

    public void expire(long tick, long ttlTicks) {
        clusters.removeIf(c -> tick - c.lastTick > ttlTicks || c.score(tick) < 2.0);
        // Drop stale duplicate keys, avoiding an unbounded collection.
        if (tick % 200 == 0) {
            Iterator<Map.Entry<String, Long>> it = lastBySource.entrySet().iterator();
            while (it.hasNext()) if (tick - it.next().getValue() > 200) it.remove();
        }
    }

    public static int tier(double evidence, int distinctKinds) {
        if (evidence < 12) return 0;  // white
        if (evidence < 25) return 1;  // light yellow
        if (evidence < 43) return 2;  // yellow
        if (evidence < 66) return 3;  // light orange
        if (evidence < 95 || distinctKinds < 3) return 4; // orange
        return 5; // red: substantial evidence from >=3 sound classes
    }

    public static Kind classify(String id) {
        String sound = id.startsWith("minecraft:") ? id.substring(10) : id;

        if (starts(sound, "block.chest.", "block.barrel.", "block.ender_chest.",
            "block.shulker_box.", "block.trapped_chest.")) {
            if (contains(sound, ".open", ".close", ".lock")) return Kind.CONTAINER;
        }
        if (starts(sound, "entity.villager.", "entity.wandering_trader.")) {
            if (contains(sound, ".ambient", ".trade", ".yes", ".no", ".work_", ".celebrate", ".levelup")) {
                return Kind.VILLAGER;
            }
        }
        if (starts(sound, "block.piston.", "block.dispenser.", "block.dropper.",
            "block.crafter.", "block.note_block.", "block.tripwire.", "block.iron_door.")) {
            return Kind.MACHINE;
        }
        if (starts(sound, "block.anvil.", "block.grindstone.", "block.stonecutter.",
            "block.smithing_table.", "block.brewing_stand.", "block.furnace.",
            "block.beacon.", "block.enchantment_table.", "block.bell.")) {
            return Kind.WORKSTATION;
        }
        if (starts(sound, "entity.experience_orb.pickup", "entity.player.levelup",
            "entity.item.pickup", "item.armor.equip", "entity.fishing_bobber.retrieve")) {
            return Kind.PLAYER;
        }
        if (starts(sound, "entity.cow.", "entity.sheep.", "entity.chicken.",
            "entity.pig.", "entity.horse.")) {
            if (contains(sound, ".ambient", ".milk", ".shear", ".eat")) return Kind.ANIMAL;
        }
        // Hoppers moving items have no vanilla sound, so cannot be detected here.
        return null;
    }

    private static boolean starts(String value, String... prefixes) {
        for (String prefix : prefixes) if (value.startsWith(prefix)) return true;
        return false;
    }
    private static boolean contains(String value, String... fragments) {
        for (String fragment : fragments) if (value.contains(fragment)) return true;
        return false;
    }
}

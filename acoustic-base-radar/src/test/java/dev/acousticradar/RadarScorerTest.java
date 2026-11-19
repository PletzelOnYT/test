package dev.acousticradar;

import java.util.List;

/**
 * Runs without Minecraft/Meteor dependencies so CI checks source-block behavior.
 * Use: java -ea dev.acousticradar.RadarScorerTest
 */
public final class RadarScorerTest {
    public static void main(String[] args) {
        assert RadarScorer.classify("minecraft:block.chest.open").priority() == 3;
        assert RadarScorer.classify("minecraft:block.shulker_box.open").priority() == 5;
        assert RadarScorer.classify("minecraft:entity.villager.ambient").priority() == 1;
        assert RadarScorer.classify("minecraft:entity.cow.ambient").priority() == 0;
        assert RadarScorer.classify("minecraft:block.crafter.craft").priority() == 4;
        assert RadarScorer.classify("minecraft:block.hopper.humming") == null;
        assert RadarScorer.classify("minecraft:block.stone.break") == null;

        RadarScorer radar = new RadarScorer();
        // No addon-side range clamp. Position can be thousands of blocks away
        // IF the server actually sent such a sound event.
        assert radar.add("minecraft:block.chest.open", 10000.5, 64.0, -30.4, 10) == 3;
        List<RadarScorer.Marker> markers = radar.markers(10, 4800, 0);
        assert markers.size() == 1 : markers;
        RadarScorer.Marker m = markers.get(0);
        assert m.x() == 10000 && m.y() == 64 && m.z() == -31;
        assert m.tier() == 3;

        // Repeated identical sound is deduplicated; different ID at SAME
        // voxel raises strength without widening or relocating the marker.
        assert radar.add("minecraft:block.chest.open", 10000.5, 64.0, -30.4, 11) == -1;
        assert radar.add("minecraft:block.chest.close", 10000.5, 64.0, -30.4, 20) == 4;
        markers = radar.markers(20, 4800, 0);
        assert markers.size() == 1 && markers.get(0).tier() == 4;

        // Nearby source is a SEPARATE 1-block marker, not a merged area.
        radar.add("minecraft:block.crafter.craft", 10002.5, 64.5, -30.4, 32);
        markers = radar.markers(32, 4800, 0);
        assert markers.size() == 2;
        assert markers.stream().anyMatch(p -> p.x() == 10000 && p.z() == -31);
        assert markers.stream().anyMatch(p -> p.x() == 10002 && p.z() == -31);

        // Highest-priority sound goes straight to red.
        radar.add("minecraft:block.shulker_box.open", -500.5, -20.5, 8500.8, 50);
        markers = radar.markers(50, 4800, 5);
        assert markers.stream().anyMatch(p -> p.x() == -501
            && p.y() == -21 && p.z() == 8500 && p.tier() == 5);

        // Evidence cools with age and expires at configured TTL.
        markers = radar.markers(2500, 4800, 5);
        assert markers.stream().noneMatch(p -> p.x() == -501);
        radar.expire(5000, 4800);
        assert radar.size() == 0;

        radar.add("minecraft:entity.villager.ambient", 1.2, 70, 1.6, 6000);
        assert radar.markers(6000, 4800, 1).size() == 1;
        assert radar.markers(6000, 4800, 2).isEmpty();

        System.out.println("Acoustic Base Radar: all source-block scoring assertions passed.");
    }
}

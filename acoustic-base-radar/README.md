# Acoustic Base Radar 1.2.0 — Minecraft Java 1.21.11 / Meteor / Fabric

A Meteor addon modeled after Saturn's SoundLocator event-listening approach, with
independent per-block classification and priority-based coloring.

## Exact block-sized sound highlights
Every received relevant sound is marked with exactly one 1 × 1 × 1 cube at the
integer sound-emitter position (floor X, floor Y, floor Z).
Neighboring sources remain distinct; there are **no large merged-area boxes**.

Important distinction: a villager, minecart, or player sound may originate from
an entity's position (a *voxel*), not an actual physical block. For chest and
redstone sounds, the reported origin is generally near the operating block.

## Color priority
- **White (0):** weak farm-animal noises (optional)
- **Light yellow (1):** ambient villagers / rail noises
- **Yellow (2):** workstations, villager trades, simple redstone / player activity
- **Light orange (3):** normal chest/barrel opening and piston/dispenser activity
- **Orange (4):** ender chest, active crafter, correlated sounds
- **Red (5):** shulker-box open/close, or strengthened multi-sound evidence

Colors indicate relative importance of **actual sound evidence**, not the
probability or confirmed presence of a player base. Repeated identical sounds
are deduplicated, different cues can strengthen a block, and stale evidence fades.

## Range
There is **no artificial listening-distance cap** in this addon. Any sound
instance Minecraft actually receives can be tracked, even if its reported
coordinates are outside the current render distance. There is likewise no
custom maximum render distance for markers.

**A client-side addon cannot obtain sounds the server does not transmit.**
Servers and Minecraft's sound engine limit what sound events reach the client.
A source behind an unloaded chunk, outside the server's sound broadcast range,
or with no vanilla sound cannot be reconstructed by this addon. Hopper item
transfer is silent in vanilla; minecart noises are merely weak hints.

## Settings
Modules > Acoustic Radar > base-sound-radar.
Individual sound categories, minimum visible color tier, marker transparency,
expiry time, red alerts, and optional self-sound filtering can be customized.

Performance: bounded memory (up to 1024 distinct source voxels), periodic
expiration, source-level sound cooldowns. Detection history is session-local and
is cleared when you change dimensions or disconnect.

## Install
Use Java 21, Minecraft Java **1.21.11**, matching Meteor Client and Fabric Loader.
Place `acoustic-base-radar-1.2.0.jar` in the instance's `mods` folder. Delete
the older `acoustic-base-radar-1.1.0.jar` to avoid duplicate mod IDs.

## Build and tests
```sh
gradle clean build
javac -d build/scorer-tests src/main/java/dev/acousticradar/RadarScorer.java src/test/java/dev/acousticradar/RadarScorerTest.java
java -ea -cp build/scorer-tests dev.acousticradar.RadarScorerTest
```

The Gradle **remapped** `build/libs/acoustic-base-radar-1.2.0.jar` is the installable addon.

Saturn reference:
https://github.com/Memeruler-k/Saturn-Addon/blob/main/src/main/java/dev/saturn/addon/modules/Exploit/SoundLocator.java

# Acoustic Base Radar — Meteor Client 1.21.1 / Fabric

A standalone addon based on the event-listening *approach* of Saturn Addon's SoundLocator, with entirely new scoring and clustering code.

## What it does
- Listens to real sound instances surfaced through Meteor's `PlaySoundEvent`.
- Handles chest/barrel/shulker sounds, villagers, redstone mechanisms, workstations, player activity, and optionally farm animals.
- Groups events by nearby coordinates and tracks separate evidence classes.
- Shows six 3D box colors: white → light yellow → yellow → light orange → orange → red.
- Applies decay and deduplication to reduce false positives from repeated idle sounds.
- Clears history on disconnect/dimension change, no disk tracking, no server packet injection.
- Red is a high *relative evidence score*, not proof of a player-built base.

**Limitations:** Vanilla hoppers do not emit a sound when transferring items; they cannot be found through sound events. The module only receives sounds supplied to your client by the server, not remote/hidden chunks. Villager villages and machinery may produce false positives.

## Build
Requires Java 21 and Gradle 8.11, with internet access for Fabric Loom/Minecraft/Meteor dependencies:

```sh
gradle build
```

Place `build/libs/acoustic-base-radar-1.0.0.jar` in the instance's `mods` folder with the **Minecraft 1.21.1** compatible Meteor Client and Fabric Loader. In Meteor open **Modules → Acoustic Radar → base-sound-radar**. The module starts **off** by default.

The Gradle-produced remapped JAR is the deployable artifact, NOT any `-dev.jar`.

## Reference
Saturn SoundLocator: https://github.com/Memeruler-k/Saturn-Addon/blob/main/src/main/java/dev/saturn/addon/modules/Exploit/SoundLocator.java
This is an independent implementation, not a copied Saturn module.

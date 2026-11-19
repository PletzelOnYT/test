package dev.acousticradar;

import meteordevelopment.meteorclient.addons.MeteorAddon;
import meteordevelopment.meteorclient.systems.modules.Category;
import meteordevelopment.meteorclient.systems.modules.Modules;
import net.minecraft.item.Items;

public final class AcousticRadarAddon extends MeteorAddon {
    public static final Category CATEGORY =
        new Category("Acoustic Radar", Items.NOTE_BLOCK.getDefaultStack());

    @Override
    public void onRegisterCategories() {
        Modules.registerCategory(CATEGORY);
    }

    @Override
    public void onInitialize() {
        Modules.get().add(new BaseSoundRadar());
    }

    @Override
    public String getPackage() {
        return "dev.acousticradar";
    }
}

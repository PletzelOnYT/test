/*
 * High-Tech Weapons v1.12 for Sandboxels
 * Rebuilt from the supplied weapons.js fragment.
 *
 * Install: place this file in Sandboxels/mods and enable it in Mods.
 */

(function () {
    "use strict";

    var MOD_VERSION = "1.12";
    // Sandboxels builds the picker from its known category names. Registering
    // directly in the built-in Weapons tab is the most compatible option.
    var CATEGORY = "weapons";
    var DEFAULT_NUKE_RADIUS = 82;
    var MAX_NUKE_RADIUS = 120;

    function empty(x, y) {
        return !outOfBounds(x, y) && isEmpty(x, y, true);
    }

    function put(name, x, y, setup) {
        if (!empty(x, y) || !elements[name]) return null;
        createPixel(name, x, y);
        var p = pixelMap[x] && pixelMap[x][y];
        if (p && setup) setup(p);
        return p;
    }

    function circleSamples(cx, cy, radius, count, callback) {
        count = Math.max(24, Math.min(count || Math.ceil(radius * 5.5), 720));
        for (var i = 0; i < count; i++) {
            var a = (Math.PI * 2 * i / count) + (Math.random() - 0.5) * 0.018;
            callback(Math.round(cx + Math.cos(a) * radius), Math.round(cy + Math.sin(a) * radius), a);
        }
    }

    function diskSamples(cx, cy, radius, count, callback) {
        for (var i = 0; i < count; i++) {
            var a = Math.random() * Math.PI * 2;
            var r = Math.sqrt(Math.random()) * radius;
            callback(Math.round(cx + Math.cos(a) * r), Math.round(cy + Math.sin(a) * r), r);
        }
    }

    function nuclearDamageAt(x, y, strength, originX, originY) {
        if (outOfBounds(x, y) || isEmpty(x, y, true)) return;
        var target = pixelMap[x][y];
        if (!target || target.element === "nuclear_controller") return;
        var info = elements[target.element] || {};
        target.temp = Math.max(target.temp || 20, 1400 + strength * 6500);
        if (strength > 0.70 && Math.random() < 0.58 + strength * 0.35) {
            deletePixel(x, y);
            if (Math.random() < 0.30) put("nuclear_fire", x, y);
        } else if (strength > 0.30 && info.state === "solid" && Math.random() < strength * 0.30) {
            if (elements.molten_rock) changePixel(target, "molten_rock");
        }
        if (pixelMap[x] && pixelMap[x][y]) {
            var p = pixelMap[x][y];
            p.vx = (p.vx || 0) + Math.sign(x - originX) * Math.ceil(strength * 5);
            p.vy = (p.vy || 0) + Math.sign(y - originY) * Math.ceil(strength * 3);
        }
    }

    function beginNuclearDetonation(x, y, radius) {
        radius = Math.max(28, Math.min(radius || DEFAULT_NUKE_RADIUS, MAX_NUKE_RADIUS));
        if (!outOfBounds(x, y) && !isEmpty(x, y, true)) deletePixel(x, y);
        var controller = put("nuclear_controller", x, y, function (p) {
            p.age = 0;
            p.blastRadius = radius;
            p.originX = x;
            p.originY = y;
        });
        if (!controller) {
            // Find a nearby empty cell so the staged effect always has a controller.
            for (var r = 1; r < 5 && !controller; r++) {
                for (var dx = -r; dx <= r && !controller; dx++) {
                    controller = put("nuclear_controller", x + dx, y - r, function (p) {
                        p.age = 0; p.blastRadius = radius; p.originX = x; p.originY = y;
                    });
                }
            }
        }
        return controller;
    }

    elements.nuclear_flash = {
        color: ["#ffffff", "#fffbd1", "#fff09a"],
        category: CATEGORY,
        state: "gas",
        density: 0.01,
        temp: 12000,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            if (pixel.life > 2 + Math.random() * 3) deletePixel(pixel.x, pixel.y);
        }
    };

    elements.nuclear_fire = {
        color: ["#ffffff", "#fff36a", "#ff9d00", "#ff3b00"],
        category: CATEGORY,
        state: "gas",
        density: 0.08,
        temp: 9000,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            var dx = Math.floor(Math.random() * 3) - 1;
            tryMove(pixel, pixel.x + dx, pixel.y - 1);
            if (pixel.life > 18 + Math.random() * 16) changePixel(pixel, "nuclear_smoke");
            else doDefaults(pixel);
        }
    };

    elements.nuclear_smoke = {
        color: ["#1d1b1a", "#302b27", "#4a4037", "#665647", "#8b735c"],
        category: CATEGORY,
        state: "gas",
        density: 0.15,
        temp: 850,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            var drift = Math.random() < 0.24 ? (Math.random() < 0.5 ? -1 : 1) : 0;
            if (!tryMove(pixel, pixel.x + drift, pixel.y - 1) && Math.random() < 0.35) {
                tryMove(pixel, pixel.x + (Math.random() < 0.5 ? -1 : 1), pixel.y);
            }
            if (pixel.life > 190 && Math.random() < 0.035) deletePixel(pixel.x, pixel.y);
            else doDefaults(pixel);
        }
    };

    elements.nuclear_shockwave = {
        color: ["#fffbd8", "#ead9b6", "#cbbca2"],
        category: CATEGORY,
        state: "gas",
        density: 0.02,
        temp: 700,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            if (pixel.life > 3) deletePixel(pixel.x, pixel.y);
        }
    };

    elements.radioactive_fallout = {
        color: ["#718431", "#899d3b", "#4e6123", "#9b8b4c"],
        category: CATEGORY,
        state: "solid",
        behavior: behaviors.POWDER,
        density: 420,
        temp: 180,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            if (pixel.life > 400 && Math.random() < 0.003) {
                if (elements.radiation && Math.random() < 0.5) changePixel(pixel, "radiation");
                else deletePixel(pixel.x, pixel.y);
            } else doDefaults(pixel);
        }
    };

    elements.nuclear_controller = {
        color: "#ffffff",
        category: CATEGORY,
        state: "gas",
        density: 99999,
        hidden: true,
        excludeRandom: true,
        tick: function (pixel) {
            var age = pixel.age = (pixel.age || 0) + 1;
            var radius = pixel.blastRadius || DEFAULT_NUKE_RADIUS;
            var ox = pixel.originX === undefined ? pixel.x : pixel.originX;
            var oy = pixel.originY === undefined ? pixel.y : pixel.originY;

            // Initial white flash and expanding incandescent fireball.
            if (age <= 10) {
                var fireRadius = Math.min(radius * 0.34, age * radius / 25);
                diskSamples(ox, oy, fireRadius, 80 + age * 16, function (x, y, r) {
                    var strength = 1 - r / Math.max(1, fireRadius);
                    if (empty(x, y)) put(age < 3 ? "nuclear_flash" : "nuclear_fire", x, y);
                    else nuclearDamageAt(x, y, 0.75 + strength * 0.25, ox, oy);
                });
            }

            // Supersonic pressure front: a visible ring with terrain heating and impulse.
            var waveRadius = Math.floor(age * 3.2);
            if (waveRadius <= radius) {
                circleSamples(ox, oy, waveRadius, Math.ceil(waveRadius * 6), function (x, y) {
                    if (empty(x, y)) put("nuclear_shockwave", x, y);
                    else nuclearDamageAt(x, y, 1 - waveRadius / (radius * 1.45), ox, oy);
                });
                circleSamples(ox, oy, Math.max(1, waveRadius - 2), Math.ceil(waveRadius * 4), function (x, y) {
                    if (!isEmpty(x, y, true)) nuclearDamageAt(x, y, 1 - waveRadius / (radius * 1.25), ox, oy);
                });
            }

            // Procedural mushroom stem, rolling cap, and hot central updraft.
            if (age >= 5 && age <= 74) {
                var rise = Math.min(radius * 0.92, (age - 4) * 1.18);
                var stemWidth = Math.max(2, Math.floor(radius * 0.055 + age * 0.018));
                for (var s = 0; s < 16; s++) {
                    var sy = Math.round(oy - Math.random() * rise);
                    var taper = 0.45 + (oy - sy) / Math.max(1, rise) * 0.7;
                    var sx = Math.round(ox + (Math.random() - 0.5) * stemWidth * 2 * taper);
                    put(Math.random() < 0.24 ? "nuclear_fire" : "nuclear_smoke", sx, sy);
                }
                var capY = Math.round(oy - rise);
                var capRadius = Math.min(radius * 0.46, 3 + Math.max(0, age - 8) * 0.62);
                for (var c = 0; c < 34; c++) {
                    var ca = Math.random() * Math.PI * 2;
                    var cr = capRadius * (0.35 + Math.random() * 0.65);
                    var cx = Math.round(ox + Math.cos(ca) * cr);
                    var cy = Math.round(capY + Math.sin(ca) * cr * 0.40);
                    put(Math.random() < 0.18 ? "nuclear_fire" : "nuclear_smoke", cx, cy);
                }
            }

            // Fallout begins after the cloud forms and spreads wider than the fireball.
            if (age >= 32 && age <= 115) {
                for (var f = 0; f < 8; f++) {
                    var fx = Math.round(ox + (Math.random() - 0.5) * radius * 1.75);
                    var fy = Math.round(oy - radius * (0.35 + Math.random() * 0.55));
                    put("radioactive_fallout", fx, fy);
                }
            }

            if (age > 125) deletePixel(pixel.x, pixel.y);
        }
    };

    elements.realistic_nuke = {
        color: ["#31383b", "#454f52", "#727d78", "#c8a83e"],
        category: CATEGORY,
        state: "solid",
        density: 7800,
        conduct: 1,
        hardness: 0.86,
        burn: 0,
        tempHigh: 650,
        excludeRandom: true,
        cooldown: (typeof defaultCooldown !== "undefined" ? defaultCooldown : 1),
        desc: "REALISTIC NUKE — ignite with electricity or heat. Creates a staged flash, destructive shockwave, procedural mushroom cloud and fallout.",
        tick: function (pixel) {
            pixel.armedTicks = pixel.armedTicks || 0;
            if (pixel.charge || pixel.temp >= 650 || pixel.burning) pixel.armedTicks++;
            else pixel.armedTicks = 0;
            if (pixel.armedTicks >= 3) beginNuclearDetonation(pixel.x, pixel.y, DEFAULT_NUKE_RADIUS);
            else doDefaults(pixel);
        }
    };

    function impactExplosive(name, options) {
        elements[name] = {
            color: options.color,
            category: CATEGORY,
            state: "solid",
            density: options.density || 1300,
            conduct: options.conduct || 0,
            excludeRandom: true,
            cooldown: (typeof defaultCooldown !== "undefined" ? defaultCooldown : 1),
            desc: options.desc,
            tick: function (pixel) {
                if (options.speed) {
                    for (var i = 0; i < options.speed; i++) {
                        if (!tryMove(pixel, pixel.x, pixel.y + 1)) {
                            explodeAt(pixel.x, pixel.y, options.power, options.payload);
                            return;
                        }
                    }
                } else if (!tryMove(pixel, pixel.x, pixel.y + 1)) {
                    explodeAt(pixel.x, pixel.y, options.power, options.payload);
                }
                if (pixel.charge || pixel.temp > (options.ignition || 500)) explodeAt(pixel.x, pixel.y, options.power, options.payload);
                else doDefaults(pixel);
            }
        };
    }

    impactExplosive("tsar_bomba", {
        color: ["#494b45", "#6b6f65"], density: 4200, power: 150,
        payload: ["plasma", "plasma", "radiation", "fallout"],
        desc: "Extremely large legacy nuclear weapon. Use Realistic Nuke for the staged visual effect."
    });
    impactExplosive("little_boy", {
        color: ["#e8dfbf", "#77745f"], density: 5000, power: 70,
        payload: ["plasma", "plasma", "radiation", "fallout"], desc: "Compact fission bomb."
    });
    impactExplosive("fat_man", {
        color: ["#2b2b28", "#e0c328"], density: 5600, power: 98,
        payload: ["plasma", "plasma", "radiation", "fallout"], desc: "Heavy implosion bomb."
    });
    impactExplosive("fast_bomb", {
        color: "#524c41", power: 12, speed: 3, payload: "explosion", desc: "High-speed impact bomb."
    });

    elements.self_propelled_bomb = {
        color: ["#596269", "#89959b"],
        category: CATEGORY,
        state: "solid",
        density: 2000,
        conduct: 1,
        burn: 90,
        burnTime: 100,
        desc: "A powered bomb that launches upward when heated or charged.",
        tick: function (pixel) {
            if ((pixel.temp > 600 || pixel.charge) && !pixel.ignited) { pixel.ignited = true; pixel.fuse = 0; }
            if (pixel.ignited) {
                pixel.fuse++;
                if (!tryMove(pixel, pixel.x, pixel.y - 1)) tryMove(pixel, pixel.x + (Math.random() < 0.5 ? -1 : 1), pixel.y - 1);
                if (pixel.fuse > 50) explodeAt(pixel.x, pixel.y, 18, ["fire", "smoke", "explosion"]);
            } else tryMove(pixel, pixel.x, pixel.y + 1);
            doDefaults(pixel);
        }
    };

    elements.cluster_munition = {
        color: "#44484a",
        category: CATEGORY,
        state: "solid",
        density: 1800,
        behavior: ["XX|EX:10>smoke,bomb,bomb|XX", "XX|XX|XX", "M2|M1 AND EX:10>smoke,bomb,bomb,cluster_munition|M2"],
        desc: "Disperses several conventional submunitions on impact."
    };

    elements.static_bomb = {
        color: ["#34383a", "#596065"],
        category: CATEGORY,
        state: "solid",
        density: 2500,
        conduct: 1,
        behavior: ["XX|EX:12|XX", "EX:12|XX|EX:12", "XX|EX:12|XX"],
        desc: "Stationary omnidirectional explosive. Trigger with electricity or heat."
    };

    elements.liquid_bomb = {
        color: ["#474d44", "#6c745f"],
        category: CATEGORY,
        state: "liquid",
        density: 1300,
        viscosity: 7,
        conduct: 0.35,
        behavior: ["XX|EX:10>explosion|XX", "M2|XX|M2", "M1|M1 AND EX:10>explosion|M1"],
        desc: "Unstable liquid explosive."
    };

    elements.gas_bomb = {
        color: ["#777e70", "#9aa28f"],
        category: CATEGORY,
        state: "gas",
        density: 1.7,
        conduct: 0.25,
        behavior: ["M2|M1|M2", "M1|XX|M1", "M2|M1 AND EX:10>explosion|M2"],
        desc: "Volatile explosive gas."
    };

    elements.laser_bomb = {
        color: ["#2c3135", "#e62222"],
        category: CATEGORY,
        state: "solid",
        density: 3200,
        conduct: 1,
        desc: "On electric activation, fires four superheated laser beams.",
        tick: function (pixel) {
            if (!pixel.charge && pixel.temp < 650) { doDefaults(pixel); return; }
            var dirs = [[1,0],[-1,0],[0,1],[0,-1]];
            for (var d = 0; d < dirs.length; d++) {
                for (var n = 1; n < Math.max(width, height); n++) {
                    var x = pixel.x + dirs[d][0] * n;
                    var y = pixel.y + dirs[d][1] * n;
                    if (outOfBounds(x, y)) break;
                    if (isEmpty(x, y, true)) {
                        var beam = put("flash", x, y);
                        if (beam) { beam.color = "#ff2020"; beam.temp = 35000; beam.delay = n / 8; }
                    } else {
                        var hit = pixelMap[x][y];
                        if (hit) hit.temp = Math.max(hit.temp || 20, 35000);
                        break;
                    }
                }
            }
            deletePixel(pixel.x, pixel.y);
        }
    };

    elements.mini_nuke = {
        color: ["#4a4136", "#82745f"],
        category: CATEGORY,
        state: "solid",
        density: 2800,
        conduct: 1,
        excludeRandom: true,
        desc: "Small staged nuclear device.",
        tick: function (pixel) {
            if (pixel.charge || pixel.temp > 600) beginNuclearDetonation(pixel.x, pixel.y, 38);
            else { tryMove(pixel, pixel.x, pixel.y + 1); doDefaults(pixel); }
        }
    };

    elements.cluster_nuke = {
        color: ["#252829", "#545b5d"],
        category: CATEGORY,
        state: "solid",
        density: 3100,
        conduct: 1,
        excludeRandom: true,
        desc: "Experimental multi-core nuclear device.",
        tick: function (pixel) {
            if (pixel.charge || pixel.temp > 650 || !tryMove(pixel, pixel.x, pixel.y + 1)) {
                var px = pixel.x, py = pixel.y;
                beginNuclearDetonation(px, py, 58);
                setTimeout(function () {
                    var offsets = [[-25,-4],[25,-4],[-15,-18],[15,-18]];
                    for (var i = 0; i < offsets.length; i++) beginNuclearDetonation(px + offsets[i][0], py + offsets[i][1], 32);
                }, 300);
            } else doDefaults(pixel);
        }
    };

    if (typeof runAfterLoad === "function") {
        runAfterLoad(function () {
            if (typeof logMessage === "function") logMessage("High-Tech Weapons v" + MOD_VERSION + " loaded. Realistic Nuke is ready.");
        });
    }
})();

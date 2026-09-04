/*
 * High-Tech Weapons v2.24 for Sandboxels
 * Eight weapons, three aircraft, specialized effects, and a living City worldgen preset.
 */
(function () {
    "use strict";

    var MOD_VERSION = "2.24";
    var CATEGORY = "weapons";
    var AIRCRAFT_CATEGORY = "aircraft";
    var SPECIAL_CATEGORY = "special";
    var MAX_CUSTOM_RADIUS = 999;
    var MAX_SHOCKWAVE_RADIUS = 260;
    var BLACK_HOLE_LIFETIME_MS = 150000;

    // EASY TUNING: change these numbers to resize explosions and shockwaves.
    // Quakewave intentionally stays at 8 / 175 because it is the dedicated shockwave bomb.
    var BOMB_TUNING = {
        littleBoy: { preBlast: 20, explosion: 70, shockwave: 90 },
        fatMan: { preBlast: 28, explosion: 98, shockwave: 128 },
        tsarBomba: { explosion: 150, shockwave: 195 },
        quakewave: { explosion: 8, shockwave: 175 },
        carpetBomb: { explosion: 13, shockwave: 24 },
        b2Nuke: { explosion: 110, shockwave: 145 },
        auroraBomb: { pulse: 10, shockwave: 56 },
        orbitalStrike: { coreBlast: 8, plasmaBlast: 18, shockwave: 38 },
        customBomb: { defaultExplosion: 40, shockwaveScale: 1.25, maxShockwave: 260 }
    };

    // EASY CITY TUNING: change these values to reshape the instant City preset.
    var CITY_TUNING = {
        streetLevel: 0.82,
        minBuildingHeight: 20, maxBuildingHeight: 72,
        minBuildingWidth: 5, maxBuildingWidth: 9,
        minBuildingGap: 11, maxBuildingGap: 20,
        peoplePerGap: 3,
        carEveryGaps: 2,
        treeEveryGaps: 3,
        streetlightEveryGap: true,
        sewerEnabled: true,
        sewerCeilingDepth: 4,
        sewerRoomHeight: 4,
        sewerPillarSpacing: 14,
        manholeSpacing: 32,
        rareBuildingChance: 0.025,
        compactDistrictChance: 0.35,
        compactDistrictMinBuildings: 5,
        compactDistrictMaxBuildings: 9,
        collapsibleFloors: true,
        airRaidSirens: true,
        subwayEnabled: true
    };

    var cityRaidUntil = 0;
    var cityRaidTargetX = null;
    function triggerCityAirRaid(targetX, durationMs) {
        cityRaidTargetX = Math.max(0, Math.min(width - 1, Math.round(targetX === undefined ? width / 2 : targetX)));
        cityRaidUntil = Math.max(cityRaidUntil, Date.now() + (durationMs || 14000));
    }
    function cityAirRaidActive() { return Date.now() < cityRaidUntil; }

    function inBounds(x, y) { return !outOfBounds(x, y); }
    function empty(x, y) { return inBounds(x, y) && isEmpty(x, y, true); }
    function safeDelete(x, y) { if (inBounds(x, y) && !isEmpty(x, y, true)) deletePixel(x, y); }

    function put(name, x, y, setup) {
        x = Math.round(x); y = Math.round(y);
        if (!elements[name] || !empty(x, y)) return null;
        createPixel(name, x, y);
        var pixel = pixelMap[x] && pixelMap[x][y];
        if (pixel && setup) setup(pixel);
        return pixel;
    }

    function forcePut(name, x, y, setup) {
        x = Math.round(x); y = Math.round(y);
        if (!elements[name] || !inBounds(x, y)) return null;
        safeDelete(x, y);
        createPixel(name, x, y);
        var pixel = pixelMap[x] && pixelMap[x][y];
        if (pixel && setup) setup(pixel);
        return pixel;
    }

    function circleSamples(cx, cy, radius, count, callback) {
        count = Math.max(20, Math.min(count || Math.ceil(radius * 3), 520));
        for (var i = 0; i < count; i++) {
            var angle = Math.PI * 2 * i / count;
            callback(Math.round(cx + Math.cos(angle) * radius), Math.round(cy + Math.sin(angle) * radius), angle);
        }
    }

    function diskSamples(cx, cy, radius, count, callback) {
        count = Math.max(1, Math.min(count || 1, 620));
        for (var i = 0; i < count; i++) {
            var angle = Math.random() * Math.PI * 2;
            var distance = Math.sqrt(Math.random()) * radius;
            callback(Math.round(cx + Math.cos(angle) * distance), Math.round(cy + Math.sin(angle) * distance), distance);
        }
    }

    function validPayload(payload, fallback) {
        if (!Array.isArray(payload)) return elements[payload] ? payload : fallback;
        var filtered = [];
        for (var i = 0; i < payload.length; i++) if (elements[payload[i]]) filtered.push(payload[i]);
        return filtered.length ? filtered : fallback;
    }

    function elementStateAt(x, y) {
        if (!inBounds(x, y) || isEmpty(x, y, true)) return null;
        var target = pixelMap[x] && pixelMap[x][y];
        return target && elements[target.element] ? elements[target.element].state : null;
    }

    function impactSurfaceBelow(pixel) {
        if (!inBounds(pixel.x, pixel.y + 1)) return true;
        var target = pixelMap[pixel.x] && pixelMap[pixel.x][pixel.y + 1];
        if (!target) return false;
        var definition = elements[target.element];
        // Anything that is not explicitly a gas is a physical impact surface. This
        // includes steel and modded solids that forgot to declare state:"solid".
        return !definition || definition.state !== "gas";
    }

    function fallWithoutFalseFuse(pixel, speed) {
        speed = Math.max(1, Math.min(speed || 1, 4));
        for (var i = 0; i < speed; i++) {
            if (impactSurfaceBelow(pixel)) return true;
            var nextY = pixel.y + 1;
            if (!inBounds(pixel.x, nextY)) return true;
            if (empty(pixel.x, nextY)) tryMove(pixel, pixel.x, nextY);
            else {
                var target = pixelMap[pixel.x] && pixelMap[pixel.x][nextY];
                var state = target && elements[target.element] ? elements[target.element].state : null;
                if (!target || !elements[target.element] || state !== "gas") return true;
                if (target && typeof swapPixels === "function") swapPixels(pixel, target);
                else if (!tryMove(pixel, pixel.x, nextY)) return false;
            }
        }
        return impactSurfaceBelow(pixel);
    }

    function pushPixelFrom(pixel, ox, oy, force) {
        if (!pixel) return;
        var dx = pixel.x - ox, dy = pixel.y - oy;
        var length = Math.sqrt(dx * dx + dy * dy) || 1;
        pixel.vx = (pixel.vx || 0) + dx / length * force;
        pixel.vy = (pixel.vy || 0) + dy / length * force * 0.7;
    }

    elements.bomb_shockwave = {
        color: ["#ffffff", "#ffe5aa", "#d5c7ad"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.01, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 4) deletePixel(pixel.x, pixel.y); }
    };

    function isLooseShockwaveTarget(target) {
        if (!target || !elements[target.element]) return false;
        if (target.element === "human" || target.element === "body" || target.element === "head") return true;
        var behavior = elements[target.element].behavior;
        return behavior === behaviors.POWDER || behavior === behaviors.STURDYPOWDER;
    }

    function shockwaveDamageAt(x, y, ox, oy, strength, flingLoose) {
        if (!inBounds(x, y) || isEmpty(x, y, true)) return;
        var target = pixelMap[x] && pixelMap[x][y];
        if (!target || target.element === "shockwave_controller") return;
        target.temp = Math.max(target.temp || 20, 160 + strength * 850);
        if (flingLoose && isLooseShockwaveTarget(target)) pushPixelFrom(target, ox, oy, Math.max(3, strength * 13));
    }

    elements.shockwave_controller = {
        color: "#ffffff", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hardness: 1, insulate: true, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            var radius = pixel.waveRadius || 24;
            var ringRadius = pixel.age * (pixel.waveSpeed || 4);
            var ox = pixel.originX === undefined ? pixel.x : pixel.originX;
            var oy = pixel.originY === undefined ? pixel.y : pixel.originY;
            if (ringRadius > radius) { deletePixel(pixel.x, pixel.y); return; }
            var strength = Math.max(0.08, 1 - ringRadius / Math.max(1, radius));
            circleSamples(ox, oy, ringRadius, Math.ceil(ringRadius * 3), function (x, y) {
                if (empty(x, y)) put("bomb_shockwave", x, y, function (wave) { if (pixel.waveColor) wave.color = pixel.waveColor; });
                else shockwaveDamageAt(x, y, ox, oy, strength, pixel.flingLoose);
            });
        }
    };

    function plantShockwave(x, y, radius, color, flingLoose) {
        radius = Math.max(8, Math.min(radius || 24, MAX_SHOCKWAVE_RADIUS));
        return forcePut("shockwave_controller", x, y, function (controller) {
            controller.age = 0; controller.waveRadius = radius;
            controller.waveSpeed = radius > 100 ? 6 : radius > 55 ? 5 : 4;
            controller.originX = x; controller.originY = y; controller.waveColor = color;
            controller.flingLoose = !!flingLoose;
        });
    }

    function detonateBomb(pixel, options) {
        var x = pixel.x, y = pixel.y;
        var fallback = elements.explosion ? "explosion" : (elements.fire ? "fire" : "smoke");
        safeDelete(x, y);
        if (options.preBlast) explodeAt(x, y - 1, options.preBlast, validPayload(options.preBlastPayload || ["plasma"], fallback));
        explodeAt(x, y, options.radius, validPayload(options.payload, fallback));
        if (options.afterBlast) options.afterBlast(x, y);
        plantShockwave(x, y, options.shockwave, options.waveColor, options.flingLoose);
    }

    function makeImpactBomb(name, options) {
        elements[name] = {
            color: options.color, category: CATEGORY, state: "solid", density: options.density,
            hardness: options.hardness || 0.84, burn: 0, conduct: 0, excludeRandom: true,
            cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
            desc: options.desc + " Detonates on impact with solid ground or liquid; gas, heat, and electricity cannot trigger it.",
            tick: function (pixel) {
                if (fallWithoutFalseFuse(pixel, options.speed || 1)) detonateBomb(pixel, options);
                else doDefaults(pixel);
            }
        };
    }

    var nuclearPayload = ["plasma", "plasma", "plasma", "plasma", "radiation", "fallout"];
    makeImpactBomb("little_boy", { color: "#F5F5DC", density: 500, radius: BOMB_TUNING.littleBoy.explosion, preBlast: BOMB_TUNING.littleBoy.preBlast, preBlastPayload: ["plasma"], shockwave: BOMB_TUNING.littleBoy.shockwave, waveColor: "#fff0bd", payload: nuclearPayload, desc: "Little Boy: a two-stage nuclear blast with a pressure wave larger than its fireball." });
    makeImpactBomb("fat_man", { color: ["#ffff00", "#333333"], density: 1000, radius: BOMB_TUNING.fatMan.explosion, preBlast: BOMB_TUNING.fatMan.preBlast, preBlastPayload: ["plasma"], shockwave: BOMB_TUNING.fatMan.shockwave, waveColor: "#ffe2a1", payload: nuclearPayload, desc: "Fat Man: a larger two-stage nuclear blast and wide pressure wave." });
    makeImpactBomb("tsar_bomba", { color: "#524C41", density: 1300, radius: BOMB_TUNING.tsarBomba.explosion, shockwave: BOMB_TUNING.tsarBomba.shockwave, waveColor: "#fff6d7", payload: ["plasma"], desc: "Tsar Bomba: a gigantic radiation-free plasma blast with a matching pressure front." });
    makeImpactBomb("quakewave_bomb", { color: ["#202b32", "#3c6070", "#8de5ff"], density: 6800, radius: BOMB_TUNING.quakewave.explosion, shockwave: BOMB_TUNING.quakewave.shockwave, waveColor: "#c8f5ff", flingLoose: true, payload: ["explosion", "fire", "smoke"], desc: "Quakewave Bomb: the one enormous-shockwave weapon. Its pressure front violently flings people and loose powders while its explosion stays small." });

    var AURORA_COLORS = ["#d8fff8", "#69ffd2", "#39d9c5", "#6e9dff", "#d16dff", "#ff7bd5"];
    elements.aurora_light = {
        color: AURORA_COLORS, category: SPECIAL_CATEGORY, state: "gas", density: 0.0001,
        hidden: true, excludeRandom: true, insulate: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 7 + Math.random() * 5) deletePixel(pixel.x, pixel.y); }
    };
    elements.aurora_controller = {
        color: "#69ffd2", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hardness: 1, hidden: true, excludeRandom: true, insulate: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            var span = Math.min(95, 25 + pixel.age * 0.55);
            var top = Math.max(3, pixel.originY - Math.min(72, 28 + pixel.age * 0.2));
            for (var band = 0; band < 5; band++) {
                for (var sample = 0; sample < 22; sample++) {
                    var dx = Math.round(-span + Math.random() * span * 2);
                    var ribbonY = top + 5 + band * 6 + Math.round(Math.sin(dx * 0.12 + pixel.age * 0.11 + band) * (4 + band));
                    var curtain = 2 + Math.floor(Math.random() * 11);
                    for (var drop = 0; drop < curtain; drop++) {
                        if (Math.random() < 0.56) put("aurora_light", pixel.originX + dx, ribbonY + drop, function (light) {
                            light.color = AURORA_COLORS[(band + drop + Math.floor(Math.random() * 2)) % AURORA_COLORS.length];
                        });
                    }
                }
            }
            if (pixel.age > 260) deletePixel(pixel.x, pixel.y);
        }
    };
    elements.aurora_bomb = {
        color: ["#50ffe1", "#708cff", "#d873ff"], category: CATEGORY, state: "solid", density: 4100,
        hardness: 0.9, burn: 0, conduct: 0, excludeRandom: true,
        cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Aurora Bomb: creates wide, flowing blue-green-violet light curtains across the sky instead of a normal fireball. Detonates on solid or liquid impact.",
        tick: function (pixel) {
            if (!fallWithoutFalseFuse(pixel, 1)) { doDefaults(pixel); return; }
            var x = pixel.x, y = pixel.y;
            safeDelete(x, y);
            explodeAt(x, y, BOMB_TUNING.auroraBomb.pulse, validPayload(["electric", "light", "plasma"], "explosion"));
            plantShockwave(x, y, BOMB_TUNING.auroraBomb.shockwave, "#9cfff2");
            forcePut("aurora_controller", x, Math.max(2, y - 2), function (controller) {
                controller.age = 0; controller.originX = x; controller.originY = y;
            });
        }
    };

    elements.custom_bomb = {
        color: ["#59276e", "#a44bd1", "#e2a7ff"], category: CATEGORY, state: "solid",
        density: 3200, hardness: 0.84, burn: 0, conduct: 0, excludeRandom: true,
        cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        properties: { customRadius: BOMB_TUNING.customBomb.defaultExplosion },
        desc: "Choose an explosion radius from 1 to 999. Detonates on solid or liquid impact.",
        onSelect: function () {
            var applyRadius = function (value) {
                var radius = Math.round(Number(value));
                if (!isFinite(radius)) radius = BOMB_TUNING.customBomb.defaultExplosion;
                radius = Math.max(1, Math.min(MAX_CUSTOM_RADIUS, radius));
                if (typeof currentElementProp !== "undefined") currentElementProp = { customRadius: radius };
            };
            if (typeof promptInput === "function") promptInput("Explosion radius (1-999)", applyRadius, "Custom Bomb", "40");
            else if (typeof prompt === "function") applyRadius(prompt("Explosion radius (1-999)", "40"));
        },
        tick: function (pixel) {
            if (fallWithoutFalseFuse(pixel, 1)) {
                var radius = Math.max(1, Math.min(MAX_CUSTOM_RADIUS, Math.round(pixel.customRadius || BOMB_TUNING.customBomb.defaultExplosion)));
                detonateBomb(pixel, { radius: radius, shockwave: Math.min(BOMB_TUNING.customBomb.maxShockwave, Math.max(8, Math.round(radius * BOMB_TUNING.customBomb.shockwaveScale))), payload: ["explosion", "fire", "smoke"], waveColor: "#e5c3ff" });
            } else doDefaults(pixel);
        }
    };

    var BLACK_HOLE_COLORS = ["#000003", "#010006", "#020109", "#04010d", "#070216", "#0b041c"];
    elements.black_hole_void = {
        color: BLACK_HOLE_COLORS, category: SPECIAL_CATEGORY, state: "solid", density: 999999,
        hardness: 1, insulate: true, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            var core = pixelMap[pixel.coreX] && pixelMap[pixel.coreX][pixel.coreY];
            if (!core || core.element !== "black_hole_core") { deletePixel(pixel.x, pixel.y); return; }
            var dx = pixel.x - core.x, dy = pixel.y - core.y;
            if (Math.sqrt(dx * dx + dy * dy) > (core.horizon || 4) + 0.8) deletePixel(pixel.x, pixel.y);
        }
    };
    elements.black_hole_disk = {
        color: ["#fffbd0", "#ffd63f", "#ff8a00", "#dc3c08"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.01, temp: 9000, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 4 + Math.random() * 3) deletePixel(pixel.x, pixel.y); }
    };
    elements.black_hole_photon_ring = {
        color: ["#ffffff", "#fff1a1", "#ffad20"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.001, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 3) deletePixel(pixel.x, pixel.y); }
    };
    elements.black_hole_jet = {
        color: ["#e9fbff", "#83d8ff", "#4d7eff"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.001, temp: 14000, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 4) deletePixel(pixel.x, pixel.y); }
    };

    function isBlackHolePart(name) { return name === "black_hole_core" || name === "black_hole_void" || name === "black_hole_disk" || name === "black_hole_photon_ring" || name === "black_hole_jet"; }
    function consumeMatter(core, target) { if (target && target !== core && !isBlackHolePart(target.element)) { safeDelete(target.x, target.y); core.consumed = (core.consumed || 0) + 1; } }

    function pullIntoBlackHole(core, horizon, suctionRadius) {
        var influence = Math.max(horizon + 2, suctionRadius || 26 + horizon * 2.2), targets = [];
        if (typeof currentPixels !== "undefined" && currentPixels && currentPixels.slice) targets = currentPixels.slice();
        else {
            for (var x = Math.max(0, Math.floor(core.x - influence)); x <= Math.min(width - 1, Math.ceil(core.x + influence)); x++) {
                for (var y = Math.max(0, Math.floor(core.y - influence)); y <= Math.min(height - 1, Math.ceil(core.y + influence)); y++) if (pixelMap[x] && pixelMap[x][y]) targets.push(pixelMap[x][y]);
            }
        }
        for (var i = 0; i < targets.length; i++) {
            var target = targets[i];
            if (!target || target === core || isBlackHolePart(target.element) || !pixelMap[target.x] || pixelMap[target.x][target.y] !== target) continue;
            var dx = core.x - target.x, dy = core.y - target.y, distance = Math.sqrt(dx * dx + dy * dy);
            if (distance > influence) continue;
            if (distance <= horizon + 1) { consumeMatter(core, target); continue; }
            target.vx = (target.vx || 0) + dx / Math.max(1, distance) * 0.8;
            target.vy = (target.vy || 0) + dy / Math.max(1, distance) * 0.8;
            var sx = target.x === core.x ? 0 : (target.x < core.x ? 1 : -1);
            var sy = target.y === core.y ? 0 : (target.y < core.y ? 1 : -1);
            if (!tryMove(target, target.x + sx, target.y + sy)) {
                if (!tryMove(target, target.x + sx, target.y)) tryMove(target, target.x, target.y + sy);
            }
        }
    }

    function drawBlackHole(core, horizon) {
        diskSamples(core.x, core.y, horizon, Math.min(400, 75 + horizon * 9), function (x, y, distance) {
            put("black_hole_void", x, y, function (pixel) { pixel.coreX = core.x; pixel.coreY = core.y; var edge = distance > horizon * 0.72 ? 2 : 0; pixel.color = BLACK_HOLE_COLORS[Math.min(BLACK_HOLE_COLORS.length - 1, edge + Math.floor(Math.random() * 4))]; });
        });
        var photonRadius = Math.max(5, horizon * 1.12);
        circleSamples(core.x, core.y, photonRadius, Math.ceil(photonRadius * 5), function (x, y) { put("black_hole_photon_ring", x, y); });
        var diskOuter = Math.max(10, horizon * 2.4), count = Math.min(300, 100 + Math.floor(horizon * 7));
        for (var i = 0; i < count; i++) {
            var angle = Math.random() * Math.PI * 2;
            var radial = horizon * 1.02 + Math.random() * (diskOuter - horizon * 1.02);
            var x = Math.round(core.x + Math.cos(angle) * radial);
            var y = Math.round(core.y + Math.sin(angle) * radial * 0.17 + Math.cos(angle) * horizon * 0.07);
            put("black_hole_disk", x, y, function (pixel) { pixel.color = x < core.x ? (Math.random() < 0.5 ? "#fff7b0" : "#ffd339") : (Math.random() < 0.5 ? "#ff7900" : "#d83a08"); });
        }
        // Keep newborn jets compact, then scale both dimensions with the horizon.
        var jetLength = Math.max(4, horizon * 1.2);
        var jetWidth = Math.max(1, Math.floor(horizon * 0.11));
        for (var direction = -1; direction <= 1; direction += 2) {
            for (var d = horizon + 2; d < horizon + jetLength; d++) {
                var progress = (d - horizon) / jetLength;
                var halfWidth = Math.max(1, Math.round(jetWidth * (1 - progress * 0.82)));
                for (var offset = -halfWidth; offset <= halfWidth; offset++) {
                    if (Math.random() < 0.72 - Math.abs(offset) / (halfWidth + 1) * 0.24) {
                        put("black_hole_jet", core.x + offset, core.y + direction * d, function (jet) {
                            jet.color = Math.random() < 0.34 ? "#efffff" : (Math.random() < 0.5 ? "#79dfff" : "#586dff");
                        });
                    }
                }
            }
        }
    }

    function collapseBlackHole(core) {
        var cx = core.x, cy = core.y, horizon = core.horizon || 4;
        if (typeof currentPixels !== "undefined" && currentPixels && currentPixels.slice) {
            var parts = currentPixels.slice();
            for (var i = 0; i < parts.length; i++) {
                var part = parts[i];
                if (part && isBlackHolePart(part.element) && pixelMap[part.x] && pixelMap[part.x][part.y] === part) safeDelete(part.x, part.y);
            }
        } else safeDelete(cx, cy);
        var supernovaRadius = Math.min(300, Math.max(95, Math.round(horizon * 2.8)));
        explodeAt(cx, cy, Math.max(18, Math.round(horizon * 0.65)), ["plasma", "light"]);
        explodeAt(cx, cy, supernovaRadius, validPayload(["plasma", "fire", "light", "radiation"], "explosion"));
        plantShockwave(cx, cy, Math.min(MAX_SHOCKWAVE_RADIUS, Math.max(120, Math.round(supernovaRadius * 1.2))), "#d9f3ff");
    }

    elements.black_hole_core = {
        color: BLACK_HOLE_COLORS, category: SPECIAL_CATEGORY, state: "solid", density: 999999,
        hardness: 1, insulate: true, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; pixel.consumed = pixel.consumed || 0;
            pixel.bornAt = pixel.bornAt || Date.now();
            var elapsed = Math.max(0, Date.now() - pixel.bornAt);
            if (elapsed >= BLACK_HOLE_LIFETIME_MS) { collapseBlackHole(pixel); return; }
            pixel.horizon = Math.min(36, 4 + elapsed / 2200 + pixel.age / 70 + Math.sqrt(pixel.consumed) * 0.015);
            pixel.suctionRadius = 26 + elapsed / 1300 + pixel.age / 55 + Math.sqrt(pixel.consumed) * 0.03;
            pullIntoBlackHole(pixel, pixel.horizon, pixel.suctionRadius); drawBlackHole(pixel, pixel.horizon);
        }
    };
    function createBlackHole(x, y) { return forcePut("black_hole_core", x, y, function (core) { core.age = 0; core.consumed = 0; core.horizon = 4; core.suctionRadius = 26; core.bornAt = Date.now(); }); }
    elements.realistic_black_hole = {
        color: ["#020205", "#191020", "#ff8a00"], category: CATEGORY, state: "solid", density: 9000,
        hardness: 1, burn: 0, conduct: 0, excludeRandom: true,
        cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Creates a consuming black hole with a 36-pixel maximum horizon, a suction field that keeps expanding, and a supernova after 2.5 minutes.",
        tick: function (pixel) { if (fallWithoutFalseFuse(pixel, 1)) createBlackHole(pixel.x, pixel.y); else doDefaults(pixel); }
    };

    elements.carpet_bomb = {
        color: ["#3f4546", "#697071"], category: SPECIAL_CATEGORY, state: "solid", density: 5200,
        hardness: 0.8, hidden: true, excludeRandom: true,
        tick: function (pixel) { if (fallWithoutFalseFuse(pixel, 2)) detonateBomb(pixel, { radius: BOMB_TUNING.carpetBomb.explosion, shockwave: BOMB_TUNING.carpetBomb.shockwave, payload: ["explosion", "fire", "smoke"], waveColor: "#ffd59a" }); else doDefaults(pixel); }
    };
    elements.fighter_jet_pixel = {
        color: ["#9aa5a9", "#c3cbd0", "#49545a"], category: SPECIAL_CATEGORY, state: "gas", density: 0.001,
        hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 2) deletePixel(pixel.x, pixel.y); }
    };

    function drawFighterJet(controller) {
        var direction = controller.direction || 1;
        var shape = [[-10,0],[-9,0],[-8,0],[-7,0],[-6,0],[-5,0],[-4,0],[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0],[10,0],[-7,-1],[-6,-1],[-1,-1],[0,-1],[1,-1],[2,-1],[3,-1],[4,-1],[5,-1],[6,-1],[-7,-2],[-6,-2],[1,-2],[2,-2],[3,-2],[4,-2],[-8,-3],[-7,-3],[2,-3],[3,-3],[-5,1],[-4,1],[-3,1],[-2,1],[-1,1],[0,1],[1,1],[2,1],[3,1],[4,1],[-3,2],[-2,2],[-1,2],[0,2],[1,2],[2,2]];
        for (var i = 0; i < shape.length; i++) {
            var dx = shape[i][0] * direction, dy = shape[i][1];
            put("fighter_jet_pixel", controller.x + dx, controller.y + dy, function (pixel) { if (dy === -2 && Math.abs(dx) < 5) pixel.color = "#79bde8"; else if (dy === 2) pixel.color = "#626b70"; else if (Math.abs(dx) === 10) pixel.color = "#d7dde0"; });
        }
        put("fighter_jet_pixel", controller.x - 9 * direction, controller.y, function (pixel) { pixel.color = "#ff8a20"; });
    }

    elements.fighter_jet_controller = {
        color: "#aab3b8", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawFighterJet(pixel);
            if (pixel.age > 8 && pixel.age % 5 === 0) {
                put("carpet_bomb", pixel.x - 3 * pixel.direction, pixel.y + 4, function (bomb) { bomb.direction = pixel.direction; });
                pixel.bombsDropped = (pixel.bombsDropped || 0) + 1;
            }
            for (var step = 0; step < 2; step++) {
                var nx = pixel.x + pixel.direction;
                if (!inBounds(nx, pixel.y)) { deletePixel(pixel.x, pixel.y); return; }
                if (!tryMove(pixel, nx, pixel.y)) { safeDelete(nx, pixel.y); tryMove(pixel, nx, pixel.y); }
            }
        }
    };

    function summonFighterJet(targetY) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? 12 : width - 13;
        var altitude = Math.max(10, Math.min(Math.floor(height * 0.34), targetY - 28));
        triggerCityAirRaid(Math.floor(width / 2), 18000);
        return forcePut("fighter_jet_controller", startX, altitude, function (jet) { jet.age = 0; jet.direction = direction; jet.bombsDropped = 0; });
    }
    elements.fighter_jet_strike = {
        color: ["#78858c", "#c1ccd1", "#5da6cf"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Place this beacon to summon a detailed pixel-art fighter jet that flies across the sky and carpet-bombs solid ground.",
        tick: function (pixel) { var targetY = pixel.y; safeDelete(pixel.x, pixel.y); summonFighterJet(targetY); }
    };

    elements.b2_nuclear_payload = {
        color: ["#292d31", "#4b5054"], category: SPECIAL_CATEGORY, state: "solid", density: 6200,
        hardness: 0.9, burn: 0, conduct: 0, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            if (fallWithoutFalseFuse(pixel, 2)) detonateBomb(pixel, { radius: BOMB_TUNING.b2Nuke.explosion, shockwave: BOMB_TUNING.b2Nuke.shockwave, payload: nuclearPayload, waveColor: "#fff0c2" });
            else doDefaults(pixel);
        }
    };
    elements.b2_bomber_pixel = {
        color: ["#171a1c", "#252a2d", "#353b3e"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.001, hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 2) deletePixel(pixel.x, pixel.y); }
    };

    function drawB2Bomber(controller) {
        var direction = controller.direction || 1;
        // Side-on B-2: a long, extremely thin tailless flying wing with a low cockpit hump.
        var rows = [
            { y: -3, from: 5, to: 10 },
            { y: -2, from: 1, to: 14 },
            { y: -1, from: -10, to: 17 },
            { y: 0, from: -18, to: 21 },
            { y: 1, from: -16, to: 16 },
            { y: 2, from: -12, to: 10 },
            { y: 3, from: -7, to: 4 }
        ];
        for (var r = 0; r < rows.length; r++) {
            var row = rows[r];
            for (var dx = row.from; dx <= row.to; dx++) {
                if (row.y > 0 && dx < 0 && (-dx + row.y) % 6 === 0) continue;
                put("b2_bomber_pixel", controller.x + dx * direction, controller.y + row.y, function (part) {
                    var edge = dx === row.from || dx === row.to || row.y === -3 || row.y === 3;
                    part.color = edge ? "#596166" : (Math.random() < 0.12 ? "#353b3f" : "#15191c");
                });
            }
        }
        for (var cockpitX = 6; cockpitX <= 11; cockpitX++) forcePut("b2_bomber_pixel", controller.x + cockpitX * direction, controller.y - 2, function (part) { part.color = "#557f98"; });
        for (var intake = -2; intake <= 4; intake++) forcePut("b2_bomber_pixel", controller.x + intake * direction, controller.y - 1, function (part) { part.color = "#080a0b"; });
        forcePut("b2_bomber_pixel", controller.x - 15 * direction, controller.y, function (part) { part.color = "#b95e2c"; });
        forcePut("b2_bomber_pixel", controller.x - 13 * direction, controller.y + 1, function (part) { part.color = "#b95e2c"; });
    }

    elements.b2_bomber_controller = {
        color: "#1b1f21", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            drawB2Bomber(pixel);
            var reachedTarget = pixel.direction > 0 ? pixel.x >= pixel.targetX : pixel.x <= pixel.targetX;
            if (!pixel.dropped && reachedTarget) {
                var payload = put("b2_nuclear_payload", pixel.x, pixel.y + 5, function (bomb) { bomb.direction = pixel.direction; });
                if (payload) { pixel.dropped = true; pixel.bombsDropped = 1; }
            }
            for (var step = 0; step < 2; step++) {
                var nx = pixel.x + pixel.direction;
                if (!inBounds(nx, pixel.y)) { deletePixel(pixel.x, pixel.y); return; }
                if (!tryMove(pixel, nx, pixel.y)) { safeDelete(nx, pixel.y); tryMove(pixel, nx, pixel.y); }
            }
        }
    };

    function summonB2Bomber(targetY) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? 24 : width - 25;
        var altitude = Math.round(targetY);
        var targetX = 20 + Math.floor(Math.random() * Math.max(1, width - 40));
        triggerCityAirRaid(targetX, 16000);
        return forcePut("b2_bomber_controller", startX, altitude, function (bomber) {
            bomber.age = 0; bomber.direction = direction; bomber.targetX = targetX;
            bomber.dropped = false; bomber.bombsDropped = 0;
        });
    }
    elements.b2_spirit_bomber = {
        color: ["#111416", "#32383b", "#657079"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a pixel-art B-2 Spirit from a random side and altitude. It chooses a random point and drops exactly one nuclear payload.",
        tick: function (pixel) { var targetY = pixel.y; safeDelete(pixel.x, pixel.y); summonB2Bomber(targetY); }
    };

    function makeAircraftArtElement(name, colors) {
        elements[name] = {
            color: colors, category: SPECIAL_CATEGORY, state: "gas", density: 0.001,
            hardness: 1, hidden: true, excludeRandom: true,
            tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 2) deletePixel(pixel.x, pixel.y); }
        };
    }

    function moveAircraftAcross(pixel, speed) {
        speed = speed || 1;
        for (var step = 0; step < speed; step++) {
            var nx = pixel.x + pixel.direction;
            if (!inBounds(nx, pixel.y)) { safeDelete(pixel.x, pixel.y); return false; }
            if (!tryMove(pixel, nx, pixel.y)) { safeDelete(nx, pixel.y); tryMove(pixel, nx, pixel.y); }
        }
        return true;
    }

    function fireDownwardProjectile(name, aircraft, offsetX, offsetY, horizontalSpeed) {
        return put(name, aircraft.x + (offsetX || 0) * aircraft.direction, aircraft.y + (offsetY || 3), function (round) {
            round.direction = aircraft.direction;
            round.horizontalSpeed = horizontalSpeed || 0;
        });
    }

    function tickAircraftProjectile(pixel, options) {
        pixel.age = (pixel.age || 0) + 1;
        if (pixel.horizontalSpeed && pixel.age % Math.max(1, Math.round(1 / Math.abs(pixel.horizontalSpeed))) === 0) {
            var sideX = pixel.x + (pixel.direction || 1) * (pixel.horizontalSpeed < 0 ? -1 : 1);
            if (inBounds(sideX, pixel.y) && empty(sideX, pixel.y)) tryMove(pixel, sideX, pixel.y);
        }
        if (fallWithoutFalseFuse(pixel, options.speed || 3)) {
            detonateBomb(pixel, {
                radius: options.radius, shockwave: options.shockwave,
                payload: options.payload || ["explosion", "fire", "smoke"], waveColor: options.waveColor || "#ffd79b"
            });
        } else doDefaults(pixel);
    }

    elements.a10_cannon_round = {
        color: ["#fff7bb", "#ffba31"], category: SPECIAL_CATEGORY, state: "solid", density: 7900,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 4, radius: 4, shockwave: 9, waveColor: "#fff1b7" }); }
    };
    elements.a10_rocket = {
        color: ["#4f575a", "#d8dde0", "#ff7a21"], category: SPECIAL_CATEGORY, state: "solid", density: 5100,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 3, radius: 18, shockwave: 28, waveColor: "#ffd2a0" }); }
    };
    makeAircraftArtElement("a10_warthog_pixel", ["#7b867c", "#aab2a9", "#4f5b52"]);

    function drawA10(controller) {
        var d = controller.direction || 1;
        var shape = [[-12,0],[-11,0],[-10,0],[-9,0],[-8,0],[-7,0],[-6,0],[-5,0],[-4,0],[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0],[10,0],[11,0],[12,0],[-9,-1],[-8,-1],[-7,-1],[-4,-1],[-3,-1],[-2,-1],[-1,-1],[0,-1],[1,-1],[2,-1],[3,-1],[4,-1],[5,-1],[6,-1],[-10,-2],[-9,-2],[-2,-2],[-1,-2],[0,-2],[1,-2],[2,-2],[3,-2],[-11,-3],[-10,-3],[-5,1],[-4,1],[-3,1],[-2,1],[-1,1],[0,1],[1,1],[2,1],[3,1],[4,1],[5,1],[-3,2],[-2,2],[2,2],[3,2]];
        for (var i = 0; i < shape.length; i++) {
            var sx = shape[i][0], sy = shape[i][1];
            put("a10_warthog_pixel", controller.x + sx * d, controller.y + sy, function (part) {
                part.color = sy === -2 && sx >= -2 && sx <= 3 ? "#69a9c5" : (sy === 2 ? "#353b37" : "#879188");
            });
        }
        put("a10_warthog_pixel", controller.x + 13 * d, controller.y, function (part) { part.color = "#d4d9d3"; });
    }

    elements.a10_warthog_controller = {
        color: "#7e8980", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawA10(pixel);
            if (pixel.age > 8 && pixel.age < 100 && pixel.age % 3 === 0) fireDownwardProjectile("a10_cannon_round", pixel, 9, 3, 0.5);
            if (pixel.age === 28 || pixel.age === 62) fireDownwardProjectile("a10_rocket", pixel, 1, 4, 0.25);
            moveAircraftAcross(pixel, 2);
        }
    };

    function summonA10(targetY) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? 15 : width - 16;
        triggerCityAirRaid(Math.floor(width / 2), 16000);
        return forcePut("a10_warthog_controller", startX, Math.round(targetY), function (jet) { jet.age = 0; jet.direction = direction; });
    }
    elements.a10_warthog = {
        color: ["#69756d", "#9ca69f", "#4d5951"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons an A-10 Thunderbolt II that crosses the selected altitude, strafes with its cannon, and fires two air-to-ground rockets.",
        tick: function (pixel) { var targetY = pixel.y; safeDelete(pixel.x, pixel.y); summonA10(targetY); }
    };

    function ac130CursorTarget(aircraft) {
        var targetX = typeof mousePos !== "undefined" && mousePos ? mousePos.x : aircraft.x;
        var targetY = typeof mousePos !== "undefined" && mousePos ? mousePos.y : Math.min(height - 1, aircraft.y + 80);
        return {
            x: Math.max(0, Math.min(width - 1, Math.round(targetX))),
            y: Math.max(0, Math.min(height - 1, Math.round(targetY)))
        };
    }

    function fireAC130AtCursor(name, aircraft, offsetX, speed) {
        var target = ac130CursorTarget(aircraft);
        return put(name, aircraft.x + offsetX * aircraft.direction, aircraft.y + 4, function (round) {
            var dx = target.x - round.x, dy = target.y - round.y;
            var distance = Math.sqrt(dx * dx + dy * dy) || 1;
            round.fx = round.x; round.fy = round.y;
            round.vx = dx / distance * speed; round.vy = dy / distance * speed;
            round.targetX = target.x; round.targetY = target.y;
        });
    }

    function tickAC130Round(pixel, radius, shockwave, speed) {
        pixel.age = (pixel.age || 0) + 1;
        pixel.fx = pixel.fx === undefined ? pixel.x : pixel.fx;
        pixel.fy = pixel.fy === undefined ? pixel.y : pixel.fy;
        for (var step = 0; step < Math.max(2, Math.ceil(speed)); step++) {
            pixel.fx += (pixel.vx || 0) / Math.max(2, Math.ceil(speed));
            pixel.fy += (pixel.vy || 1) / Math.max(2, Math.ceil(speed));
            var nx = Math.round(pixel.fx), ny = Math.round(pixel.fy);
            if (!inBounds(nx, ny)) { safeDelete(pixel.x, pixel.y); return; }
            var remaining = Math.sqrt(Math.pow((pixel.targetX === undefined ? nx : pixel.targetX) - nx, 2) + Math.pow((pixel.targetY === undefined ? ny : pixel.targetY) - ny, 2));
            var obstruction = pixelMap[nx] && pixelMap[nx][ny];
            if (obstruction && obstruction !== pixel) {
                var definition = elements[obstruction.element];
                if (definition && definition.state === "gas") safeDelete(nx, ny);
                else {
                    detonateBomb(pixel, { radius: radius, shockwave: shockwave, payload: ["explosion", "fire", "smoke"], waveColor: "#ffe0a4" });
                    return;
                }
            }
            if (remaining <= speed * 0.8) {
                if (nx !== pixel.x || ny !== pixel.y) { safeDelete(nx, ny); if (empty(nx, ny)) tryMove(pixel, nx, ny); }
                detonateBomb(pixel, { radius: radius, shockwave: shockwave, payload: ["explosion", "fire", "smoke"], waveColor: "#ffe0a4" });
                return;
            }
            if ((nx !== pixel.x || ny !== pixel.y) && empty(nx, ny)) tryMove(pixel, nx, ny);
        }
        if (pixel.age > 180) safeDelete(pixel.x, pixel.y);
    }

    elements.ac130_25mm_round = {
        color: ["#fff4a0", "#ff9d20"], category: SPECIAL_CATEGORY, state: "solid", density: 7900,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAC130Round(pixel, 6, 12, 5); }
    };
    elements.ac130_105mm_shell = {
        color: ["#353c3f", "#747e82"], category: SPECIAL_CATEGORY, state: "solid", density: 7600,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAC130Round(pixel, 27, 39, 3.5); }
    };
    makeAircraftArtElement("ac130_gunship_pixel", ["#4c5558", "#899397", "#c2c9cb"]);

    function drawAC130(controller) {
        var d = controller.direction || 1;
        for (var x = -18; x <= 18; x++) {
            put("ac130_gunship_pixel", controller.x + x * d, controller.y, function (part) { part.color = x > 13 ? "#c5cdcf" : "#697377"; });
            if (x > -12 && x < 13) put("ac130_gunship_pixel", controller.x + x * d, controller.y + 1, function (part) { part.color = "#586267"; });
        }
        for (var wing = -8; wing <= 8; wing++) put("ac130_gunship_pixel", controller.x + wing * d, controller.y - 1 - Math.floor((8 - Math.abs(wing)) / 5), function (part) { part.color = "#7f898c"; });
        for (var tail = -18; tail <= -13; tail++) put("ac130_gunship_pixel", controller.x + tail * d, controller.y - 1 - Math.floor((-tail - 13) / 2), function (part) { part.color = "#5b6568"; });
        for (var engine = -7; engine <= 7; engine += 7) {
            put("ac130_gunship_pixel", controller.x + engine * d, controller.y + 2, function (part) { part.color = "#252b2e"; });
            var spin = controller.age % 2 ? 2 : 1;
            put("ac130_gunship_pixel", controller.x + engine * d, controller.y - spin, function (part) { part.color = "#d7dddf"; });
            put("ac130_gunship_pixel", controller.x + engine * d, controller.y + spin + 1, function (part) { part.color = "#d7dddf"; });
        }
        for (var windowX = 9; windowX <= 14; windowX += 2) put("ac130_gunship_pixel", controller.x + windowX * d, controller.y - 1, function (part) { part.color = "#66a5bf"; });
    }

    elements.ac130_gunship_controller = {
        color: "#5f696c", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawAC130(pixel);
            if (pixel.age > 5 && pixel.age % 4 === 0) fireAC130AtCursor("ac130_25mm_round", pixel, -2, 5);
            var rightClicking = typeof mouseIsDown !== "undefined" && mouseIsDown && typeof mouseType !== "undefined" && mouseType === "right";
            if (rightClicking && (pixel.lastHeavyShot === undefined || pixel.age - pixel.lastHeavyShot >= 16)) {
                if (fireAC130AtCursor("ac130_105mm_shell", pixel, -7, 3.5)) pixel.lastHeavyShot = pixel.age;
            }
            if (pixel.age % 2 === 0) moveAircraftAcross(pixel, 1);
        }
    };

    function summonAC130(targetY) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? 22 : width - 23;
        triggerCityAirRaid(Math.floor(width / 2), 22000);
        return forcePut("ac130_gunship_controller", startX, Math.round(targetY), function (plane) { plane.age = 0; plane.direction = direction; plane.lastHeavyShot = -999; });
    }
    elements.ac130_gunship = {
        color: ["#465055", "#7d888c", "#b1b9bc"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a slow AC-130 gunship. Its 25 mm cannon tracks the cursor automatically; hold right-click to fire a heavy 105 mm shell exactly toward the cursor.",
        tick: function (pixel) { var targetY = pixel.y; safeDelete(pixel.x, pixel.y); summonAC130(targetY); }
    };

    elements.apache_chain_round = {
        color: ["#fff7ad", "#ff9f22"], category: SPECIAL_CATEGORY, state: "solid", density: 7800,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 3, radius: 3, shockwave: 8, waveColor: "#ffe7ae" }); }
    };
    elements.apache_hellfire = {
        color: ["#282f2b", "#6e796f", "#ff6f18"], category: SPECIAL_CATEGORY, state: "solid", density: 5600,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 3, radius: 22, shockwave: 34, waveColor: "#ffc98f" }); }
    };
    makeAircraftArtElement("apache_helicopter_pixel", ["#313b32", "#5f6c5e", "#8c978a"]);

    function drawApache(controller) {
        var d = controller.direction || 1;
        for (var rotor = -14; rotor <= 14; rotor++) if (rotor % 2 === controller.age % 2) put("apache_helicopter_pixel", controller.x + rotor, controller.y - 5, function (part) { part.color = "#aeb6b0"; });
        put("apache_helicopter_pixel", controller.x, controller.y - 4, function (part) { part.color = "#48534a"; });
        for (var x = -7; x <= 7; x++) {
            put("apache_helicopter_pixel", controller.x + x * d, controller.y - (Math.abs(x) > 5 ? 1 : 0), function (part) { part.color = x > 3 ? "#54665a" : "#333e35"; });
            if (x >= -4 && x <= 4) put("apache_helicopter_pixel", controller.x + x * d, controller.y + 1, function (part) { part.color = "#465248"; });
        }
        for (var tail = -13; tail <= -7; tail++) put("apache_helicopter_pixel", controller.x + tail * d, controller.y - 1, function (part) { part.color = "#3c473e"; });
        put("apache_helicopter_pixel", controller.x + 4 * d, controller.y - 1, function (part) { part.color = "#5e9daf"; });
        put("apache_helicopter_pixel", controller.x - 13 * d, controller.y - 3, function (part) { part.color = "#aeb6b0"; });
        put("apache_helicopter_pixel", controller.x - 13 * d, controller.y + 1, function (part) { part.color = "#aeb6b0"; });
        for (var skid = -4; skid <= 4; skid++) if (Math.abs(skid) > 1) put("apache_helicopter_pixel", controller.x + skid * d, controller.y + 3, function (part) { part.color = "#242b26"; });
    }

    elements.apache_helicopter_controller = {
        color: "#3f4a40", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawApache(pixel);
            var hovering = pixel.age >= 24 && pixel.age <= 145;
            if (hovering && pixel.age % 5 === 0) fireDownwardProjectile("apache_chain_round", pixel, 5, 3, 0.34);
            if (hovering && (pixel.age === 45 || pixel.age === 82 || pixel.age === 119)) fireDownwardProjectile("apache_hellfire", pixel, 2, 4, 0.25);
            if (!hovering || pixel.age % 6 === 0) moveAircraftAcross(pixel, 1);
        }
    };

    function summonApache(targetY) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? 16 : width - 17;
        triggerCityAirRaid(Math.floor(width / 2), 22000);
        return forcePut("apache_helicopter_controller", startX, Math.round(targetY), function (helicopter) { helicopter.age = 0; helicopter.direction = direction; });
    }
    elements.ah64_apache = {
        color: ["#303a31", "#596759", "#8a9588"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons an AH-64 Apache that flies to the selected altitude, hovers under its animated rotor, and attacks with a chain gun and three Hellfire missiles.",
        tick: function (pixel) { var targetY = pixel.y; safeDelete(pixel.x, pixel.y); summonApache(targetY); }
    };

    function summonSimpleAircraft(controllerName, targetY, edgePadding, raidTime) {
        var direction = Math.random() < 0.5 ? 1 : -1;
        var startX = direction > 0 ? edgePadding : width - edgePadding - 1;
        triggerCityAirRaid(Math.floor(width / 2), raidTime || 18000);
        return forcePut(controllerName, startX, Math.round(targetY), function (aircraft) { aircraft.age = 0; aircraft.direction = direction; });
    }

    elements.f22_precision_bomb = {
        color: ["#353b3e", "#9ca6aa"], category: SPECIAL_CATEGORY, state: "solid", density: 5900,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 3, radius: 20, shockwave: 31, waveColor: "#d8ecf4" }); }
    };
    makeAircraftArtElement("f22_raptor_pixel", ["#69747b", "#a8b2b8", "#3d464b"]);
    function drawF22(controller) {
        var d = controller.direction || 1;
        var rows = [{y:-2,a:1,b:7},{y:-1,a:-7,b:11},{y:0,a:-13,b:14},{y:1,a:-9,b:9},{y:2,a:-4,b:4}];
        for (var r = 0; r < rows.length; r++) for (var x = rows[r].a; x <= rows[r].b; x++) put("f22_raptor_pixel", controller.x + x * d, controller.y + rows[r].y, function (part) {
            part.color = rows[r].y === -2 ? "#5e9bb4" : ((x + rows[r].y) % 5 ? "#77838a" : "#444e53");
        });
        put("f22_raptor_pixel", controller.x - 11 * d, controller.y, function (part) { part.color = "#ff8a27"; });
    }
    elements.f22_raptor_controller = {
        color: "#6d787f", category: SPECIAL_CATEGORY, state: "gas", density: 999999, hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawF22(pixel);
            if (pixel.age === 16 || pixel.age === 29 || pixel.age === 42 || pixel.age === 55) fireDownwardProjectile("f22_precision_bomb", pixel, -2, 4, 0.35);
            moveAircraftAcross(pixel, 3);
        }
    };
    elements.f22_raptor = {
        color: ["#59656c", "#8f9aa0", "#3c4549"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a fast stealthy F-22 Raptor that releases four compact precision glide bombs during a supersonic pass.",
        tick: function (pixel) { var y = pixel.y; safeDelete(pixel.x, pixel.y); summonSimpleAircraft("f22_raptor_controller", y, 16, 15000); }
    };

    elements.f35_guided_bomb = {
        color: ["#252b2f", "#656f74", "#d8dcde"], category: SPECIAL_CATEGORY, state: "solid", density: 6100,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 2, radius: 34, shockwave: 48, waveColor: "#d7ebf4" }); }
    };
    makeAircraftArtElement("f35_lightning_pixel", ["#4c575e", "#818d94", "#aeb8bd"]);
    function drawF35(controller) {
        var d = controller.direction || 1;
        var shape = [[-11,0],[-10,0],[-9,0],[-8,0],[-7,0],[-6,0],[-5,0],[-4,0],[-3,0],[-2,0],[-1,0],[0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0],[10,0],[11,0],[-5,-1],[-4,-1],[-3,-1],[-2,-1],[-1,-1],[0,-1],[1,-1],[2,-1],[3,-1],[4,-1],[5,-1],[6,-1],[-2,-2],[-1,-2],[0,-2],[1,-2],[2,-2],[3,-2],[-5,1],[-4,1],[-3,1],[-2,1],[-1,1],[0,1],[1,1],[2,1],[3,1],[4,1],[5,1]];
        for (var i = 0; i < shape.length; i++) {
            var x = shape[i][0], y = shape[i][1];
            put("f35_lightning_pixel", controller.x + x * d, controller.y + y, function (part) { part.color = y === -2 ? "#5792ad" : "#69767d"; });
        }
        if (controller.age >= 22 && controller.age <= 105) put("f35_lightning_pixel", controller.x - 2 * d, controller.y + 3, function (part) { part.color = controller.age % 2 ? "#a8e9ff" : "#ffb039"; });
    }
    elements.f35_lightning_controller = {
        color: "#657178", category: SPECIAL_CATEGORY, state: "gas", density: 999999, hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawF35(pixel);
            var hovering = pixel.age >= 22 && pixel.age <= 105;
            if (pixel.age === 67) fireDownwardProjectile("f35_guided_bomb", pixel, 1, 4, 0.1);
            if (!hovering || pixel.age % 7 === 0) moveAircraftAcross(pixel, 1);
        }
    };
    elements.f35b_lightning = {
        color: ["#455158", "#77838a", "#a8b1b6"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons an F-35B that brakes into a visible hover using its lift fan, drops one guided bomb, then accelerates away.",
        tick: function (pixel) { var y = pixel.y; safeDelete(pixel.x, pixel.y); summonSimpleAircraft("f35_lightning_controller", y, 14, 19000); }
    };

    elements.su57_missile = {
        color: ["#d7dcdf", "#525c62", "#ff7a1c"], category: SPECIAL_CATEGORY, state: "solid", density: 5400,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 4, radius: 17, shockwave: 27, waveColor: "#e1f2ff" }); }
    };
    makeAircraftArtElement("su57_felon_pixel", ["#55717a", "#7898a1", "#334b52"]);
    function drawSu57(controller) {
        var d = controller.direction || 1;
        var rows = [{y:-2,a:0,b:7},{y:-1,a:-8,b:11},{y:0,a:-14,b:14},{y:1,a:-10,b:9},{y:2,a:-5,b:4}];
        for (var r = 0; r < rows.length; r++) for (var x = rows[r].a; x <= rows[r].b; x++) put("su57_felon_pixel", controller.x + x * d, controller.y + rows[r].y, function (part) {
            part.color = rows[r].y === -2 && x > 1 ? "#68a4ba" : ((x + r) % 4 ? "#607c84" : "#38545c");
        });
        put("su57_felon_pixel", controller.x - 12 * d, controller.y, function (part) { part.color = "#68cfff"; });
    }
    elements.su57_felon_controller = {
        color: "#53727b", category: SPECIAL_CATEGORY, state: "gas", density: 999999, hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawSu57(pixel);
            if (pixel.age === 18) plantShockwave(pixel.x, pixel.y + 6, 34, "#bfeaff");
            if (pixel.age === 27 || pixel.age === 51) fireDownwardProjectile("su57_missile", pixel, 0, 4, 0.4);
            moveAircraftAcross(pixel, 3);
        }
    };
    elements.su57_felon = {
        color: ["#45636c", "#71919a", "#2d4850"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a Su-57 Felon that creates a visible sonic pressure ring and fires two high-speed strike missiles.",
        tick: function (pixel) { var y = pixel.y; safeDelete(pixel.x, pixel.y); summonSimpleAircraft("su57_felon_controller", y, 16, 15000); }
    };

    elements.tu160_cluster_canister = {
        color: ["#efefef", "#626b70"], category: SPECIAL_CATEGORY, state: "solid", density: 6000,
        hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            if (pixel.age === 14 && !impactSurfaceBelow(pixel)) {
                var x = pixel.x, y = pixel.y; safeDelete(x, y);
                for (var spread = -4; spread <= 4; spread += 2) put("carpet_bomb", x + spread, y, function (bomb) { bomb.direction = spread < 0 ? -1 : 1; });
                return;
            }
            tickAircraftProjectile(pixel, { speed: 2, radius: 16, shockwave: 25, waveColor: "#ffe0a8" });
        }
    };
    makeAircraftArtElement("tu160_blackjack_pixel", ["#d9dde0", "#9ca5aa", "#596269"]);
    function drawTu160(controller) {
        var d = controller.direction || 1;
        for (var x = -21; x <= 21; x++) {
            put("tu160_blackjack_pixel", controller.x + x * d, controller.y, function (part) { part.color = x > 14 ? "#f3f3f3" : "#c7cccf"; });
            if (x > -16 && x < 15) put("tu160_blackjack_pixel", controller.x + x * d, controller.y + 1, function (part) { part.color = "#aeb5b8"; });
        }
        for (var wing = -13; wing <= 10; wing++) if (Math.abs(wing) < 5 || wing % 2 === 0) put("tu160_blackjack_pixel", controller.x + wing * d, controller.y - 1 - Math.floor((12 - Math.abs(wing)) / 6), function (part) { part.color = "#bfc5c8"; });
        for (var tail = -21; tail <= -16; tail++) put("tu160_blackjack_pixel", controller.x + tail * d, controller.y - Math.floor((-tail - 15) / 2), function (part) { part.color = "#9fa7ab"; });
        for (var windowX = 15; windowX <= 19; windowX++) put("tu160_blackjack_pixel", controller.x + windowX * d, controller.y - 1, function (part) { part.color = "#5a92aa"; });
    }
    elements.tu160_blackjack_controller = {
        color: "#c5cace", category: SPECIAL_CATEGORY, state: "gas", density: 999999, hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawTu160(pixel);
            if (pixel.age === 24 || pixel.age === 48 || pixel.age === 72) fireDownwardProjectile("tu160_cluster_canister", pixel, -3, 4, 0.15);
            moveAircraftAcross(pixel, 2);
        }
    };
    elements.tu160_blackjack = {
        color: ["#e5e6e7", "#aeb5b9", "#606970"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a large Tu-160 Blackjack that releases three canisters, each separating into a five-bomb cluster before impact.",
        tick: function (pixel) { var y = pixel.y; safeDelete(pixel.x, pixel.y); summonSimpleAircraft("tu160_blackjack_controller", y, 24, 20000); }
    };

    elements.reaper_hellfire = {
        color: ["#30363a", "#aab1b5", "#ff8424"], category: SPECIAL_CATEGORY, state: "solid", density: 5300,
        hidden: true, excludeRandom: true,
        tick: function (pixel) { tickAircraftProjectile(pixel, { speed: 3, radius: 19, shockwave: 29, waveColor: "#ffd19b" }); }
    };
    makeAircraftArtElement("mq9_reaper_pixel", ["#bfc4c6", "#7e888d", "#424a4e"]);
    function drawReaper(controller) {
        var d = controller.direction || 1;
        for (var x = -12; x <= 12; x++) put("mq9_reaper_pixel", controller.x + x * d, controller.y, function (part) { part.color = x > 8 ? "#e2e4e5" : "#adb4b7"; });
        for (var wing = -8; wing <= 8; wing++) put("mq9_reaper_pixel", controller.x + wing * d, controller.y + (Math.abs(wing) > 5 ? 1 : -1), function (part) { part.color = "#929ca0"; });
        put("mq9_reaper_pixel", controller.x + 8 * d, controller.y - 1, function (part) { part.color = "#416f83"; });
        put("mq9_reaper_pixel", controller.x - 12 * d, controller.y - 2, function (part) { part.color = "#676f73"; });
        put("mq9_reaper_pixel", controller.x - 12 * d, controller.y + 2, function (part) { part.color = "#676f73"; });
    }
    elements.mq9_reaper_controller = {
        color: "#aeb5b8", category: SPECIAL_CATEGORY, state: "gas", density: 999999, hidden: true, excludeRandom: true, hardness: 1,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1; drawReaper(pixel);
            if (pixel.age === 35 || pixel.age === 70 || pixel.age === 105 || pixel.age === 140) fireDownwardProjectile("reaper_hellfire", pixel, 1, 3, 0.15);
            if (pixel.age % 2 === 0) moveAircraftAcross(pixel, 1);
        }
    };
    elements.mq9_reaper = {
        color: ["#d3d6d8", "#929a9e", "#545c60"], category: AIRCRAFT_CATEGORY, state: "solid", density: 1000,
        hardness: 1, excludeRandom: true, cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Summons a slow MQ-9 Reaper drone with a long surveillance pass and four spaced Hellfire missile strikes.",
        tick: function (pixel) { var y = pixel.y; safeDelete(pixel.x, pixel.y); summonSimpleAircraft("mq9_reaper_controller", y, 14, 23000); }
    };

    function isAircraftControllerName(name) {
        return name === "fighter_jet_controller" || name === "b2_bomber_controller" || name === "ac130_gunship_controller";
    }
    function isAircraftVisualName(name) {
        return name === "fighter_jet_pixel" || name === "b2_bomber_pixel" || name === "ac130_gunship_pixel";
    }

    // Retired aircraft and their private payload/art elements are deleted before
    // Sandboxels builds its element menu, so they cannot appear even with Unhide on.
    var RETIRED_AIRCRAFT_ELEMENTS = [
        "a10_cannon_round", "a10_rocket", "a10_warthog_pixel", "a10_warthog_controller", "a10_warthog",
        "apache_chain_round", "apache_hellfire", "apache_helicopter_pixel", "apache_helicopter_controller", "ah64_apache",
        "f22_precision_bomb", "f22_raptor_pixel", "f22_raptor_controller", "f22_raptor",
        "f35_guided_bomb", "f35_lightning_pixel", "f35_lightning_controller", "f35b_lightning",
        "su57_missile", "su57_felon_pixel", "su57_felon_controller", "su57_felon",
        "tu160_cluster_canister", "tu160_blackjack_pixel", "tu160_blackjack_controller", "tu160_blackjack",
        "reaper_hellfire", "mq9_reaper_pixel", "mq9_reaper_controller", "mq9_reaper"
    ];
    for (var retiredIndex = 0; retiredIndex < RETIRED_AIRCRAFT_ELEMENTS.length; retiredIndex++) delete elements[RETIRED_AIRCRAFT_ELEMENTS[retiredIndex]];

    elements.orbital_beam = {
        color: ["#ffffff", "#c8ffff", "#63ccff", "#ffd66b"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.0001, temp: 12000, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 3) deletePixel(pixel.x, pixel.y); }
    };
    elements.orbital_vapor = {
        color: ["#ffffff", "#d7ffff", "#77dfff", "#ffd64f", "#ff6b18"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.0001, temp: 18000, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            if (pixel.life > 10) pixel.color = pixel.life % 2 ? "#ff6b18" : "#6d2412";
            if (pixel.life > 18 + Math.random() * 8) deletePixel(pixel.x, pixel.y);
        }
    };

    elements.orbital_strike_controller = {
        color: "#d8ffff", category: SPECIAL_CATEGORY, state: "gas", density: 999999,
        hardness: 1, insulate: true, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            var ox = pixel.originX === undefined ? pixel.x : pixel.originX;
            var oy = pixel.originY === undefined ? pixel.y : pixel.originY;
            for (var y = 1; y < oy; y++) {
                var widthAtY = pixel.age < 14 ? 0 : (pixel.age < 19 ? 1 : 3);
                for (var bx = -widthAtY; bx <= widthAtY; bx++) if ((y + bx + pixel.age) % 2 === 0 || bx === 0) put("orbital_beam", ox + bx, y);
            }
            var ring = Math.max(3, 17 - Math.min(14, pixel.age));
            circleSamples(ox, oy, ring, ring * 4, function (x, y) { put("orbital_beam", x, y); });
            if (pixel.age === 20) {
                explodeAt(ox, oy, BOMB_TUNING.orbitalStrike.coreBlast, validPayload(["plasma", "plasma", "light"], "explosion"));
                explodeAt(ox - 5, oy - 2, 13, validPayload(["plasma", "fire", "plasma"], "explosion"));
                explodeAt(ox + 5, oy - 2, BOMB_TUNING.orbitalStrike.plasmaBlast, validPayload(["plasma", "plasma", "fire"], "explosion"));
                diskSamples(ox, oy - 3, 25, 180, function (sparkX, sparkY) {
                    put("orbital_vapor", sparkX, sparkY, function (vapor) { vapor.color = Math.random() < 0.5 ? "#d7ffff" : (Math.random() < 0.5 ? "#ffffff" : "#ff8d28"); });
                });
                plantShockwave(ox, oy, BOMB_TUNING.orbitalStrike.shockwave, "#d7f7ff");
                safeDelete(pixel.x, pixel.y);
            }
        }
    };
    elements.orbital_strike_beacon = {
        color: ["#e8ffff", "#56cfff", "#f4b942"], category: CATEGORY, state: "solid", density: 5400,
        hardness: 0.96, burn: 0, conduct: 1, excludeRandom: true,
        cooldown: typeof defaultCooldown !== "undefined" ? defaultCooldown : 1,
        desc: "Orbital Strike Beacon: locks onto solid or liquid impact for five seconds, then calls down a beam ending in three compact blue-white plasma explosions.",
        tick: function (pixel) {
            if (!fallWithoutFalseFuse(pixel, 1)) { doDefaults(pixel); return; }
            if (!pixel.armedAt) {
                pixel.armedAt = Date.now();
                triggerCityAirRaid(pixel.x, 12000);
            }
            pixel.chargeAge = (pixel.chargeAge || 0) + 1;
            if (pixel.chargeAge % 3 === 0) put("orbital_beam", pixel.x, pixel.y - 1 - (pixel.chargeAge % 7));
            if (Date.now() - pixel.armedAt < 5000) return;
            var x = pixel.x, y = pixel.y;
            safeDelete(x, y);
            forcePut("orbital_strike_controller", x, Math.max(1, y - 3), function (controller) {
                controller.age = 0; controller.originX = x; controller.originY = y;
            });
        }
    };

    function cityMaterial(names) {
        if (!Array.isArray(names)) names = [names];
        for (var i = 0; i < names.length; i++) if (elements[names[i]]) return names[i];
        return elements.wood ? "wood" : (elements.wall ? "wall" : null);
    }

    function cityPut(names, x, y, color) {
        var name = cityMaterial(names);
        if (!name) return null;
        return put(name, x, y, function (pixel) { if (color) pixel.color = color; });
    }

    function cityWalkable(x, y) {
        return empty(x, y) && inBounds(x, y + 1) && elementStateAt(x, y + 1) === "solid";
    }

    elements.city_siren_flash = {
        color: ["#ff2c22", "#ffd447", "#ffffff"], category: SPECIAL_CATEGORY, state: "gas", density: 0.0001,
        hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            if (pixel.life > 4) deletePixel(pixel.x, pixel.y);
        }
    };

    elements.city_air_raid_siren = {
        color: ["#4e5960", "#78858b", "#b92020"], category: SPECIAL_CATEGORY, state: "solid", density: 7800,
        hardness: 0.8, hidden: true, excludeRandom: true, behavior: behaviors.WALL,
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            if (!cityAirRaidActive()) { pixel.color = pixel.age % 24 < 12 ? "#58646a" : "#69767c"; return; }
            pixel.color = pixel.age % 4 < 2 ? "#ff251c" : "#fff1a6";
            if (pixel.age % 3 === 0) {
                put("city_siren_flash", pixel.x - 1, pixel.y - 1);
                put("city_siren_flash", pixel.x + 1, pixel.y - 1);
            }
        }
    };

    elements.city_shelter_door = {
        color: ["#253239", "#40535b", "#e5c43d"], category: SPECIAL_CATEGORY, state: "solid", density: 7800,
        hardness: 0.9, hidden: true, excludeRandom: true, behavior: behaviors.WALL
    };

    elements.city_anti_air_gun_pixel = {
        color: ["#68747a", "#303a3f", "#b9c3c7"], category: SPECIAL_CATEGORY, state: "gas", density: 0.001,
        hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 2) deletePixel(pixel.x, pixel.y); }
    };

    elements.city_anti_air_round = {
        color: ["#fffbd0", "#ffd13b", "#ff7b1c"], category: SPECIAL_CATEGORY, state: "gas", density: 0.001,
        temp: 900, hidden: true, excludeRandom: true,
        tick: function (pixel) {
            pixel.life = (pixel.life || 0) + 1;
            pixel.fx = pixel.fx === undefined ? pixel.x : pixel.fx;
            pixel.fy = pixel.fy === undefined ? pixel.y : pixel.fy;
            for (var step = 0; step < 3; step++) {
                pixel.fx += (pixel.vx || 0) / 3;
                pixel.fy += (pixel.vy || -2) / 3;
                var nx = Math.round(pixel.fx), ny = Math.round(pixel.fy);
                for (var sx = -1; sx <= 1; sx++) for (var sy = -1; sy <= 1; sy++) {
                    var aircraft = pixelMap[nx + sx] && pixelMap[nx + sx][ny + sy];
                    if (aircraft && isAircraftControllerName(aircraft.element)) {
                        var hitX = aircraft.x, hitY = aircraft.y;
                        safeDelete(hitX, hitY); safeDelete(pixel.x, pixel.y);
                        if (typeof explodeAt === "function") explodeAt(hitX, hitY, 5, validPayload(["fire", "smoke", "explosion"], "fire"));
                        return;
                    }
                }
                if (!inBounds(nx, ny)) { safeDelete(pixel.x, pixel.y); return; }
                if (nx === pixel.x && ny === pixel.y) continue;
                var obstruction = pixelMap[nx] && pixelMap[nx][ny];
                if (obstruction && (isAircraftVisualName(obstruction.element) || obstruction.element === "city_anti_air_gun_pixel")) safeDelete(nx, ny);
                else if (obstruction) { safeDelete(pixel.x, pixel.y); return; }
                if (empty(nx, ny)) tryMove(pixel, nx, ny);
            }
            if (pixel.life > 90) safeDelete(pixel.x, pixel.y);
        }
    };

    function nearestAircraft(pixel) {
        if (typeof currentPixels === "undefined") return null;
        var nearest = null, nearestDistance = 170;
        for (var i = 0; i < currentPixels.length; i++) {
            var candidate = currentPixels[i];
            if (!candidate || !pixelMap[candidate.x] || pixelMap[candidate.x][candidate.y] !== candidate) continue;
            if (!isAircraftControllerName(candidate.element)) continue;
            var dx = candidate.x - pixel.x, dy = candidate.y - pixel.y;
            var distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < nearestDistance) { nearest = candidate; nearestDistance = distance; }
        }
        return nearest;
    }

    function drawAntiAirGun(pixel, aimX, aimY) {
        var length = Math.sqrt(aimX * aimX + aimY * aimY) || 1;
        var ux = aimX / length, uy = aimY / length;
        for (var segment = 1; segment <= 4; segment++) put("city_anti_air_gun_pixel", pixel.x + Math.round(ux * segment), pixel.y + Math.round(uy * segment), function (part) { part.color = segment === 4 ? "#b9c3c7" : "#465158"; });
    }

    elements.city_anti_air_turret = {
        color: ["#536067", "#2f393e", "#7c898f"], category: SPECIAL_CATEGORY, state: "solid", density: 8200,
        hardness: 0.88, hidden: true, excludeRandom: true, behavior: behaviors.WALL,
        properties: { age: 0, aimX: 0, aimY: -1 },
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            var target = cityAirRaidActive() ? nearestAircraft(pixel) : null;
            if (target) { pixel.aimX = target.x - pixel.x; pixel.aimY = target.y - pixel.y; }
            if (target && pixel.age % 7 === 0) {
                var distance = Math.sqrt(pixel.aimX * pixel.aimX + pixel.aimY * pixel.aimY) || 1;
                var muzzlePixel = pixelMap[pixel.x] && pixelMap[pixel.x][pixel.y - 2];
                if (muzzlePixel && muzzlePixel.element === "city_anti_air_gun_pixel") safeDelete(pixel.x, pixel.y - 2);
                put("city_anti_air_round", pixel.x, pixel.y - 2, function (round) {
                    round.fx = round.x; round.fy = round.y;
                    round.vx = pixel.aimX / distance * 3.2;
                    round.vy = pixel.aimY / distance * 3.2;
                });
            }
            drawAntiAirGun(pixel, pixel.aimX || 0, pixel.aimY || -1);
        }
    };

    function nearbyHumanDangerDirection(pixel) {
        var dangerous = { explosion: true, fire: true, plasma: true, radiation: true, fallout: true, magma: true, acid: true, black_hole_core: true, black_hole_void: true, orbital_beam: true, orbital_vapor: true };
        var closestDistance = 999;
        var fleeDirection = 0;
        for (var dx = -8; dx <= 8; dx++) for (var dy = -5; dy <= 5; dy++) {
            var target = pixelMap[pixel.x + dx] && pixelMap[pixel.x + dx][pixel.y + dy];
            if (!target || !dangerous[target.element]) continue;
            var distance = Math.abs(dx) + Math.abs(dy);
            if (distance < closestDistance) {
                closestDistance = distance;
                fleeDirection = dx >= 0 ? -1 : 1;
            }
        }
        return fleeDirection;
    }

    function humanNearShelter(pixel) {
        for (var sx = -3; sx <= 3; sx++) for (var sy = -2; sy <= 2; sy++) {
            var shelter = pixelMap[pixel.x + sx] && pixelMap[pixel.x + sx][pixel.y + sy];
            if (shelter && shelter.element === "city_shelter_door") return true;
        }
        return false;
    }

    function moveBuiltInHuman(body, direction) {
        direction = direction < 0 ? -1 : 1;
        var targetX = body.x + direction;
        if (!cityWalkable(targetX, body.y)) return false;
        var head = pixelMap[body.x] && pixelMap[body.x][body.y - 1];
        if (head && head.element === "head") {
            if (!empty(targetX, body.y - 1)) return false;
            if (!tryMove(head, targetX, body.y - 1)) return false;
        }
        return tryMove(body, targetX, body.y);
    }

    function installBuiltInHumanAI() {
        if (!elements.body || elements.body.highTechCityAI) return;
        var originalBodyTick = elements.body.tick;
        elements.body.tick = function (pixel) {
            if (originalBodyTick) originalBodyTick(pixel);
            if (!pixel || !pixelMap[pixel.x] || pixelMap[pixel.x][pixel.y] !== pixel || pixel.element !== "body") return;
            pixel.cityAiAge = (pixel.cityAiAge || 0) + 1;
            var raid = cityAirRaidActive();
            var dangerDirection = nearbyHumanDangerDirection(pixel);
            pixel.panic = raid || dangerDirection !== 0;
            if (raid && humanNearShelter(pixel)) {
                var head = pixelMap[pixel.x] && pixelMap[pixel.x][pixel.y - 1];
                if (head && head.element === "head") deletePixel(head.x, head.y);
                deletePixel(pixel.x, pixel.y);
                return;
            }
            if (dangerDirection) pixel.cityDirection = dangerDirection;
            else if (raid) pixel.cityDirection = pixel.x < cityRaidTargetX ? -1 : 1;
            else if (!pixel.cityDirection || pixel.cityAiAge % 53 === 0) pixel.cityDirection = Math.random() < 0.5 ? -1 : 1;
            var moveEvery = pixel.panic ? 2 : 14;
            if (pixel.cityAiAge % moveEvery !== 0) return;
            if (!moveBuiltInHuman(pixel, pixel.cityDirection) && !pixel.panic) pixel.cityDirection *= -1;
        };
        elements.body.highTechCityAI = true;
    }

    elements.city_floor = {
        color: ["#aeb4b6", "#929a9d", "#c2c6c7"], category: SPECIAL_CATEGORY, state: "solid", density: 2450,
        hardness: 0.62, hidden: true, excludeRandom: true, behavior: behaviors.WALL,
        properties: { unsupportedAge: 0 },
        tick: function (pixel) {
            var supported = elementStateAt(pixel.x, pixel.y + 1) === "solid" ||
                elementStateAt(pixel.x - 1, pixel.y + 1) === "solid" || elementStateAt(pixel.x + 1, pixel.y + 1) === "solid";
            pixel.unsupportedAge = supported ? 0 : (pixel.unsupportedAge || 0) + 1;
            if (pixel.unsupportedAge > 7) {
                var debris = cityMaterial(["rubble", "gravel", "brick", "rock"]);
                changePixel(pixel, debris);
            }
        }
    };

    elements.city_subway_train_pixel = {
        color: ["#dbe2e5", "#2a78a7", "#79c9e8", "#22292d"], category: SPECIAL_CATEGORY, state: "gas",
        density: 0.001, hardness: 1, hidden: true, excludeRandom: true,
        tick: function (pixel) { pixel.life = (pixel.life || 0) + 1; if (pixel.life > 2) deletePixel(pixel.x, pixel.y); }
    };

    function drawCitySubwayTrain(controller) {
        var direction = controller.direction || 1;
        for (var dx = -9; dx <= 9; dx++) {
            var taper = Math.abs(dx) > 7;
            if (!taper) put("city_subway_train_pixel", controller.x + dx * direction, controller.y - 1, function (part) { part.color = "#aeb8bd"; });
            put("city_subway_train_pixel", controller.x + dx * direction, controller.y, function (part) {
                part.color = Math.abs(dx) < 8 && dx % 4 !== 0 ? "#70c5e5" : "#d9e0e3";
            });
            if (!taper) put("city_subway_train_pixel", controller.x + dx * direction, controller.y + 1, function (part) {
                part.color = dx % 5 === 0 ? "#20282c" : "#236f9d";
            });
        }
        put("city_subway_train_pixel", controller.x + 10 * direction, controller.y, function (part) { part.color = "#fff2a0"; });
        put("city_subway_train_pixel", controller.x - 10 * direction, controller.y, function (part) { part.color = "#e6332d"; });
    }

    elements.city_subway_train = {
        color: ["#d5dadd", "#2475a8", "#f0c22d"], category: SPECIAL_CATEGORY, state: "solid", density: 4000,
        hidden: true, excludeRandom: true, properties: { age: 0, direction: 1, deepMetro: true },
        tick: function (pixel) {
            pixel.age = (pixel.age || 0) + 1;
            drawCitySubwayTrain(pixel);
            if (pixel.age % 4 !== 0) return;
            var nx = pixel.x + (pixel.direction || 1);
            var obstruction = pixelMap[nx] && pixelMap[nx][pixel.y];
            if (obstruction && obstruction.element === "city_subway_train_pixel") safeDelete(nx, pixel.y);
            if (empty(nx, pixel.y)) tryMove(pixel, nx, pixel.y);
            else pixel.direction *= -1;
        }
    };

    function cityRandomInt(min, max) {
        min = Math.ceil(min); max = Math.floor(max);
        return min + Math.floor(Math.random() * Math.max(1, max - min + 1));
    }

    function cityPaintGround(streetY) {
        for (var x = 0; x < width; x++) {
            for (var y = streetY; y < height; y++) {
                var groundMaterial = y === streetY ? cityMaterial(["asphalt", "concrete", "stone"]) :
                    y < streetY + 4 ? cityMaterial(["concrete", "stone"]) :
                    y < streetY + 12 ? cityMaterial(["dirt", "rock"]) : cityMaterial(["rock", "stone"]);
                var groundColor = y === streetY ? (x % 14 < 7 ? "#34383b" : "#303437") :
                    y < streetY + 4 ? ((x + y) % 3 ? "#777c7e" : "#686d70") :
                    y < streetY + 12 ? "#654a32" : "#47494a";
                forcePut(groundMaterial, x, y, function (p) { p.color = groundColor; });
            }
        }
    }

    function cityAddSewer(streetY) {
        if (!CITY_TUNING.sewerEnabled) return;
        var ceilingY = streetY + CITY_TUNING.sewerCeilingDepth;
        var floorY = ceilingY + CITY_TUNING.sewerRoomHeight + 1;
        if (floorY + 1 >= height) return;
        var wallMaterial = cityMaterial(["brick", "concrete", "stone"]);
        var pipeMaterial = cityMaterial(["steel", "metal"]);
        var sewerLiquid = cityMaterial(["sewage", "dirty_water", "water"]);

        // Carve only the enclosed tunnel. The road and its three-row concrete slab stay solid.
        for (var x = 1; x < width - 1; x++) {
            for (var y = ceilingY + 1; y < floorY; y++) safeDelete(x, y);
            forcePut(wallMaterial, x, ceilingY, function (p) { p.color = (p.x + p.y) % 2 ? "#665d55" : "#756b60"; });
            // Rebuild every row beneath the tunnel as a continuous solid mass.
            for (var belowY = floorY; belowY < height; belowY++) {
                var belowMaterial = belowY < floorY + 4 ? cityMaterial(["concrete", "stone"]) : cityMaterial(["rock", "stone"]);
                forcePut(belowMaterial, x, belowY, function (p) { p.color = p.y < floorY + 4 ? "#55514d" : "#47494a"; });
            }
            forcePut(sewerLiquid, x, floorY - 1, function (p) { p.color = "#52623b"; });
            if (x % 3 !== 0) forcePut(pipeMaterial, x, ceilingY + 1, function (p) { p.color = "#59666a"; });
        }

        // Seal both ends and add regular load-bearing supports so no cavity is unframed.
        for (var side = 0; side <= width - 1; side += Math.max(1, width - 1)) {
            for (var sideY = ceilingY; sideY < height; sideY++) {
                forcePut(wallMaterial, side, sideY, function (p) { p.color = "#625b55"; });
            }
        }
        for (var pillarX = CITY_TUNING.sewerPillarSpacing; pillarX < width - 1; pillarX += CITY_TUNING.sewerPillarSpacing) {
            for (var pillarY = ceilingY + 1; pillarY < floorY; pillarY++) {
                forcePut(wallMaterial, pillarX, pillarY, function (p) { p.color = p.y % 2 ? "#77716a" : "#67615b"; });
            }
        }

        // Closed manholes connect the street to the sewer without leaving a hole in the road.
        for (var manholeX = Math.floor(CITY_TUNING.manholeSpacing / 2); manholeX < width - 2; manholeX += CITY_TUNING.manholeSpacing) {
            forcePut(pipeMaterial, manholeX, streetY, function (p) { p.color = "#30383b"; });
            for (var shaftY = streetY + 1; shaftY <= ceilingY; shaftY++) {
                forcePut(wallMaterial, manholeX - 1, shaftY, function (p) { p.color = "#625b55"; });
                forcePut(wallMaterial, manholeX + 1, shaftY, function (p) { p.color = "#625b55"; });
                forcePut(pipeMaterial, manholeX, shaftY, function (p) { p.color = shaftY % 2 ? "#727d80" : "#4d575a"; });
            }
        }

    }

    function fillCityBottomPixels() {
        // Detect Sandboxels' true playable edges because some builds reserve an outer canvas border.
        var probeX = Math.floor(width / 2);
        var bottomY = height - 1;
        while (bottomY > 0 && !inBounds(probeX, bottomY)) bottomY--;
        var leftX = 0, rightX = width - 1;
        while (leftX < width && !inBounds(leftX, bottomY)) leftX++;
        while (rightX >= 0 && !inBounds(rightX, bottomY)) rightX--;
        for (var bottomX = leftX; bottomX <= rightX; bottomX++) {
            forcePut(cityMaterial(["rock", "stone"]), bottomX, bottomY - 1, function (p) { p.color = "#47494a"; });
            forcePut(cityMaterial(["tungsten", "steel", "metal", "rock"]), bottomX, bottomY, function (p) { p.color = "#010102"; });
        }
        // Explicitly seal the final playable corner after the row pass.
        forcePut(cityMaterial(["tungsten", "steel", "metal", "rock"]), rightX, bottomY, function (p) { p.color = "#010102"; p.sealedCityCorner = true; });
    }

    function cityAddAntiAirGun(center, roofY) {
        for (var baseX = -2; baseX <= 2; baseX++) forcePut(cityMaterial(["steel", "metal", "concrete"]), center + baseX, roofY - 1, function (p) { p.color = "#39454b"; });
        forcePut(cityMaterial(["steel", "metal"]), center - 1, roofY - 2, function (p) { p.color = "#56636a"; });
        forcePut(cityMaterial(["steel", "metal"]), center + 1, roofY - 2, function (p) { p.color = "#56636a"; });
        forcePut("city_anti_air_turret", center, roofY - 2, function (turret) { turret.antiAirCityGun = true; turret.aimX = 0; turret.aimY = -1; });
    }

    function cityAddTower(left, towerWidth, towerHeight, streetY, style, compactBlock, antiAirGun) {
        var roofY = Math.max(3, streetY - towerHeight);
        var facadeColors = ["#c5ccce", "#b5bec1", "#d0cbc1", "#aeb8bc"];
        var windowColors = ["#83a7aa", "#73979e", "#91b6bd", "#6f9298"];
        var facade = facadeColors[cityRandomInt(0, facadeColors.length - 1)];
        var windows = windowColors[cityRandomInt(0, windowColors.length - 1)];
        var right = Math.min(width - 2, left + towerWidth - 1);

        for (var x = left; x <= right; x++) {
            for (var y = roofY; y < streetY; y++) {
                var edge = x === left || x === right || y === roofY || y >= streetY - 2;
                var floorBeam = (y - roofY) % 6 === 5;
                var window = !edge && !floorBeam && (x - left) % 2 === 1 && (y - roofY) % 3 !== 0;
                if (floorBeam && CITY_TUNING.collapsibleFloors) cityPut("city_floor", x, y, facade);
                else cityPut(window ? ["glass", "rad_glass"] : ["concrete", "brick", "stone"], x, y, window ? windows : facade);
            }
        }

        var doorX = left + Math.floor((right - left) / 2);
        forcePut(cityMaterial(["glass", "wood", "steel"]), doorX, streetY - 1, function (door) { door.color = "#40565e"; });
        forcePut(cityMaterial(["glass", "wood", "steel"]), doorX, streetY - 2, function (door) { door.color = "#40565e"; });
        for (var sidewalk = left - 1; sidewalk <= right + 1; sidewalk++) forcePut(cityMaterial(["concrete", "stone"]), sidewalk, streetY, function (p) { p.color = "#a9adae"; });

        // Ground-floor shops make the skyline read as an inhabited city instead of empty slabs.
        var awningColor = ["#c73939", "#2f78bd", "#dc9d27", "#4a9a65"][style % 4];
        for (var shopX = left + 1; shopX < right; shopX++) {
            if (shopX !== doorX) forcePut(cityMaterial(["glass", "steel"]), shopX, streetY - 2, function (shop) { shop.color = "#577b86"; });
            cityPut(["cloth", "plastic", "wood", "steel"], shopX, streetY - 3, awningColor);
        }

        if (style === 1) {
            var center = left + Math.floor((right - left) / 2);
            for (var spire = 1; spire <= 6; spire++) cityPut(["steel", "metal", "wire"], center, roofY - spire, spire === 6 ? "#b71919" : "#bcc5c8");
        } else if (style === 2) {
            for (var step = 1; step <= 3; step++) {
                for (var sx = left + step; sx <= right - step; sx++) cityPut(["concrete", "steel"], sx, roofY - step, facade);
            }
        } else if (style === 3) {
            cityPut(["steel", "metal"], left + 1, roofY - 1, "#69777d");
            cityPut(["steel", "metal"], right - 1, roofY - 1, "#69777d");
        }
        if (style === 0 && right - left >= 6) {
            var tankCenter = left + Math.floor((right - left) / 2);
            for (var leg = -2; leg <= 2; leg += 4) for (var legY = 1; legY <= 3; legY++) cityPut(["steel", "metal"], tankCenter + leg, roofY - legY, "#5b6264");
            for (var tankX = -2; tankX <= 2; tankX++) for (var tankY = 4; tankY <= 6; tankY++) cityPut(["steel", "metal", "wood"], tankCenter + tankX, roofY - tankY, "#6f7779");
        }
        if (compactBlock) {
            var compactMarker = pixelMap[left] && pixelMap[left][Math.min(streetY - 1, roofY + 1)];
            if (compactMarker) compactMarker.compactCityBlock = true;
        }
        if (antiAirGun) cityAddAntiAirGun(left + Math.floor((right - left) / 2), roofY);
    }

    function cityAddRareBuilding(left, towerWidth, towerHeight, streetY) {
        var right = Math.min(width - 2, left + towerWidth - 1);
        var center = left + Math.floor((right - left) / 2);
        var roofY = Math.max(5, streetY - towerHeight);
        for (var x = left; x <= right; x++) {
            for (var y = roofY; y < streetY; y++) {
                var edge = x === left || x === right || y === roofY || y >= streetY - 3;
                var brace = (y - roofY) % 8 === 0 || Math.abs(x - center) === Math.floor((y - roofY) % 8 / 2);
                var material = edge || brace ? ["steel", "metal", "concrete"] : ["glass", "rad_glass"];
                cityPut(material, x, y, edge || brace ? "#27343b" : ((x + y) % 3 ? "#46c8d8" : "#9af5ff"));
            }
        }
        for (var baseX = left - 1; baseX <= right + 1; baseX++) forcePut(cityMaterial(["concrete", "stone"]), baseX, streetY, function (p) { p.color = "#899398"; });
        for (var domeY = 1; domeY <= 3; domeY++) {
            var spread = 4 - domeY;
            for (var domeX = -spread; domeX <= spread; domeX++) cityPut(["glass", "steel"], center + domeX, roofY - domeY, "#7beeff");
        }
        for (var antenna = 4; antenna <= 11; antenna++) cityPut(["steel", "metal", "wire"], center, roofY - antenna, antenna === 11 ? "#ff3045" : "#8fdce5");
        var marker = forcePut(cityMaterial(["steel", "metal"]), center, roofY, function (p) { p.color = "#00e5ff"; });
        if (marker) marker.rareCityLandmark = true;
    }

    function cityAddPerson(x, streetY) {
        if (!empty(x, streetY - 1)) return;
        put("human", x, streetY - 1, function (person) { person.cityCivilian = true; });
    }

    function cityAddCar(center, streetY) {
        var paint = ["#d33b32", "#2d68c2", "#e0ae25", "#e8e8e8", "#31917b"][cityRandomInt(0, 4)];
        for (var dx = -3; dx <= 3; dx++) {
            if (dx === -2 || dx === 2) cityPut(["rubber", "steel"], center + dx, streetY - 1, "#202124");
            else cityPut(["steel", "metal", "concrete"], center + dx, streetY - 1, paint);
        }
        for (var roofX = -1; roofX <= 2; roofX++) cityPut(roofX === 0 || roofX === 1 ? ["glass", "steel"] : ["steel", "metal"], center + roofX, streetY - 2, roofX === 0 || roofX === 1 ? "#79a7ba" : paint);
    }

    function cityAddLamp(x, streetY) {
        for (var pole = 1; pole <= 6; pole++) cityPut(["steel", "metal", "wire"], x, streetY - pole, "#50585b");
        cityPut(["steel", "metal"], x + 1, streetY - 6, "#50585b");
        cityPut(["light", "led_y", "electric", "glass"], x + 2, streetY - 6, "#fff2a3");
    }

    function cityAddTree(x, streetY) {
        for (var trunk = 1; trunk <= 5; trunk++) cityPut(["wood", "branch"], x, streetY - trunk, "#70472c");
        for (var level = 3; level <= 8; level++) {
            var spread = level < 6 ? 2 : 1;
            for (var dx = -spread; dx <= spread; dx++) cityPut(["plant", "grass", "vine"], x + dx, streetY - level, Math.random() < 0.5 ? "#1b702c" : "#2b8d38");
        }
    }

    function cityAddBench(x, streetY) {
        for (var seatX = 0; seatX < 5; seatX++) cityPut(["wood", "steel", "metal"], x + seatX, streetY - 2, "#8a5a32");
        cityPut(["wood", "steel"], x, streetY - 1, "#4f3b2a");
        cityPut(["wood", "steel"], x + 4, streetY - 1, "#4f3b2a");
        for (var backX = 0; backX < 5; backX++) cityPut(["wood", "steel"], x + backX, streetY - 3, "#9b693a");
    }

    function cityAddHydrant(x, streetY) {
        cityPut(["steel", "metal", "concrete"], x, streetY - 1, "#d7352e");
        cityPut(["steel", "metal"], x, streetY - 2, "#ed4a3e");
        cityPut(["steel", "metal"], x - 1, streetY - 1, "#a51f1c");
        cityPut(["steel", "metal"], x + 1, streetY - 1, "#a51f1c");
    }

    function cityAddTrafficSignal(x, streetY) {
        for (var pole = 1; pole <= 8; pole++) cityPut(["steel", "metal", "wire"], x, streetY - pole, "#3f474a");
        for (var arm = 1; arm <= 4; arm++) cityPut(["steel", "metal"], x + arm, streetY - 8, "#3f474a");
        cityPut(["light", "led_r", "electric", "glass"], x + 4, streetY - 7, "#ff3b30");
        cityPut(["light", "led_y", "electric", "glass"], x + 4, streetY - 6, "#ffd229");
        cityPut(["light", "led_g", "electric", "glass"], x + 4, streetY - 5, "#39d353");
    }

    function cityAddTrashCan(x, streetY) {
        cityPut(["steel", "metal", "concrete"], x, streetY - 1, "#566267");
        cityPut(["steel", "metal"], x, streetY - 2, "#758287");
        cityPut(["steel", "metal"], x + 1, streetY - 2, "#475156");
    }

    function cityAddBusStop(x, streetY) {
        for (var roofX = 0; roofX <= 7; roofX++) cityPut(["steel", "metal", "concrete"], x + roofX, streetY - 7, "#3f5058");
        for (var poleY = 1; poleY <= 6; poleY++) {
            cityPut(["steel", "metal"], x, streetY - poleY, "#4c5b61");
            cityPut(["steel", "metal"], x + 7, streetY - poleY, "#4c5b61");
        }
        for (var glassX = 1; glassX <= 6; glassX++) for (var glassY = 3; glassY <= 6; glassY++) cityPut(["glass", "rad_glass"], x + glassX, streetY - glassY, "#739ca7");
        for (var seat = 2; seat <= 5; seat++) cityPut(["wood", "steel"], x + seat, streetY - 2, "#99704a");
        cityPut(["light", "led_y", "electric", "glass"], x + 1, streetY - 6, "#ffe37a");
    }

    function cityAddPhoneBooth(x, streetY) {
        for (var dx = 0; dx <= 2; dx++) for (var dy = 1; dy <= 6; dy++) {
            var frame = dx === 0 || dx === 2 || dy === 1 || dy === 6;
            cityPut(frame ? ["steel", "metal"] : ["glass", "rad_glass"], x + dx, streetY - dy, frame ? "#c92f37" : "#79a9b1");
        }
        cityPut(["wire", "metal", "steel"], x + 1, streetY - 3, "#222629");
    }

    function cityAddMailbox(x, streetY) {
        cityPut(["steel", "metal"], x, streetY - 1, "#244f91");
        cityPut(["steel", "metal"], x, streetY - 2, "#2e66b1");
        cityPut(["steel", "metal"], x + 1, streetY - 2, "#2e66b1");
        cityPut(["steel", "metal"], x, streetY - 3, "#4d7bc1");
    }

    function cityAddCrosswalk(x, streetY) {
        for (var stripe = 0; stripe < 8; stripe += 2) forcePut(cityMaterial(["concrete", "stone"]), x + stripe, streetY, function (p) { p.color = "#d7d8d6"; });
    }

    function cityAddSiren(x, streetY) {
        if (!CITY_TUNING.airRaidSirens) return;
        for (var pole = 1; pole <= 9; pole++) cityPut(["steel", "metal", "wire"], x, streetY - pole, "#4d585e");
        cityPut(["steel", "metal"], x - 1, streetY - 9, "#6c777c");
        cityPut(["steel", "metal"], x + 1, streetY - 9, "#6c777c");
        put("city_air_raid_siren", x, streetY - 10);
    }

    function cityAddShelter(x, streetY) {
        forcePut("city_shelter_door", x, streetY - 1, function (p) { p.color = "#26353b"; p.cityFeature = "evacuation_shelter"; });
        cityPut(["steel", "metal"], x - 1, streetY - 1, "#e6c62f");
        cityPut(["steel", "metal"], x + 1, streetY - 1, "#e6c62f");
        cityPut(["steel", "metal"], x, streetY - 2, "#e6c62f");
    }

    function cityAddSubway(streetY) {
        if (!CITY_TUNING.subwayEnabled) return;
        // Full-width metro halfway through the deep rock, inside a sealed seven-pixel tunnel.
        var rockTopY = streetY + 12;
        var bottomRockY = height - 2;
        var centerY = Math.floor((rockTopY + bottomRockY) / 2);
        var roofY = centerY - 3;
        var trackY = centerY + 3;
        if (roofY <= streetY + CITY_TUNING.sewerCeilingDepth + CITY_TUNING.sewerRoomHeight + 1 || trackY >= height - 2) return;
        var wall = cityMaterial(["concrete", "stone", "brick"]);
        var rail = cityMaterial(["steel", "metal"]);
        var startX = 1;
        var endX = width - 2;
        for (var x = startX; x <= endX; x++) {
            forcePut(wall, x, roofY, function (p) { p.color = x % 4 ? "#43484a" : "#596064"; p.metroRoof = true; });
            for (var tunnelY = roofY + 1; tunnelY < trackY; tunnelY++) safeDelete(x, tunnelY);
            forcePut(rail, x, trackY, function (p) { p.color = x % 3 ? "#4f5558" : "#9aa3a7"; p.metroFloor = true; });
            if (x % 4 === 0) forcePut(wall, x, trackY - 1, function (p) { p.color = "#5f5650"; p.metroSleeper = true; });
            if (x % 12 === 6) cityPut(["light", "led_y", "electric", "glass"], x, roofY + 1, "#fff0a6");
            else if (x % 3 === 0) cityPut(["wire", "metal", "steel"], x, roofY + 1, "#27343a");
        }
        for (var endY = roofY; endY <= trackY; endY++) {
            forcePut(wall, startX - 1, endY, function (p) { p.color = "#555b5d"; });
            forcePut(wall, endX + 1, endY, function (p) { p.color = "#555b5d"; });
        }
        for (var stationX = 42; stationX < width - 20; stationX += 72) {
            for (var p = -11; p <= 11; p++) forcePut(wall, stationX + p, trackY - 1, function (q) { q.color = p % 3 ? "#b7b1a7" : "#e2c94d"; q.metroPlatform = true; });
            for (var signX = -4; signX <= 4; signX++) cityPut(["steel", "metal", "concrete"], stationX + signX, roofY + 1, "#225e86");
            cityPut(["light", "led_y", "electric", "glass"], stationX - 8, roofY + 1, "#fff8cf");
            cityPut(["light", "led_y", "electric", "glass"], stationX + 8, roofY + 1, "#fff8cf");
        }
        put("city_subway_train", Math.max(14, Math.floor(width * 0.22)), centerY, function (train) { train.direction = 1; train.deepMetro = true; });
        put("city_subway_train", Math.min(width - 15, Math.floor(width * 0.78)), centerY, function (train) { train.direction = -1; train.deepMetro = true; });
    }

    function generateInstantCity() {
        var streetY = Math.max(30, Math.min(height - 8, Math.floor(height * CITY_TUNING.streetLevel)));
        cityPaintGround(streetY);
        cityAddSewer(streetY);
        cityAddSubway(streetY);
        var cursor = 3;
        var gapNumber = 0;
        var maxTowerHeight = Math.min(CITY_TUNING.maxBuildingHeight, streetY - 6);
        var rareBuildingEnabled = Math.random() < CITY_TUNING.rareBuildingChance;
        var rareBuildingSlot = rareBuildingEnabled ? cityRandomInt(0, 4) : -1;
        var compactDistrictEnabled = Math.random() < CITY_TUNING.compactDistrictChance;
        var compactDistrictStart = compactDistrictEnabled ? cityRandomInt(1, 4) : -1;
        var compactDistrictLength = compactDistrictEnabled ? cityRandomInt(CITY_TUNING.compactDistrictMinBuildings, CITY_TUNING.compactDistrictMaxBuildings) : 0;

        while (cursor < width - CITY_TUNING.minBuildingWidth - 3) {
            var rareBuildingHere = gapNumber === rareBuildingSlot;
            var compactBuildingHere = compactDistrictEnabled && gapNumber >= compactDistrictStart && gapNumber < compactDistrictStart + compactDistrictLength;
            var towerWidth = rareBuildingHere ? 13 : cityRandomInt(CITY_TUNING.minBuildingWidth, CITY_TUNING.maxBuildingWidth);
            if (towerWidth % 2 === 0) towerWidth++;
            towerWidth = Math.min(towerWidth, width - cursor - 3);
            var towerHeight = rareBuildingHere ? Math.min(streetY - 8, CITY_TUNING.maxBuildingHeight + 18) : cityRandomInt(CITY_TUNING.minBuildingHeight, maxTowerHeight);
            if (rareBuildingHere) cityAddRareBuilding(cursor, towerWidth, towerHeight, streetY);
            else cityAddTower(cursor, towerWidth, towerHeight, streetY, gapNumber % 4, compactBuildingHere, gapNumber % 5 === 2);
            cursor += towerWidth;

            var gap = compactBuildingHere ? 0 : cityRandomInt(CITY_TUNING.minBuildingGap, CITY_TUNING.maxBuildingGap);
            var gapStart = cursor;
            var gapEnd = Math.min(width - 3, cursor + gap - 1);
            if (CITY_TUNING.streetlightEveryGap && gapEnd - gapStart >= 3) cityAddLamp(gapStart + 1, streetY);
            if (gapNumber % CITY_TUNING.carEveryGaps === 0 && gapEnd - gapStart >= 9) cityAddCar(gapStart + Math.floor((gapEnd - gapStart) / 2) + 1, streetY);
            else if (gapNumber % CITY_TUNING.treeEveryGaps === 0 && gapEnd - gapStart >= 6) cityAddTree(gapStart + Math.floor((gapEnd - gapStart) / 2), streetY);
            if (gapEnd - gapStart >= 10 && gapNumber % 4 === 1) cityAddBench(gapStart + 4, streetY);
            if (gapEnd - gapStart >= 7 && gapNumber % 5 === 2) cityAddHydrant(gapEnd - 2, streetY);
            if (gapEnd - gapStart >= 11 && gapNumber % 6 === 3) cityAddTrafficSignal(gapStart + 3, streetY);
            if (gapEnd - gapStart >= 6 && gapNumber % 3 === 2) cityAddTrashCan(gapEnd - 1, streetY);
            if (gapEnd - gapStart >= 14 && gapNumber % 7 === 4) cityAddBusStop(gapStart + 4, streetY);
            if (gapEnd - gapStart >= 9 && gapNumber % 8 === 5) cityAddPhoneBooth(gapEnd - 4, streetY);
            if (gapEnd - gapStart >= 6 && gapNumber % 4 === 0) cityAddMailbox(gapEnd - 2, streetY);
            if (gapEnd - gapStart >= 9 && gapNumber % 3 === 0) cityAddCrosswalk(gapStart + 2, streetY);
            if (gapEnd - gapStart >= 7 && gapNumber % 4 === 2) cityAddShelter(gapEnd - 3, streetY);
            if (gapEnd - gapStart >= 6 && gapNumber % 6 === 1) cityAddSiren(gapStart + Math.floor((gapEnd - gapStart) / 2), streetY);
            for (var person = 0; person < CITY_TUNING.peoplePerGap; person++) {
                var personX = gapStart + 2 + person * Math.max(2, Math.floor((gapEnd - gapStart - 3) / Math.max(1, CITY_TUNING.peoplePerGap)));
                if (personX <= gapEnd) cityAddPerson(personX, streetY);
            }
            cursor = gapEnd + 1;
            gapNumber++;
        }
        fillCityBottomPixels();
    }

    function installCityWorldgenHook() {
        if (typeof worldGen !== "function" || worldGen.highTechCityHook) return;
        var originalWorldGen = worldGen;
        var wrappedWorldGen = function (worldtype) {
            if (worldtype && worldtype.highTechInstantCity) {
                generateInstantCity();
                return;
            }
            return originalWorldGen.apply(this, arguments);
        };
        wrappedWorldGen.highTechCityHook = true;
        wrappedWorldGen.originalWorldGen = originalWorldGen;
        worldGen = wrappedWorldGen;
    }

    function registerCityWorldgen() {
        if (typeof worldgentypes !== "undefined" && worldgentypes) {
            worldgentypes.city = {
                highTechInstantCity: true,
                name: "City"
            };
        }
    }

    function placeAircraftCategoryAfterWeapons() {
        if (typeof categoryOrder !== "undefined" && Array.isArray(categoryOrder)) {
            var oldIndex = categoryOrder.indexOf(AIRCRAFT_CATEGORY);
            if (oldIndex !== -1) categoryOrder.splice(oldIndex, 1);
            var weaponsIndex = categoryOrder.indexOf(CATEGORY);
            categoryOrder.splice(weaponsIndex === -1 ? categoryOrder.length : weaponsIndex + 1, 0, AIRCRAFT_CATEGORY);
        }
        if (typeof document === "undefined") return;
        var weaponsButton = document.getElementById("categoryButton-weapons") || document.querySelector('[category="weapons"], [data-category="weapons"]');
        var aircraftButton = document.getElementById("categoryButton-aircraft") || document.querySelector('[category="aircraft"], [data-category="aircraft"]');
        if (weaponsButton && aircraftButton && weaponsButton.parentNode === aircraftButton.parentNode) {
            weaponsButton.parentNode.insertBefore(aircraftButton, weaponsButton.nextSibling);
        }
    }

    registerCityWorldgen();
    installCityWorldgenHook();
    installBuiltInHumanAI();
    placeAircraftCategoryAfterWeapons();
    if (typeof runAfterLoad === "function") runAfterLoad(function () {
        registerCityWorldgen();
        installCityWorldgenHook();
        installBuiltInHumanAI();
        placeAircraftCategoryAfterWeapons();
        if (typeof setTimeout === "function") {
            setTimeout(placeAircraftCategoryAfterWeapons, 0);
            setTimeout(placeAircraftCategoryAfterWeapons, 250);
        }
        if (typeof logMessage === "function") logMessage("High-Tech Weapons v" + MOD_VERSION + " loaded: instant finished City worldgen enabled.");
    });
})();

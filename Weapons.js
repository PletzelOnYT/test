/* Realistic Nuke — standalone Sandboxels mod */

elements.realistic_nuke = {
    color: ["#303638", "#596265", "#8c7b44", "#d2bd4b"],
    behavior: [
        "XX|XX|XX",
        "XX|XX|XX",
        "M2|M1|M2"
    ],
    category: "weapons",
    state: "solid",
    density: 7800,
    conduct: 1,
    excludeRandom: true,
    cooldown: 10,
    desc: "Detonates on impact, electricity, or heat above 650 C.",

    tick: function(pixel) {
        if (
            pixel.charge ||
            pixel.temp >= 650 ||
            pixel.burning ||
            !isEmpty(pixel.x, pixel.y + 1, false)
        ) {
            realisticNukeExplode(pixel);
            return;
        }

        tryMove(pixel, pixel.x, pixel.y + 1);
        doDefaults(pixel);
    }
};

function realisticNukeCreate(element, x, y) {
    if (
        outOfBounds(x, y) ||
        !isEmpty(x, y, true) ||
        !elements[element]
    ) {
        return null;
    }

    createPixel(element, x, y);
    return pixelMap[x][y];
}

function realisticNukeExplode(pixel) {
    var x = pixel.x;
    var y = pixel.y;

    explodeAt(x, y, 45, [
        "plasma",
        "plasma",
        "plasma",
        "plasma",
        "radiation",
        "fallout",
        "realistic_nuke_fire"
    ]);

    if (!outOfBounds(x, y) && !isEmpty(x, y, true)) {
        deletePixel(x, y);
    }

    var controller = realisticNukeCreate(
        "realistic_nuke_controller",
        x,
        y
    );

    if (controller) {
        controller.age = 0;
        controller.originX = x;
        controller.originY = y;
    }
}

elements.realistic_nuke_controller = {
    color: "#ffffff",
    behavior: [
        "XX|XX|XX",
        "XX|XX|XX",
        "XX|XX|XX"
    ],
    category: "weapons",
    state: "solid",
    density: 999999,
    hidden: true,
    excludeRandom: true,

    tick: function(pixel) {
        pixel.age = (pixel.age || 0) + 1;

        var age = pixel.age;
        var centerX = pixel.originX;
        var centerY = pixel.originY;
        var shockwaveRadius = age * 3;

        // Expanding circular shockwave
        if (shockwaveRadius <= 75) {
            var points = Math.min(
                420,
                Math.max(40, shockwaveRadius * 6)
            );

            for (var i = 0; i < points; i++) {
                var angle = Math.PI * 2 * i / points;

                var waveX = Math.round(
                    centerX + Math.cos(angle) * shockwaveRadius
                );

                var waveY = Math.round(
                    centerY + Math.sin(angle) * shockwaveRadius
                );

                if (outOfBounds(waveX, waveY)) {
                    continue;
                }

                if (isEmpty(waveX, waveY, true)) {
                    realisticNukeCreate(
                        "realistic_nuke_shockwave",
                        waveX,
                        waveY
                    );
                }
                else if (
                    !(waveX === pixel.x && waveY === pixel.y)
                ) {
                    var hitPixel = pixelMap[waveX][waveY];

                    if (hitPixel) {
                        hitPixel.temp = Math.max(
                            hitPixel.temp || 20,
                            2500 - shockwaveRadius * 12
                        );

                        if (
                            shockwaveRadius < 38 &&
                            Math.random() < 0.35
                        ) {
                            deletePixel(waveX, waveY);
                        }
                    }
                }
            }
        }

        // Bright central fireball
        if (age <= 18) {
            var fireRadius = Math.min(25, age * 2);

            for (var fire = 0; fire < 65; fire++) {
                var fireAngle = Math.random() * Math.PI * 2;
                var fireDistance =
                    Math.sqrt(Math.random()) * fireRadius;

                var fireX = Math.round(
                    centerX +
                    Math.cos(fireAngle) * fireDistance
                );

                var fireY = Math.round(
                    centerY +
                    Math.sin(fireAngle) * fireDistance
                );

                realisticNukeCreate(
                    "realistic_nuke_fire",
                    fireX,
                    fireY
                );
            }
        }

        // Mushroom-cloud stem
        if (age >= 3 && age <= 70) {
            var rise = Math.min(62, age);

            for (var stem = 0; stem < 10; stem++) {
                var stemX = Math.round(
                    centerX + (Math.random() - 0.5) * 7
                );

                var stemY = Math.round(
                    centerY - Math.random() * rise
                );

                realisticNukeCreate(
                    "realistic_nuke_cloud",
                    stemX,
                    stemY
                );
            }

            // Procedural mushroom-cloud cap
            var capY = Math.round(centerY - rise);
            var capRadius = Math.min(32, 4 + age * 0.45);

            for (var cap = 0; cap < 24; cap++) {
                var capAngle = Math.random() * Math.PI * 2;

                var capDistance =
                    capRadius *
                    (0.35 + Math.random() * 0.65);

                var capX = Math.round(
                    centerX +
                    Math.cos(capAngle) * capDistance
                );

                var cloudY = Math.round(
                    capY +
                    Math.sin(capAngle) *
                    capDistance *
                    0.4
                );

                realisticNukeCreate(
                    "realistic_nuke_cloud",
                    capX,
                    cloudY
                );
            }
        }

        // Radioactive fallout
        if (age >= 25 && age <= 95) {
            for (var dust = 0; dust < 5; dust++) {
                realisticNukeCreate(
                    "realistic_nuke_fallout",
                    Math.round(
                        centerX +
                        (Math.random() - 0.5) * 110
                    ),
                    Math.round(
                        centerY -
                        25 -
                        Math.random() * 40
                    )
                );
            }
        }

        if (age > 105) {
            deletePixel(pixel.x, pixel.y);
        }
    }
};

elements.realistic_nuke_shockwave = {
    color: ["#ffffff", "#fff4cf", "#d7c5a3"],
    behavior: [
        "XX|XX|XX",
        "XX|XX|XX",
        "XX|XX|XX"
    ],
    category: "weapons",
    state: "gas",
    density: 0.01,
    temp: 900,
    hidden: true,
    excludeRandom: true,

    tick: function(pixel) {
        pixel.life = (pixel.life || 0) + 1;

        if (pixel.life > 3) {
            deletePixel(pixel.x, pixel.y);
        }
    }
};

elements.realistic_nuke_fire = {
    color: [
        "#ffffff",
        "#fff45c",
        "#ff9900",
        "#ff3300"
    ],
    behavior: [
        "M2|M1|M2",
        "M1|XX|M1",
        "M2|M1|M2"
    ],
    category: "weapons",
    state: "gas",
    density: 0.08,
    temp: 9000,
    hidden: true,
    excludeRandom: true,

    tick: function(pixel) {
        pixel.life = (pixel.life || 0) + 1;

        if (pixel.life > 25) {
            changePixel(
                pixel,
                "realistic_nuke_cloud"
            );
            return;
        }

        doDefaults(pixel);
    }
};

elements.realistic_nuke_cloud = {
    color: [
        "#171513",
        "#302a26",
        "#51453b",
        "#78614d",
        "#9b7c61"
    ],
    behavior: [
        "M2|M1|M2",
        "M1|XX|M1",
        "M2|M1|M2"
    ],
    category: "weapons",
    state: "gas",
    density: 0.15,
    temp: 700,
    hidden: true,
    excludeRandom: true,

    tick: function(pixel) {
        pixel.life = (pixel.life || 0) + 1;

        tryMove(
            pixel,
            pixel.x + (
                Math.random() < 0.5 ? -1 : 1
            ),
            pixel.y - 1
        );

        if (
            pixel.life > 180 &&
            Math.random() < 0.04
        ) {
            deletePixel(pixel.x, pixel.y);
            return;
        }

        doDefaults(pixel);
    }
};

elements.realistic_nuke_fallout = {
    color: [
        "#62772f",
        "#82963b",
        "#4c6025",
        "#91834b"
    ],
    behavior: [
        "XX|XX|XX",
        "XX|XX|XX",
        "M2|M1|M2"
    ],
    category: "weapons",
    state: "solid",
    density: 430,
    temp: 180,
    hidden: true,
    excludeRandom: true,

    tick: function(pixel) {
        pixel.life = (pixel.life || 0) + 1;

        if (
            pixel.life > 400 &&
            Math.random() < 0.005
        ) {
            if (elements.radiation) {
                changePixel(pixel, "radiation");
            }
            else {
                deletePixel(pixel.x, pixel.y);
            }

            return;
        }

        doDefaults(pixel);
    }
};

console.log(
    "Realistic Nuke loaded in the Weapons category."
);

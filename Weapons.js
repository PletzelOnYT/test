async function _weaponsjsprompt(message, defaultValue = "") {
    return new Promise(resolve => {
        promptInput(message, (result) => {
            resolve(result);
        }, "weapons.js is asking you...", defaultValue);
    })
}

elements.tsar_bomba = {
    color: "#524C41",
    behavior: [
        "XX|EX:150>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:150>plasma|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1300,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.little_boy = {
    color: "#F5F5DC",
    behavior: [
        "XX|EX:20>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:70>plasma,plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 500,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.fat_man = {
    color: ["#ffff00","#333333"],
    behavior: [
        "XX|EX:28>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:98>plasma,plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1000,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.self_propelled_bomb = {
    color: "#71797E",
    tick: function(pixel) {
        if ((pixel.temp > 1000 || pixel.charge) && !pixel.burning) {
            pixel.burning = true;
            pixel.burnStart = pixelTicks;
        }
        if (pixel.burning) {
            if (!tryMove(pixel, pixel.x, pixel.y-1)) {
                tryMove(pixel, pixel.x+(Math.random() < 0.5 ? -1 : 1), pixel.y-1);
            }
            if (pixelTicks-pixel.burnStart > 50 && Math.random() < 0.1) {
                explodeAt(pixel.x, pixel.y, 10, "bomb");
            }
        }
        else {
            if (!tryMove(pixel, pixel.x, pixel.y+1)) {
                tryMove(pixel, pixel.x+(Math.random() < 0.5 ? -1 : 1), pixel.y+1);
            }
        }
        doDefaults(pixel);
    },
    burn: 90,
    burnTime: 100,
    density: 2000,
    conduct: 1,
    state: "solid",
    category: "weapons"
};

elements.cluster_munition = {
    color: "#444444",
    behavior: [
        "XX|EX:10>smoke,smoke,smoke,smoke,bomb,bomb|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:10>smoke,smoke,smoke,smoke,bomb,cluster_munition|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1300,
};

elements.fast_bomb = {
    color: "#524c41",
    category: "weapons",
    state: "solid",
    behavior: [
        "XX|EX:10>explosion|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:10>explosion|M2",
        ],
    tick: function(pixel) {
        for (var i=0; i<3; i++) {
            if (!tryMove(pixel, pixel.x, pixel.y+1)) {
                if (!isEmpty(pixel.x, pixel.y+1,true)) {
                    }
                }
            }
        },
    density: 1300,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.liquid_bomb = {
    color: "#524c41",
    tick: function(pixel) {
                if (pixel.start === pixelTicks) {return}
                if (pixel.charge && elements[pixel.element].behaviorOn) {
                    pixelTick(pixel)
                }
                if (elements[pixel.element].viscosity && (!((Math.random()*100) < 100 / Math.pow(elements[pixel.element].viscosity, 0.25)))) {
                    var move1Spots = [
                        [pixel.x, pixel.y+1]
                    ]
                }
                else {
                    var move1Spots = [
                        [pixel.x+1, pixel.y+1],
                        [pixel.x, pixel.y+1],
                        [pixel.x-1, pixel.y+1],
                    ]
                }
                var moved = false;
                for (var i = 0; i < move1Spots.length; i++) {
                    var coords = move1Spots[Math.floor(Math.random()*move1Spots.length)];
                    if (tryMove(pixel, coords[0], coords[1])) { moved = true; break; }
                    else { move1Spots.splice(move1Spots.indexOf(coords), 1); }
                }
                if (!moved) {
                    if (elements[pixel.element].viscosity===undefined || !(!((Math.random()*100) < 100 / Math.pow(elements[pixel.element].viscosity, 0.25)))) {
                        if (Math.random() < 0.5) {
                            if (!tryMove(pixel, pixel.x+1, pixel.y)) {
                                tryMove(pixel, pixel.x-1, pixel.y);
                            }
                        } else {
                            if (!tryMove(pixel, pixel.x-1, pixel.y)) {
                                tryMove(pixel, pixel.x+1, pixel.y);
                            }
                        }
                    }
                }
                doDefaults(pixel);
            },
    category: "weapons",
    state: "liquid",
    behavior: [
        "XX|EX:10>explosion|XX",
        "XX|XX|XX",
        "XX|EX:10>explosion|XX",
        ],
    density: 1300,
    excludeRandom: true,
    ignore: "gas_bomb",
    cooldown: defaultCooldown
};

elements.gas_bomb = {
    color: "#524c41",
    tick: function(pixel) {
                if (pixel.start === pixelTicks) {return}
                if (pixel.charge && elements[pixel.element].behaviorOn) {
                    pixelTick(pixel)
                }
                var move1Spots = [
                    [pixel.x, pixel.y+1],
                    [pixel.x, pixel.y-1],
                    [pixel.x+1, pixel.y],
                    [pixel.x-1, pixel.y],
                ]
                var moved = false;
                for (var i = 0; i < move1Spots.length; i++) {
                    var coords = move1Spots[Math.floor(Math.random()*move1Spots.length)];
                    if (tryMove(pixel, coords[0], coords[1])) { moved = true; break; }
                    else { move1Spots.splice(move1Spots.indexOf(coords), 1);}
                }
                if (!moved) {
                    var move2Spots = [
                        [pixel.x+1, pixel.y+1],
                        [pixel.x-1, pixel.y+1],
                        [pixel.x+1, pixel.y-1],
                        [pixel.x-1, pixel.y-1],
                    ]
                    for (var i = 0; i < move2Spots.length; i++) {
                        var coords = move2Spots[Math.floor(Math.random()*move2Spots.length)];
                        if (tryMove(pixel, coords[0], coords[1])) { break; }
                        else { move2Spots.splice(move2Spots.indexOf(coords), 1); }
                    }
                }
                doDefaults(pixel);
            },
    category: "weapons",
    state: "gas",
    behavior: [
        "XX|EX:10>explosion|XX",
        "XX|XX|XX",
        "XX|EX:10>explosion|XX",
        ],
    density: 1300,
    excludeRandom: true,
    ignore: "liquid_bomb",
    cooldown: defaultCooldown
};

elements.static_bomb = {
    color: "#524c41",
    behavior: [
        "XX|EX:10|XX",
        "EX:10|XX|EX:10",
        "XX|EX:10|XX",
    ],
    category: "weapons",
    state: "solid",
    density: 1300,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.laser_bomb = {
    category: "weapons",
    color: "#524c41",
    tick: function(pixel) {
        var x = pixel.x;
        for (var y = pixel.y; y < height+1; y++) {
            if (outOfBounds(x, y)) {
                if (isEmpty(x, y-1)) { createPixel("smoke", x, y-1); }
                break;
            }
            if (isEmpty(x, y)) {
                createPixel("flash", x, y);
                pixelMap[x][y].color = "#ff0000";
                pixelMap[x][y].temp = 35000;
                pixelMap[x][y].delay = (y + pixel.y) / 8;
            }
        }
        for (var y = pixel.y; y < height-1; y--) {
            if (outOfBounds(x, y)) {
                if (isEmpty(x, y+1)) { createPixel("smoke", x, y+1); }
                break;
            }
            if (isEmpty(x, y)) {
                createPixel("flash", x, y);
                pixelMap[x][y].color = "#ff0000";
                pixelMap[x][y].temp = 35000;
                pixelMap[x][y].delay = (y + pixel.y) / 8;
            }
        }
        var y = pixel.y;
        for (var x = pixel.x; x < width+1; x++) {
            if (outOfBounds(x, y)) {
                if (isEmpty(x-1, y)) { createPixel("smoke", x-1, y); }
                break;
            }
            if (isEmpty(x, y)) {
                createPixel("flash", x, y);
                pixelMap[x][y].color = "#ff0000";
                pixelMap[x][y].temp = 35000;
                pixelMap[x][y].delay = (x + pixel.x) / 8;
            }
        }
        for (var x = pixel.x; x < width-1; x--) {
            if (outOfBounds(x, y)) {
                if (isEmpty(x+1, y)) { createPixel("smoke", x+1, y); }
                break;
            }
            if (isEmpty(x, y)) {
                createPixel("flash", x, y);
                pixelMap[x][y].color = "#ff0000";
                pixelMap[x][y].temp = 35000;
                pixelMap[x][y].delay = (x + pixel.x) / 8;
            }
        }
        deletePixel(pixel.x, pixel.y);
    },
};

elements.mini_nuke = {
    color: "#534636",
    behavior: [
        "XX|XX|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:20>plasma,plasma,plasma,plasma,radiation,rad_steam|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1500,
    excludeRandom: true,
    cooldown: defaultCooldown
};

elements.cluster_nuke = {
    color: "#323232",
    ignore: "cluster_nuke",
    category: "weapons",
    behavior: behaviors.POWDER,
    maxSize: 1,
    tick: (pixel) => {
        for (var y = 1; y < 50; y++) {
            if (!isEmpty(pixel.x, pixel.y + y, false)) {
                explodeAt(pixel.x,pixel.y,50,["dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","nuke",])
            }
        }
    }
};

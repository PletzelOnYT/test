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
},
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
},
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
},
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
},
elements.up_missile = {
    color: "#4c4e42",
    behavior: [
        "M2|M1 AND EX:10|M2",
       "EX:10|XX|EX:10",
        "XX|EX:10|XX",
    ],
    state: "solid",
    category:"ammunition",
    density: 1300,
    excludeRandom: true,
    cooldown: defaultCooldown
},
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
},
    elements.RL_cluster_munition = {
    color: "#444444",
    behavior: [
        "XX|XX|XX",
        "CRcluster%20|XX|CR:cluster%20",
        "M2|M1|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1300,
},
    elements.cluster = {
    color: "#444444",
    behavior: [
        "XX|EX:10%10|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:10%10|M2",
    ],
    category: "ammunition",
    state: "solid",
    density: 1300,
    hidden: true,
},
                                                elements.flak_cannon = {
    color: "#C0C0C0",
    behavior: behaviors.WALL,
    behaviorOn: [
        "XX|CR:flak|XX",
        "XX|XX|XX",
        "XX|XX|XX",
    ],
    category: "weapons",
    state: "solid",
    density: 1300,
    conduct: 1,
},
    elements.flak = {
    color: "#f0f0f0",
    tick: function(pixel) {
        if ((pixel.temp > 10 || pixel.charge) && !pixel.burning) {
            pixel.burning = true;
            pixel.burnStart = pixelTicks;
        }
        if (pixel.burning) {
            if (!tryMove(pixel, pixel.x, pixel.y-1)) {
                tryMove(pixel, pixel.x+(Math.random() < 0.5 ? -1 : 1), pixel.y-1);
            }
            if (pixelTicks-pixel.burnStart > 50 && Math.random() < 0.005) {
                explodeAt(pixel.x, pixel.y, 10, "flak_shrapnel");
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
    category: "ammunition"
},
    elements.flak_shrapnel = {
    color: "#71797E",
       behavior: [
        "XX|XX|XX",
        "XX|EX:5 %10|XX",
        "M2|M1|M2",
    ],
    burn: 90,
    burnTime: 100,
    density: 2000,
    conduct: 1,
    state: "solid",
    category: "ammunition"
},
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
},
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
},
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
}
    elements.missile_shrapnel = {
    color: "#71797E",
       behavior: [
        "XX|XX|XX",
        "XX|EX:5 %20|XX",
        "M2%20|M1%20|M2%20",
    ],
    burn: 90,
    burnTime: 100,
    density: 2000,
    conduct: 1,
    state: "solid",
    category: "ammunition"
},
createAtXvar = 0;
createAtYvar = 0;
create1var = "";
elements.element_spawner = {
    color: "#71797E",
    onSelect: async function() {
        var answer1 = await _weaponsjsprompt("Please input the x value.",(createAtXvar||undefined));
        if (!answer1) {return}
        createAtXvar = parseInt(answer1);
        var answer2 = await _weaponsjsprompt("Please input the y value.",(createAtYvar||undefined));
        if (!answer2) {return}
        createAtYvar = parseInt(answer2);
        var answer3 = await _weaponsjsprompt("Please input what element should spawn.",(create1var||undefined));
        if (!answer3) {return}
        create1var = answer3;
    },
    tick: function(pixel) {
        if (pixel.charge){
            createPixel(create1var, createAtXvar, createAtYvar);
        }
        doDefaults(pixel);
    },
    density: 1,
    conduct: 1,
    state: "solid",
    category: "machines"
},
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
}
var target =[,];
var tgt = "head";
elements.tracking_missile = {
    color: "#323232",
    category: "weapons",
    behavior: [
        "XX|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|XX",
        "EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel",
        "EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel",
        "EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|XX|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel",
        "EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel",
        "EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel",
        "XX|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|EX:20>missile_shrapnel|XX",
    ],
    onSelect: function() {
        var answer1 = prompt("Please input the target element.",(tgt||undefined));
        if (!answer1) {return}
        tgt = answer1;
    },
    tick: (pixel) => {
        for (var x = 1; x < width; x++) {
            for (var y = 1; y < height; y++) {
                if (!isEmpty(x,y)) {
                    if (pixelMap[x][y].element===tgt) {
                        target = [pixelMap[x][y].x, pixelMap[x][y].y];
                    }
                }
            }
        }
        if (pixel.x != target[0] || pixel.y != target[1]) {
            let {x, y} = pixel;
            const empty = checkForEmptyPixels(x, y);
            const [tX, tY] = target;
            let bestVal = Math.sqrt(Math.pow(tX - x, 2) + Math.pow(tY - y, 2));
            let best = null;
            for (const pixelPair of empty) {
                const [x_, y_] = [x + pixelPair[0], y + pixelPair[1]];
                const c = Math.sqrt(Math.pow(tX - x_, 2) + Math.pow(tY - y_, 2));
                if (c < bestVal) {
                    bestVal = c;
                    best = pixelPair;
                }
            }
            if (best) {
                tryMove(pixel, x + best[0]*2, y + best[1]*2, undefined, true);
            }
        } 
    }
},
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
},
elements.cluster_nuke = {
    color: "#323232",
    category: "weapons",
    behavior: behaviors.POWDER,
    tick: (pixel) => {
        for (var y = 1; y < 50; y++) {
            if (!isEmpty(pixel.x, pixel.y + y, false)) {
                explodeAt(pixel.x,pixel.y,50,["dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","dirty_bomb","nuke",])
            }
        }
    }
}
document.onkeydown = function(ki)/*keyboard_input*/ {
    //a
    if (ki.keyCode == 65) {
        KA = true;
        //vX ++;
    }
    //d
    if (ki.keyCode == 68) {
        KD = true;
        //vX ++;
    }
    //w
    if (ki.keyCode == 87) {
        KW = true;
        //vY ++;
    }
    //s
    if (ki.keyCode == 83) {
        KS = true;
        //vY ++;
    }
}
document.onkeyup = function(i2)/*keyboard_input*/ {
    //a
    if (i2.keyCode == 65) {
        KA = false;
        //vX --;
    }
    //d
    if (i2.keyCode == 68) {
        KD = false;
       //vX --;
    }
    //w
    if (i2.keyCode == 87) {
        KW = false;
        //vY = 0;
    }
    //s
    if (i2.keyCode == 83) {
        KS = false;
        //vY = 0;
    }
}
var KA = false;
var KD = false;
var KW = false;
var KS = false;
var vX = 1;
var vY = 1;
elements.heli_bomb = {
    behavior: [
        "XX|EX:10|XX",
        "EX:10|XX|EX:10",
        "XX|EX:10|XX",
    ],
    tick: function(pixel) {
    /*if (vX === 3) {
            vX --;
        }
    if (vY === 3) {
            vY --;
        }*/
    if (KA === true) {
            tryMove (pixel,pixel.x-vX,pixel.y)
        }
    if (KD === true) {
            tryMove (pixel,pixel.x+vX,pixel.y)
        }
    if (KW === true) {
            tryMove (pixel,pixel.x,pixel.y-vY)
        }
    if (KS === true) {
            tryMove (pixel,pixel.x,pixel.y+vY)
        }
    },
    category: "weapons",
    states:"solid",
    color: "#524c41",
},
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
},
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
}

// Additional well-known nuclear weapons
elements.castle_bravo = {
    color: ["#6f765f","#d8c46a"],
    behavior: [
        "XX|EX:30>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:120>plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1700,
    excludeRandom: true,
    cooldown: defaultCooldown
},
elements.ivy_mike = {
    color: ["#444b48","#9ca39d"],
    behavior: [
        "XX|EX:35>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:135>plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1900,
    excludeRandom: true,
    cooldown: defaultCooldown
},
elements.trinity_gadget = {
    color: ["#303030","#8b6f47"],
    behavior: [
        "XX|EX:22>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:85>plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1600,
    excludeRandom: true,
    cooldown: defaultCooldown
},
elements.b83_nuclear_bomb = {
    color: ["#555b45","#b7ad69"],
    behavior: [
        "XX|EX:28>plasma|XX",
        "XX|XX|XX",
        "M2|M1 AND EX:110>plasma,plasma,plasma,radiation,fallout|M2",
    ],
    category: "weapons",
    state: "solid",
    density: 1800,
    excludeRandom: true,
    cooldown: defaultCooldown
};

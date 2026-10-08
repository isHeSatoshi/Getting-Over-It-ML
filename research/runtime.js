/* Original packaged TurboWarp VM and real renderer, with explicit stepping.
 * No cloud provider, live-action poller, collision stubs, or automatic restart.
 */
"use strict";
(async () => {
    const params = new URLSearchParams(location.search);
    // Scratch's native stage and the game's FRAME/30 timer are the reference.
    const fps = Number(params.get("fps") || 30);
    const width = Number(params.get("width") || 480);
    const height = Number(params.get("height") || 360);
    const compiled = params.get("compiled") !== "false";
    const fast = params.get("fast") === "true";
    if (![30, 60].includes(fps) || ![480, 640].includes(width) || ![360, 480].includes(height)) {
        throw new Error("Unsupported reference-runtime configuration");
    }
    const scaffolding = new Scaffolding.Scaffolding();
    scaffolding.width = width;
    scaffolding.height = height;
    scaffolding.resizeMode = "preserve-ratio";
    scaffolding.usePackagedRuntime = false;
    scaffolding.setup();
    scaffolding.appendTo(document.getElementById("app"));
    const vm = scaffolding.vm;
    const run = vm.runtime;
    window.vm = vm;
    vm.setTurboMode(false);
    if (vm.setFramerate) vm.setFramerate(fps);
    if (vm.setInterpolation) vm.setInterpolation(false);
    if (vm.setRuntimeOptions) vm.setRuntimeOptions({fencing: false, miscLimits: false, maxClones: 300});
    if (vm.setCompilerOptions) vm.setCompilerOptions({enabled: compiled, warpTimer: true});
    scaffolding.setUsername("rl-research");
    const project = await (await fetch("assets/project.json")).arrayBuffer();
    scaffolding.storage.addWebStore(
        [scaffolding.storage.AssetType.ImageVector, scaffolding.storage.AssetType.ImageBitmap,
         scaffolding.storage.AssetType.Sound],
        asset => new URL("assets/" + asset.assetId + "." + asset.dataFormat, location.href).href
    );
    await scaffolding.loadProject(project);
    run.stopAll();
    // Reloading every episode leaks retired costume skins in this packaged
    // renderer. Restore the complete initial target data in place instead.
    // Keeping variable objects intact also preserves compiled-block references.
    const initialTargets = run.targets.filter(t => t.isOriginal).map(t => ({
        target: t, variables: JSON.parse(JSON.stringify(t.variables)),
        x: t.x, y: t.y, size: t.size, direction: t.direction,
        visible: t.visible, costume: t.currentCostume, rotationStyle: t.rotationStyle,
        order: t.isStage ? null : vm.renderer.getDrawableOrder(t.drawableID),
    }));
    const playerTarget = run.targets.find(t => t.isOriginal && t.getName() === "Player");
    const stageVariables = new Map(Object.values(run.getTargetForStage().variables).map(v => [v.name, v]));
    const playerVariables = new Map(Object.values(playerTarget.variables).map(v => [v.name, v]));
    let levelIds = [];
    const memo = fast ? ResearchCollisionMemo.createMemo(vm.renderer, () => playerTarget) : null;
    const actualDraw = vm.renderer.draw.bind(vm.renderer);
    if (fast) vm.renderer.draw = () => {};
    let tick = 0, previous = null, commandId = 0, seedState = 1, virtualMs = 0;
    let collision = {body: 0, hammer: 0, queries: 0};
    let lastState = null;
    const realTouching = vm.renderer.isTouchingDrawables.bind(vm.renderer);
    vm.renderer.isTouchingDrawables = function (id, candidates) {
        const hit = realTouching(id, candidates);
        const player = fast ? playerTarget : run.targets.find(t => t.isOriginal && t.getName() === "Player");
        if (player && id === player.drawableID) {
            collision.queries++;
            const costume = player.getCostumes()[player.currentCostume].name;
            if (hit && costume === "player hitbox") collision.body++;
            if (hit && costume === "hammer hitbox") collision.hammer++;
        }
        return hit;
    };
    const random = () => {
        seedState = (Math.imul(1664525, seedState) + 1013904223) >>> 0;
        return seedState / 4294967296;
    };
    function target(name) {
        const t = run.targets.find(t => t.isOriginal && t.getName() === name);
        if (!t) throw new Error("Missing target: " + name);
        return t;
    }
    function variable(t, name) {
        const v = Object.values(t.variables).find(v => v.name === name);
        if (!v) throw new Error("Missing variable: " + t.getName() + "/" + name);
        return v.value;
    }
    const stage = name => Number(fast ? stageVariables.get(name).value : variable(run.getTargetForStage(), name));
    const local = name => Number(fast ? playerVariables.get(name).value : variable(target("Player"), name));
    function state() {
        const px = stage("PLAYER X"), py = stage("PLAYER Y");
        const hx = stage("HAMMER X"), hy = stage("HAMMER Y");
        const angle = Math.atan2(hy - py, hx - px);
        const deltaAngle = previous ? Math.atan2(Math.sin(angle - previous.hammer_angle_rad),
                                                Math.cos(angle - previous.hammer_angle_rad)) : 0;
        const p = fast ? playerTarget : target("Player");
        return {
            schema_version: 2, backend: "turbowarp-real-renderer", tick, physics_hz: fps,
            execution_mode: fast ? "fast" : "reference",
            frame_id: stage("FRAME"), game_time: virtualMs / 1000,
            command_id_applied: commandId,
            player_world_x: px, player_world_y: py,
            player_vx: previous ? px - previous.player_world_x : 0,
            player_vy: previous ? py - previous.player_world_y : 0,
            player_impulse_vx: stage("PLAYER SX"), player_impulse_vy: stage("PLAYER SY"),
            hammer_world_x: hx, hammer_world_y: hy,
            hammer_vx: previous ? hx - previous.hammer_world_x : 0,
            hammer_vy: previous ? hy - previous.hammer_world_y : 0,
            hammer_angle_rad: angle, hammer_angular_velocity: deltaAngle,
            camera_x: stage("CAMERA X"), camera_y: stage("CAMERA Y"),
            player_screen_x: p.x, player_screen_y: p.y,
            pointer_x: run.ioDevices.mouse.getScratchX(), pointer_y: run.ioDevices.mouse.getScratchY(),
            body_collision: collision.body > 0, hammer_collision: collision.hammer > 0,
            collision_queries: collision.queries,
            control_error_memory_x: local("touch x"), control_error_memory_y: local("touch y"),
            effort: local("effort"), hammer_air: stage("HAMMER AIR"),
            last_tx: local("last tx"), last_ty: local("last ty"),
            last_hammer_distance: local("last h dist"), last_effort: local("lastEffort"),
            offset_x: local("cox"), offset_y: local("coy"),
            success: py > 16000, dead: py < -180,
            stage_width: run.stageWidth, stage_height: run.stageHeight,
        };
    }
    function pointer(x, y, down = false) {
        // The mouse reporter is interpreted by the game as a PLAYER-RELATIVE
        // offset, not a world coordinate or a hammer screen location.
        run.ioDevices.mouse.postData({
            x: (x / run.stageWidth + 0.5) * 640,
            y: (0.5 - y / run.stageHeight) * 480,
            canvasWidth: 640, canvasHeight: 480, isDown: down
        });
    }
    function advance(x, y, id, down = false) {
        previous = lastState;
        commandId = id;
        pointer(x, y, down);
        collision = {body: 0, hammer: 0, queries: 0};
        if (memo) {
            // Reset may create new Level clones on its first tick.
            if (!levelIds.length || commandId === 0) {
                levelIds = run.targets.filter(t => t.getName() === "Level").map(t => t.drawableID);
            }
            memo.beginTick(levelIds);
        }
        virtualMs += 1000 / fps;
        run.currentMSecs = virtualMs;
        run._step();
        tick++;
        lastState = state();
        return lastState;
    }
    async function reset(seed = 0) {
        run.stopAll();
        seedState = seed >>> 0;
        Math.random = random;
        for (const initial of initialTargets) {
            const t = initial.target;
            for (const [id, value] of Object.entries(initial.variables)) {
                t.variables[id].value = JSON.parse(JSON.stringify(value.value));
            }
            if (!t.isStage) {
                t.setSize(initial.size);
                t.setDirection(initial.direction);
                t.setRotationStyle(initial.rotationStyle);
                t.setCostume(initial.costume);
                t.setXY(initial.x, initial.y);
                t.setVisible(initial.visible);
                t.clearEffects();
                vm.renderer.setDrawableOrder(t.drawableID, initial.order);
            }
        }
        virtualMs = 0;
        Date.now = () => Math.floor(virtualMs);
        run.currentMSecs = 0;
        run.currentStepTime = 1000 / fps;
        run.ioDevices.clock.resetProjectTimer();
        // Audio/commentary are presentation-only. Avoid asynchronous sound waits.
        for (const name of ["sound_play", "sound_playuntildone", "sound_seteffectto",
                            "sound_setvolumeto", "sound_changeeffectby", "sound_stopallsounds"]) {
            run._primitives[name] = () => {};
        }
        for (const name of ["SFX", "COMMENTARY"]) {
            Object.values(run.getTargetForStage().variables).find(v => v.name === name).value = "false";
        }
        run.ioDevices.keyboard.postData({key: " ", isDown: false});
        tick = 0; previous = null; lastState = null; commandId = 0;
        levelIds = [];
        pointer(0, 0);
        run.startHats("event_whenbroadcastreceived", {BROADCAST_OPTION: "New Game"});
        for (let i = 0; i < 120; i++) advance(0, 0, 0);
        if (memo) memo.resetStats();
        if (!fast) {
            vm.renderer.draw();
            document.getElementById("status").textContent = JSON.stringify(lastState, null, 2);
        }
        return lastState;
    }
    // Exact in-page state snapshots. At every tick boundary the only live
    // thread is the compiled Player main loop (stack depth 1), the clone set is
    // fixed, and all game state lives in Scratch variables/lists and sprite
    // properties. The live thread is left untouched; state is written around it.
    // Fidelity is verified by explore/snapshot_fidelity.py, not assumed.
    const snapshots = new Map();
    let nextSnapshot = 1;
    // Packed snapshots: numeric variable values and sprite properties live in typed arrays
    // (the variable/target objects are shared via `layout`); only non-numeric values (strings,
    // lists) are stored individually. `previous` is not saved: advance() overwrites it first.
    const EFFECT_KEYS = ["color", "fisheye", "whirl", "pixelate", "mosaic", "brightness", "ghost"];
    let layout = null;
    function layoutValid() {
        return layout && layout.targets.length === run.targets.length &&
               run.targets.every((t, i) => t === layout.targets[i]);
    }
    function buildLayout() {
        const targets = run.targets.slice(), vars = [];
        for (const t of targets) for (const v of Object.values(t.variables)) vars.push(v);
        layout = {targets, vars};
    }
    function takeSnapshot() {
        if (run.threads.length !== 1) throw new Error("Snapshot needs exactly one live thread");
        if (!layoutValid()) buildLayout();
        const L = layout, nv = L.vars.length, nt = L.targets.length, K = EFFECT_KEYS.length;
        const nums = new Float64Array(nv), isNum = new Uint8Array(nv), others = [];
        for (let i = 0; i < nv; i++) {
            const val = L.vars[i].value;
            if (typeof val === "number") {nums[i] = val; isNum[i] = 1;}
            else others.push([i, Array.isArray(val) ? val.slice() : val]);
        }
        const props = new Float64Array(nt * 6), fx = new Float64Array(nt * K), rot = new Array(nt);
        for (let j = 0; j < nt; j++) {
            const t = L.targets[j];
            props[j * 6] = t.x; props[j * 6 + 1] = t.y; props[j * 6 + 2] = t.size; props[j * 6 + 3] = t.direction;
            props[j * 6 + 4] = t.currentCostume; props[j * 6 + 5] = t.visible ? 1 : 0;
            rot[j] = t.rotationStyle;
            for (let k = 0; k < K; k++) fx[j * K + k] = t.effects[EFFECT_KEYS[k]] || 0;
        }
        return {layout: L, nums, isNum, others, props, fx, rot, tick, commandId, seedState, virtualMs,
                collision: {...collision}, lastState: lastState ? {...lastState} : null,
                levelIds: levelIds.slice()};
    }
    function applySnapshot(s) {
        const L = s.layout;
        if (run.threads.length !== 1 || L.targets.length !== run.targets.length ||
            run.targets.some((t, i) => t !== L.targets[i])) {
            throw new Error("Snapshot target/thread set changed; cannot restore");
        }
        const K = EFFECT_KEYS.length;
        for (let i = 0; i < L.vars.length; i++) if (s.isNum[i]) L.vars[i].value = s.nums[i];
        for (const [i, val] of s.others) {
            const v = L.vars[i];
            if (Array.isArray(val)) {
                if (!Array.isArray(v.value)) v.value = [];
                v.value.length = 0;
                for (const item of val) v.value.push(item);
            } else v.value = val;
        }
        for (let j = 0; j < L.targets.length; j++) {
            const t = L.targets[j];
            for (let k = 0; k < K; k++) {
                const value = s.fx[j * K + k];
                if ((t.effects[EFFECT_KEYS[k]] || 0) !== value) t.setEffect(EFFECT_KEYS[k], value);
            }
            if (t.isStage) continue;
            t.setRotationStyle(s.rot[j]);
            t.setCostume(s.props[j * 6 + 4]);
            t.setSize(s.props[j * 6 + 2]);
            t.setDirection(s.props[j * 6 + 3]);
            t.setXY(s.props[j * 6], s.props[j * 6 + 1], true);
            t.setVisible(s.props[j * 6 + 5] === 1);
        }
        tick = s.tick; previous = null; commandId = s.commandId;
        seedState = s.seedState; virtualMs = s.virtualMs; collision = {...s.collision};
        lastState = s.lastState ? {...s.lastState} : null; levelIds = s.levelIds.slice();
        run.currentMSecs = virtualMs;
    }

    // Page-side Go-Explore cell archive: cell key -> {snap, tick}. Search bookkeeping only;
    // it never alters physics. A decision holds one pointer offset for `hold` ticks.
    // Frontier states are hold-tested (pointer frozen, then rolled back) so that transient
    // flung/airborne height is not mistaken for retained progress.
    const cells = new Map();
    const frontier = {y: -Infinity, phi: Infinity};
    // Optional geometry potential (offline world map, search guidance only): lower is closer to the goal.
    const phiGrid = {data: null};
    function phiAt(x, y) {
        const g = phiGrid;
        const c = Math.max(0, Math.min(g.W - 1, Math.round((x - g.x0) / g.unit)));
        const r = Math.max(0, Math.min(g.H - 1, Math.round((g.y1 - y) / g.unit)));
        return g.data[r * g.W + c];
    }
    const cellKey = (s, cx, cy) => Math.floor(s.player_world_x / cx) + "," + Math.floor(s.player_world_y / cy);
    function holdTest(ax, ay, o) {
        const tmp = takeSnapshot(), x0 = lastState.player_world_x, y0 = lastState.player_world_y;
        for (let k = 0; k < o.holdTicks && !lastState.dead && !lastState.success; k++) advance(ax, ay, commandId + 1);
        const retained = !lastState.dead && (lastState.player_world_y - y0) > -o.retainDy &&
                         Math.abs(lastState.player_world_x - x0) < o.retainDx;
        applySnapshot(tmp);
        return retained;
    }
    // Retained cells also bucket the hammer configuration (8 angle sectors x near/far) so the
    // frontier keeps diverse hammer/body relationships, which launches depend on.
    function fullKey(cx, cy, retained) {
        let key = cellKey(lastState, cx, cy);
        if (retained) {
            const dx = lastState.hammer_world_x - lastState.player_world_x, dy = lastState.hammer_world_y - lastState.player_world_y;
            const sector = Math.min(7, Math.floor((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI) * 8));
            key += "|R" + sector + (Math.hypot(dx, dy) < 60 ? "n" : "f");
        }
        return key;
    }
    function registerCell(cx, cy, retained) {
        const key = fullKey(cx, cy, retained), old = cells.get(key);
        if (old) {
            if (old.tick <= tick) return null;
            snapshots.delete(old.snap);
        }
        const snap = nextSnapshot++;
        snapshots.set(snap, takeSnapshot());
        cells.set(key, {snap, tick});
        return {key, snap, tick, x: lastState.player_world_x, y: lastState.player_world_y,
                hx: lastState.hammer_world_x, hy: lastState.hammer_world_y, replaced: !!old, retained};
    }
    function noteFrontier() {
        if (lastState.player_world_y > frontier.y) frontier.y = lastState.player_world_y;
        if (phiGrid.data) frontier.phi = Math.min(frontier.phi, phiAt(lastState.player_world_x, lastState.player_world_y));
    }
    function exploreSegment(startSnap, actions, hold, cx, cy, opts) {
        const o = Object.assign({margin: 60, holdTicks: 90, retainDy: 6, retainDx: 12, maxSpeed: 8, every: 1, testAll: false, phiMargin: 150}, opts || {});
        const s = snapshots.get(startSnap);
        if (!s) throw new Error("Unknown snapshot " + startSnap);
        if (!Array.isArray(actions) || actions.length > 5000) throw new Error("Invalid segment");
        applySnapshot(s);
        const found = [];
        let maxY = lastState.player_world_y, dead = false, success = false, decisions = 0, holdTests = 0;
        for (let d = 0; d < actions.length && !dead && !success; d++) {
            const [ax, ay] = actions[d];
            if (!Number.isFinite(ax) || !Number.isFinite(ay)) throw new Error("Non-finite action");
            for (let k = 0; k < hold && !lastState.dead && !lastState.success; k++) advance(ax, ay, commandId + 1);
            decisions = d + 1;
            dead = lastState.dead; success = lastState.success;
            if (lastState.player_world_y > maxY) maxY = lastState.player_world_y;
            if (dead) break;
            if ((d + 1) % o.every !== 0 && d + 1 !== actions.length) continue;
            let retained = false;
            const speed = Math.hypot(lastState.player_vx, lastState.player_vy);
            const near = phiGrid.data
                ? phiAt(lastState.player_world_x, lastState.player_world_y) <= frontier.phi + o.phiMargin
                : lastState.player_world_y >= frontier.y - o.margin;
            if (o.testAll || (speed < o.maxSpeed && near)) {
                const known = cells.get(fullKey(cx, cy, true));
                if (!(known && known.tick <= tick)) {
                    holdTests++;
                    retained = holdTest(ax, ay, o);
                    if (retained) noteFrontier();
                }
            }
            const c = registerCell(cx, cy, retained);
            if (c) {c.d = d + 1; found.push(c);}
        }
        return {found, maxY, dead, success, decisions, holdTests, frontierY: frontier.y, tick,
                x: lastState.player_world_x, y: lastState.player_world_y};
    }

    // Batch rollouts for local trajectory optimisation (CEM/MPPI). From one snapshot, run each
    // candidate decision sequence and return [minDistToGoalBox, endX, endY, dead, maxY, ticks].
    // Search bookkeeping only; the snapshot's state is restored afterwards.
    function rolloutBatch(startSnap, candidates, hold, goal) {
        const s = snapshots.get(startSnap);
        if (!s) throw new Error("Unknown snapshot " + startSnap);
        if (!Array.isArray(candidates) || candidates.length > 512) throw new Error("Invalid candidate batch");
        const out = [];
        for (const actions of candidates) {
            if (!Array.isArray(actions) || actions.length > 600) throw new Error("Invalid candidate");
            applySnapshot(s);
            let minD = Infinity, maxY = lastState.player_world_y, n = 0;
            for (let d = 0; d < actions.length && !lastState.dead && !lastState.success; d++) {
                const ax = actions[d][0], ay = actions[d][1];
                if (!Number.isFinite(ax) || !Number.isFinite(ay)) throw new Error("Non-finite action");
                for (let k = 0; k < hold && !lastState.dead && !lastState.success; k++) {
                    advance(ax, ay, commandId + 1); n++;
                    const x = lastState.player_world_x, y = lastState.player_world_y;
                    const dx = Math.max(goal.x0 - x, 0, x - goal.x1), dy = Math.max(goal.y0 - y, 0, y - goal.y1);
                    const dist = Math.hypot(dx, dy);
                    if (dist < minD) minD = dist;
                    if (y > maxY) maxY = y;
                }
            }
            out.push([minD, lastState.player_world_x, lastState.player_world_y, lastState.dead ? 1 : 0, maxY, n]);
        }
        applySnapshot(s);
        return out;
    }

    window.research = {
        reset, state: () => lastState,
        registerCurrent: (cx, cy, retained) => {
            const c = registerCell(cx, cy, !!retained);
            if (c && retained) noteFrontier();
            return c;
        },
        setPhi: (W, H, x0, y1, unit, data) => {
            phiGrid.data = data ? Float32Array.from(data) : null;
            Object.assign(phiGrid, {W, H, x0, y1, unit}); frontier.phi = Infinity;
            return phiGrid.data ? phiGrid.data.length : 0;
        },
        seedCell: (cx, cy) => {frontier.y = -Infinity; frontier.phi = Infinity; const c = registerCell(cx, cy, true); noteFrontier(); return c;},
        exploreSegment,
        rolloutBatch,
        clearCells: () => {for (const c of cells.values()) snapshots.delete(c.snap); cells.clear(); frontier.y = -Infinity; frontier.phi = Infinity;},
        cellCount: () => cells.size,
        snapshot: () => {const id = nextSnapshot++; snapshots.set(id, takeSnapshot()); return id;},
        restore: id => {
            const s = snapshots.get(id);
            if (!s) throw new Error("Unknown snapshot " + id);
            applySnapshot(s);
            return {...lastState};
        },
        dropSnapshot: id => snapshots.delete(id),
        clearSnapshots: () => snapshots.clear(),
        snapshotCount: () => snapshots.size,
        step: (commands) => {
            if (!Array.isArray(commands) || commands.length > 2400) throw new Error("Invalid command budget");
            const trace = [];
            for (const c of commands) {
                if (![c.x, c.y, c.id].every(Number.isFinite)) throw new Error("Non-finite command");
                if (lastState.dead || lastState.success) break;
                trace.push({...advance(c.x, c.y, c.id, !!c.down)});
            }
            if (!fast) {
                vm.renderer.draw();
                document.getElementById("status").textContent = JSON.stringify(lastState, null, 2);
            }
            return trace;
        },
        metadata: () => ({stageWidth: run.stageWidth, stageHeight: run.stageHeight,
                          targets: run.targets.length, frameRate: run.frameLoop.framerate,
                          skins: Object.keys(vm.renderer._allSkins).length, compiled, fast}),
        stats: () => memo ? memo.stats() : {calls: 0, hits: 0, misses: 0},
        render: () => {
            vm.renderer.dirty = true;
            actualDraw();
            document.getElementById("status").textContent = JSON.stringify(lastState, null, 2);
            return lastState;
        },
        // Real renderer point-hit oracle for validating the terrain descriptor.
        terrain: async (points) => {
            if (!Array.isArray(points) || points.length > 1000) throw new Error("Invalid point budget");
            const skin = vm.renderer.createSVGSkin(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><path fill="black" d="M0 0h1v1H0z"/></svg>',
                [0.5, 0.5]);
            // SVG silhouette generation completes on the browser event loop.
            await new Promise(resolve => setTimeout(resolve, 20));
            const id = vm.renderer.createDrawable("sprite");
            const candidates = run.targets.filter(t => t.getName() === "Level").map(t => t.drawableID);
            vm.renderer.updateDrawableSkinId(id, skin);
            vm.renderer.updateDrawableDirectionScale(id, 90, [100, 100]);
            vm.renderer.updateDrawableVisible(id, true);
            try {
                return points.map(([x, y]) => {
                    vm.renderer.updateDrawablePosition(id, [x - stage("CAMERA X"), y - stage("CAMERA Y")]);
                    return realTouching(id, candidates);
                });
            } finally {
                vm.renderer.destroyDrawable(id, "sprite");
                vm.renderer.destroySkin(skin);
            }
        },
    };
    await reset();
    window.researchReady = true;
})().catch(error => {
    window.researchError = String(error.stack || error);
    document.getElementById("status").textContent = window.researchError;
});

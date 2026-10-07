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
    window.research = {
        reset, state: () => lastState,
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

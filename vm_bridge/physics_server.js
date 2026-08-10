const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Pure-JS global stubs for headless Node environment
if (typeof global.Image === 'undefined') {
  global.Image = class {
    constructor() {
      setTimeout(() => {
        this.width = 360;
        this.height = 270;
        if (typeof this.onload === 'function') this.onload();
      }, 0);
    }
  };
}

if (typeof global.document === 'undefined') {
  global.document = {
    createElement: (tag) => {
      if (tag === 'canvas') {
        return {
          width: 480, height: 360,
          getContext: () => ({ drawImage: () => {}, getImageData: () => ({ data: new Uint8Array(4) }) })
        };
      }
      if (tag === 'img') return new global.Image();
      return {};
    }
  };
}

let virtualMSecs = Date.now();
// Override global Date.now so all Scratch timers measure virtual time
Date.now = function() {
  return Math.floor(virtualMSecs);
};

const VirtualMachine = require('scratch-vm');
const ScratchStorage = require('scratch-storage');

console.log = (...args) => process.stderr.write(args.join(' ') + '\n');
console.warn = (...args) => process.stderr.write(args.join(' ') + '\n');

async function main() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');

  // 1. Direct filesystem asset loader (no fetch/HTTP/data-url issues)
  const storage = new ScratchStorage();
  storage.addHelper({
    load: (assetType, assetId, dataFormat) => {
      const p = path.join(ASSETS_DIR, `${assetId}.${dataFormat}`);
      if (!fs.existsSync(p)) return Promise.resolve(null);
      const buf = fs.readFileSync(p);
      const asset = storage.createAsset(assetType, dataFormat, new Uint8Array(buf), assetId, true);
      return Promise.resolve(asset);
    }
  });

  // 2. Initialize VM with storage and a no-throw stub renderer to satisfy skin dimensions
  const vm = new VirtualMachine();
  vm.attachStorage(storage);

  let nextSkinId = 1;
  let nextDrawableId = 1;
  const skins = new Map();

  let playerDrawableId = null;
  let levelDrawableId = null;
  let hammerDrawableId = null;

  const stubRenderer = {
    createSVGSkin: (svgData, rotationCenter) => {
      const id = nextSkinId++;
      skins.set(id, { size: [360, 270], rotationCenter: rotationCenter || [180, 135] });
      return id;
    },
    createBitmapSkin: (bitmapData, costRes, rotationCenter) => {
      const id = nextSkinId++;
      skins.set(id, { size: [360, 270], rotationCenter: rotationCenter || [180, 135] });
      return id;
    },
    createTextSkin: () => nextSkinId++,
    destroySkin: (skinId) => skins.delete(skinId),
    getSkinSize: (skinId) => {
      const s = skins.get(skinId);
      return s ? s.size : [360, 270];
    },
    getSkinRotationCenter: (skinId) => {
      const s = skins.get(skinId);
      return s ? s.rotationCenter : [180, 135];
    },
    getCurrentSkinSize: (skinId) => {
      const s = skins.get(skinId);
      return s ? s.size : [360, 270];
    },
    createDrawable: () => nextDrawableId++,
    destroyDrawable: () => {},
    updateDrawableSkinId: () => {},
    updateDrawablePosition: () => {},
    updateDrawableVisible: () => {},
    updateDrawableEffect: () => {},
    updateDrawableDirectionScale: () => {},
    getDrawableOrder: () => 0,
    setDrawableOrder: () => {},
    setDrawableOrderSkinID: () => {},
    setLayerGroupOrdering: () => {},
    draw: () => {},
    getBounds: () => ({ left: -240, right: 240, top: 180, bottom: -180, width: 480, height: 360 }),
    getDrawableBounds: () => ({ left: -240, right: 240, top: 180, bottom: -180, width: 480, height: 360 }),
    getFencedPositionOfDrawable: (id, pos) => pos,
    clientPositionToRenderPosition: (pos) => pos,
    pick: () => false,
    extractColor: () => [0, 0, 0, 0],
    getNativeSize: () => [480, 360],
    getBoundsForBubble: () => ({ left: 0, right: 0, top: 0, bottom: 0 }),
    isTouchingColor: () => false,
    isTouchingDrawables: () => false,
  };

  stubRenderer.v2BitmapAdapter = {
    getCanvas: () => global.document.createElement('canvas'),
    importBitmap: () => Promise.resolve([360, 270])
  };

  vm.attachRenderer(stubRenderer);
  vm.runtime.v2BitmapAdapter = stubRenderer.v2BitmapAdapter;

  // Load project.json
  const projectBuffer = fs.readFileSync(path.join(ASSETS_DIR, 'project.json'));
  await vm.loadProject(projectBuffer);

  const run = vm.runtime;

  // Cache drawable IDs for fast collision checking
  run.targets.forEach(t => {
    if (t.getName() === 'Player') playerDrawableId = t.drawableID;
    if (t.getName() === 'Level') levelDrawableId = t.drawableID;
    if (t.getName() === 'Hammer' || t.getName() === 'hammer') hammerDrawableId = t.drawableID;
  });

  // Ensure currentStepTime is set so Sequencer.stepThreads WORK_TIME enables execution without vm.start()
  run.currentStepTime = 1000 / 30;

  // Stub sound primitives AFTER loadProject so they override default audio block handlers
  const noop = () => {};
  run._primitives.sound_seteffectto = noop;
  run._primitives.sound_setvolumeto = noop;
  run._primitives.sound_changeeffectby = noop;
  run._primitives.sound_changevolumeby = noop;
  run._primitives.sound_playuntildone = noop;
  run._primitives.sound_play = noop;
  run._primitives.sound_stopallsounds = noop;

  // 3. Virtual Clock Patching: advance currentMSecs by 33.33ms per manual step
  run.currentMSecs = virtualMSecs;
  if (run.ioDevices && run.ioDevices.clock) {
    const clock = run.ioDevices.clock;
    clock._projectStartTime = virtualMSecs;
    clock.projectTimer = function() {
      return (virtualMSecs - this._projectStartTime) / 1000.0;
    };
  }

  const origStep = run._step.bind(run);
  run._step = function() {
    virtualMSecs += 33.333333; // Advance ~30 TPS frame duration
    run.currentMSecs = virtualMSecs;
    run.redrawRequested = true;
    return origStep();
  };

  // State tracking variables
  let lastCommandId = 0;
  let prevHammerX = undefined;
  let prevHammerY = undefined;
  let prevHammerAngle = undefined;
  let prevContactAge = 0;

  function getStageVar(name) {
    const stage = run.getTargetForStage();
    if (!stage || !stage.variables) return 0;
    const v = Object.values(stage.variables).find(v => v.name === name);
    return v ? Number(v.value) : 0;
  }

  function getSpriteVar(targetName, name) {
    const t = run.targets.find(t => !t.isClone && t.getName() === targetName);
    if (!t) return 0;
    const vars = t.getVariables ? t.getVariables() : t.variables;
    if (!vars) return 0;
    const v = Object.values(vars).find(v => v.name === name);
    return v ? Number(v.value) : 0;
  }

  function gameState(commandIdApplied) {
    const frame_id = getStageVar('FRAME');
    const player_world_x = getStageVar('PLAYER X');
    const player_world_y = getStageVar('PLAYER Y');
    const player_vx = getStageVar('PLAYER SX');
    const player_vy = getStageVar('PLAYER SY');
    const hammer_world_x = getStageVar('HAMMER X');
    const hammer_world_y = getStageVar('HAMMER Y');
    const camera_x = getStageVar('CAMERA X');
    const camera_y = getStageVar('CAMERA Y');
    const hammer_air = getStageVar('HAMMER AIR');

    const hammerTarget = run.targets.find(t => !t.isClone && (t.getName() === 'Hammer' || t.getName() === 'hammer'));
    const hammer_angle = hammerTarget ? hammerTarget.direction : 90;

    const touch_x = getSpriteVar('Player', 'touch x');
    const touch_y = getSpriteVar('Player', 'touch y');
    const touch_flag = (touch_x !== 0 || touch_y !== 0) ? 1 : 0;
    const effort = Math.max(0, Math.min(1, getSpriteVar('Player', 'effort')));

    const hammer_vx = prevHammerX !== undefined ? (hammer_world_x - prevHammerX) : 0;
    const hammer_vy = prevHammerY !== undefined ? (hammer_world_y - prevHammerY) : 0;

    let hammer_angular_velocity = 0;
    if (prevHammerAngle !== undefined) {
      let dAngle = hammer_angle - prevHammerAngle;
      while (dAngle > 180) dAngle -= 360;
      while (dAngle < -180) dAngle += 360;
      hammer_angular_velocity = dAngle;
    }

    // Cache current state for next delta computation
    prevHammerX = hammer_world_x;
    prevHammerY = hammer_world_y;
    prevHammerAngle = hammer_angle;

    const mouse = run.ioDevices.mouse;
    const pointer_screen_x = mouse ? mouse._scratchX : 0;
    const pointer_screen_y = mouse ? mouse._scratchY : 0;

    prevContactAge = touch_flag ? 0 : (prevContactAge + 1);

    return {
      frame_id,
      game_time: run.currentMSecs,
      command_id_applied: commandIdApplied,
      player_world_x,
      player_world_y,
      player_vx,
      player_vy,
      hammer_world_x,
      hammer_world_y,
      hammer_vx,
      hammer_vy,
      camera_x,
      camera_y,
      pointer_screen_x,
      pointer_screen_y,
      hammer_angle,
      hammer_angular_velocity,
      contact_flag: touch_flag,
      contact_point: [touch_x, touch_y],
      contact_normal: [0, 1],
      contact_age: prevContactAge,
      hammer_air,
      effort
    };
  }

  function setMousePointer(nx, ny, isDown) {
    const canvasX = (nx * 0.5 + 0.5) * 480.0;
    const canvasY = (0.5 - ny * 0.5) * 360.0;
    run.ioDevices.mouse.postData({
      x: canvasX,
      y: canvasY,
      canvasWidth: 480,
      canvasHeight: 360,
      isDown: !!isDown
    });
  }

  function checkDeathPulse() {
    const py = getStageVar('PLAYER Y');
    if (py < -180) {
      const kb = run.ioDevices.keyboard;
      if (!kb._keysPressed.includes('space')) {
        kb._keysPressed.push('space');
      }
    }
  }

  function clearKeyPulse() {
    const kb = run.ioDevices.keyboard;
    kb._keysPressed.length = 0;
  }

  function doReset() {
    run.stopAll();
    run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'New Game' });
    const kb = run.ioDevices.keyboard;
    kb._keysPressed.push('space');
    run._step();
    clearKeyPulse();
    for (let i = 0; i < 200; i++) {
      checkDeathPulse();
      run._step();
      clearKeyPulse();
    }
    prevHammerX = undefined;
    prevHammerY = undefined;
    prevHammerAngle = undefined;
    prevContactAge = 0;
  }

  // Initial reset on boot
  doReset();

  // Send ready message
  const readyMsg = JSON.stringify({
    type: 'ready',
    targets: run.targets.length
  });
  process.stdout.write(readyMsg + '\n');

  // JSON-ND IPC loop on stdin
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', (line) => {
    if (!line.trim()) return;
    try {
      const msg = JSON.parse(line);
      if (msg.type === 'reset') {
        doReset();
        const st = gameState(0);
        process.stdout.write(JSON.stringify({ type: 'state', state: st }) + '\n');
      } else if (msg.type === 'step') {
        const cmdId = msg.command_id || (lastCommandId + 1);
        lastCommandId = cmdId;
        const nx = msg.nx !== undefined ? msg.nx : 0;
        const ny = msg.ny !== undefined ? msg.ny : 0;
        const isDown = msg.is_down !== undefined ? msg.is_down : true;
        const nSteps = msg.n_steps || 1;

        setMousePointer(nx, ny, isDown);

        let framesAdvanced = 0;
        for (let s = 0; s < nSteps; s++) {
          checkDeathPulse();
          run._step();
          clearKeyPulse();
          framesAdvanced++;
        }

        const st = gameState(cmdId);
        process.stdout.write(JSON.stringify({
          type: 'state',
          state: st,
          frames_advanced: framesAdvanced
        }) + '\n');
      } else if (msg.type === 'get_var') {
        const val = getStageVar(msg.name);
        process.stdout.write(JSON.stringify({
          type: 'var',
          name: msg.name,
          value: val
        }) + '\n');
      } else if (msg.type === 'set_var') {
        const stage = run.getTargetForStage();
        if (stage && stage.variables) {
          const v = Object.values(stage.variables).find(v => v.name === msg.name);
          if (v) v.value = msg.value;
        }
        process.stdout.write(JSON.stringify({ type: 'ok' }) + '\n');
      } else if (msg.type === 'close') {
        process.exit(0);
      }
    } catch (err) {
      process.stdout.write(JSON.stringify({ type: 'error', error: String(err) }) + '\n');
    }
  });
}

main().catch((err) => {
  console.error('Fatal Physics Server error:', err);
  process.exit(1);
});

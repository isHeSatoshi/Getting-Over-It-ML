# Physics Server Bridge — Complete Design Spec (Updated)

## The core insight

The game "does physics in scripts": the Scratch project computes position, velocity, collisions itself using block math against costume collision data, keeping state in Stage variables (`PLAYER X`, `PLAYER Y`, `HAMMER X`, `HAMMER Y`, `PLAYER SX`, `PLAYER SY`, `HAMMER AIR`). The renderer is not the simulator — it just shows them. So you can simulate the game entirely headlessly by:

1. Running `scratch-vm`'s **Runtime** under Node (not attached to a screen)
2. **Manually calling `_step()`** to advance one frame at a time
3. **Virtual-time clock patching**: overriding `runtime.currentMSecs` / `Date.now` so 33.33ms of game time elapses per `_step()`, bypassing `control_wait` wall-clock throttling.
4. **Injecting input** via the `ioDevices` roundtable (`ioDevices.keyboard`, `ioDevices.mouse`)
5. **Reading state** off `Stage` and `Player` variables each frame

This is a physics server. It replaces the Selenium/Chrome-in-loop path entirely and should be 100–500× faster.

## Non-negotiable Implementation Contracts

### 1. No Renderer, No Audio Engine, No `vm.start()`
```js
const VM = require('scratch-vm');
const vm = new VM();
// Do NOT attachRenderer. Do NOT attachAudioEngine.
// Do NOT call vm.start(). If start() is ever called, immediately clearInterval(vm.runtime._steppingInterval).
```

### 2. Attach Storage with Base64 Data URL Web Store (No Native Dependencies)
```js
const ScratchStorage = require('scratch-storage').ScratchStorage;
const AssetType = require('scratch-storage').AssetType;
const storage = new ScratchStorage();

storage.addWebStore(
  [AssetType.ImageVector, AssetType.ImageBitmap, AssetType.Sound],
  (asset) => {
    const p = path.resolve(__dirname, '../Getting Over It v1/assets', `${asset.assetId}.${asset.dataFormat}`);
    if (!fs.existsSync(p)) return null;
    const buf = fs.readFileSync(p);
    const mime = asset.dataFormat === 'svg' ? 'image/svg+xml'
               : asset.dataFormat === 'png' ? 'image/png'
               : asset.dataFormat === 'wav' ? 'audio/wav'
               : asset.dataFormat === 'mp3' ? 'audio/mpeg'
               : 'application/octet-stream';
    return `data:${mime};base64,` + buf.toString('base64');
  }
);
vm.attachStorage(storage);
```
Dependencies must ONLY be `scratch-vm@5.0.300` and `scratch-storage`. Do NOT include `canvas` or native node-gyp modules.

### 3. Virtual Clock Patch & Manual Step Driving
The game's inner thread calls `control_wait` (~33ms) per frame. Microsecond manual steps will cause `control_wait` to never expire in real-time. We patch virtual time:

```js
const run = vm.runtime;
let virtualMSecs = Date.now();

// Override time provider so control_wait expires deterministically:
run.currentMSecs = virtualMSecs;
const origStep = run._step.bind(run);
run._step = function() {
  virtualMSecs += 33.333; // Advance ~30 TPS frame duration
  run.currentMSecs = virtualMSecs;
  run.redrawRequested = true;
  return origStep();
};
```

### 4. Input Injection & Screen Pointer Conversion
Convert normalized pointer coordinates `[-1, 1]` to canvas pixel coordinates `[0, 480]` and `[0, 360]`:
```js
function setMouse(nx, ny, isDown) {
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
```

Spacebar key pulse for respawn/unblock:
```js
run.ioDevices.keyboard._keysPressed.push('space');
// After tick:
run.ioDevices.keyboard._keysPressed.length = 0;
```

### 5. Reset & Episode Semantics
```js
run.stopAll();
run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'New Game' });
run.ioDevices.keyboard._keysPressed.push('space');
run._step();
run.ioDevices.keyboard._keysPressed.length = 0;
for (let i = 0; i < 200; i++) {
  run._step();
}
```

### 6. Subprocess IPC & Stderr Draining
- Python process must open the Node child with `stderr=subprocess.DEVNULL` or pipe to log file to prevent OS buffer deadlocks caused by `scratch-vm` warning logs.
- Node process reads stdin line-by-line using `readline` and responds with single-line JSON to stdout.

### 7. Environment Target Fixes
- Target summit height `success_y = 16000.0`.
- Track decision-start altitude for setback calculation.
- Prevent fall-budget double-fire.

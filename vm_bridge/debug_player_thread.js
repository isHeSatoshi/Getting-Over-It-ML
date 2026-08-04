const fs = require('fs');
const path = require('path');

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
Date.now = function() {
  return Math.floor(virtualMSecs);
};

const VirtualMachine = require('scratch-vm');
const ScratchStorage = require('scratch-storage');

async function debug() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');
  const storage = new ScratchStorage();
  storage.addHelper({
    load: (assetType, assetId, dataFormat) => {
      const p = path.join(ASSETS_DIR, `${assetId}.${dataFormat}`);
      if (!fs.existsSync(p)) return Promise.resolve(null);
      const buf = fs.readFileSync(p);
      return Promise.resolve(storage.createAsset(assetType, dataFormat, new Uint8Array(buf), assetId, true));
    }
  });

  const vm = new VirtualMachine();
  vm.attachStorage(storage);

  let nextSkinId = 1;
  let nextDrawableId = 1;
  const skins = new Map();

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
    getSkinSize: (skinId) => [360, 270],
    getSkinRotationCenter: (skinId) => [180, 135],
    getCurrentSkinSize: (skinId) => [360, 270],
    createDrawable: () => nextDrawableId++,
    destroyDrawable: () => {},
    updateDrawableSkinId: () => {},
    updateDrawablePosition: () => {},
    updateDrawableVisible: () => {},
    updateDrawableEffect: () => {},
    updateDrawableDirectionScale: () => {},
    getDrawableOrder: () => 0,
    setDrawableOrderSkinID: () => {},
    setLayerGroupOrdering: () => {},
    draw: () => {},
    getBounds: () => ({ left: -240, right: 240, top: 180, bottom: -180, width: 480, height: 360 }),
    getDrawableBounds: () => ({ left: -240, right: 240, top: 180, bottom: -180, width: 480, height: 360 }),
    clientPositionToRenderPosition: (pos) => pos,
    pick: () => false,
    extractColor: () => [0, 0, 0, 0],
    getNativeSize: () => [480, 360],
    getFencedPositionOfDrawable: (id, pos) => pos,
    getBoundsForBubble: () => ({ left: 0, right: 0, top: 0, bottom: 0 }),
    isTouchingColor: () => false,
    isTouchingDrawables: () => false,
    drawableTouching: () => false,
    penClear: () => {},
    penDrawLine: () => {},
    penPoint: () => {}
  };

  stubRenderer.v2BitmapAdapter = {
    getCanvas: () => global.document.createElement('canvas'),
    importBitmap: () => Promise.resolve([360, 270])
  };

  vm.attachRenderer(stubRenderer);
  vm.runtime.v2BitmapAdapter = stubRenderer.v2BitmapAdapter;

  const projectBuffer = fs.readFileSync(path.join(ASSETS_DIR, 'project.json'));
  await vm.loadProject(projectBuffer);

  const run = vm.runtime;
  run.currentMSecs = virtualMSecs;
  if (run.ioDevices && run.ioDevices.clock) {
    run.ioDevices.clock._projectStartTime = virtualMSecs;
    run.ioDevices.clock.projectTimer = function() {
      return (virtualMSecs - this._projectStartTime) / 1000.0;
    };
  }

  const origStep = run._step.bind(run);
  run._step = function() {
    virtualMSecs += 33.333333;
    run.currentMSecs = virtualMSecs;
    run.redrawRequested = true;
    return origStep();
  };

  run.stopAll();
  run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'New Game' });
  run.ioDevices.keyboard._keysPressed.push('space');
  run._step();
  run.ioDevices.keyboard._keysPressed.length = 0;

  const playerThread = run.threads.find(t => t.target && t.target.getName() === 'Player');
  console.log("Player thread stack before step:", playerThread.stack);

  // Step and log executed blocks inside Player thread
  for (let s = 1; s <= 5; s++) {
    console.log(`\n--- Step ${s} ---`);
    console.log("Stack top:", playerThread.peekStack(), "status:", playerThread.status);
    run._step();
  }
}

debug().catch(console.error);

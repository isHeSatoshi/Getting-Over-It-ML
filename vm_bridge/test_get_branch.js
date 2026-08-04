const fs = require('fs');
const path = require('path');
const VirtualMachine = require('scratch-vm');

async function test() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');
  const vm = new VirtualMachine();
  await vm.loadProject(fs.readFileSync(path.join(ASSETS_DIR, 'project.json')));

  const player = vm.runtime.targets.find(t => t.getName() === 'Player');
  console.log("lc block:", player.blocks.getBlock('lc'));
  console.log("getBranch('lc', 1):", player.blocks.getBranch('lc', 1));
}

test().catch(console.error);

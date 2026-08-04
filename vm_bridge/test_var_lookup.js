const fs = require('fs');
const path = require('path');
const VirtualMachine = require('scratch-vm');

async function test() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');
  const vm = new VirtualMachine();
  await vm.loadProject(fs.readFileSync(path.join(ASSETS_DIR, 'project.json')));

  const run = vm.runtime;
  const stage = run.getTargetForStage();
  const player = run.targets.find(t => t.getName() === 'Player');

  const varId = "(h/zA+h*`trBdxt,jtOV"; // FRAME id
  console.log("Stage var by ID:", stage.variables[varId]);
  console.log("Player var by ID:", player.variables[varId]);
  console.log("Player lookupVariableById:", player.lookupVariableById(varId));
}

test().catch(console.error);

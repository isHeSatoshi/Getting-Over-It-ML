const fs = require('fs');
const path = require('path');
const VirtualMachine = require('scratch-vm');

async function test() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');
  const vm = new VirtualMachine();
  await vm.loadProject(fs.readFileSync(path.join(ASSETS_DIR, 'project.json')));

  const run = vm.runtime;
  
  console.log("1. startHats with BROADCAST_OPTION='New Game':", run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'New Game' }).length);
  console.log("2. startHats with BROADCAST_OPTION='new game':", run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'new game' }).length);
  console.log("3. startHats with BROADCAST_OPTION='JyyW3(Ci,45B:9I_qvBl':", run.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'JyyW3(Ci,45B:9I_qvBl' }).length);
  console.log("4. startHats without optMatch:", run.startHats('event_whenbroadcastreceived').length);
}

test().catch(console.error);

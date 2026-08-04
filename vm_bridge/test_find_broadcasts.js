const fs = require('fs');
const path = require('path');
const VirtualMachine = require('scratch-vm');

async function test() {
  const ASSETS_DIR = path.resolve(__dirname, '../Getting Over It v1/assets');
  const vm = new VirtualMachine();
  const projectBuffer = fs.readFileSync(path.join(ASSETS_DIR, 'project.json'));
  await vm.loadProject(projectBuffer);

  const run = vm.runtime;
  
  console.log("Searching for broadcast hats:");
  run.targets.forEach(t => {
    Object.values(t.blocks._blocks).forEach(b => {
      if (b.opcode === 'event_whenbroadcastreceived') {
        console.log(`Target ${t.getName()}: block ${b.id}, BROADCAST_OPTION=${JSON.stringify(b.fields.BROADCAST_OPTION)}`);
      }
    });
  });
}

test().catch(console.error);

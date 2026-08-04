const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Running npm install script in', __dirname);
try {
  const out = execSync('npm.cmd install scratch-vm@0.2.0-prerelease.20230307165039 scratch-storage@2.3.0', {
    cwd: __dirname,
    encoding: 'utf8'
  });
  console.log('OUTPUT:', out);
} catch (err) {
  console.error('ERROR:', err.stdout, err.stderr);
}

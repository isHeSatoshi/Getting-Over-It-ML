import subprocess
import sys
import os

print("Starting npm install process...")
sys.stdout.flush()

cmd = "npm install scratch-vm@5.0.300 scratch-storage@2.3.0 --no-audit --no-fund"
proc = subprocess.Popen(
    cmd,
    shell=True,
    cwd=os.path.dirname(os.path.abspath(__file__)),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

for line in proc.stdout:
    print(line, end="")
    sys.stdout.flush()

proc.wait()
print(f"\nNPM finished with code: {proc.returncode}")

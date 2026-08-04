# Getting Over It — High-Speed Headless Node.js Physics Bridge & Reinforcement Learning Environment

A ultra-fast, headless **Scratch VM Physics Server Bridge** and **Gymnasium RL Environment** for Bennett Foddy's *Getting Over It* (Scratch Edition).

By executing `scratch-vm` headlessly under Node.js with virtual clock patching, this bridge achieves simulation throughput of **>750 to 4,500+ physics steps per second** without display overhead or native browser rendering constraints.

---

## 🏗️ Core Architecture & Features

1. **Headless Node.js Physics Server (`vm_bridge/physics_server.js`)**:
   - Executes Scratch 3.0 Runtime headlessly under Node.js without a screen or visual canvas renderer.
   - Advances game physics microstep-by-microstep via `_step()` calls.
   - Overrides `Date.now()` and `ioDevices.clock` to advance virtual game time by ~33.33ms per step, eliminating real-world wall-clock throttling.
   - Employs direct filesystem asset loading for SVG/PNG costumes and stubbed audio primitives to prevent promise-lock thread stalls.

2. **Python Subprocess IPC Bridge (`vm_bridge/node_bridge.py`)**:
   - Launches the Node.js server via `subprocess.Popen` with non-blocking line-delimited JSON IPC over stdin/stdout.
   - Delivers accurate real-time telemetry (player position, velocity, hammer angle, contact age, effort, camera offset, stage variables).

3. **Gymnasium RL Environment (`GettingOverItEnv.py`)**:
   - Standard Gymnasium API (`reset()`, `step()`, `render()`, `close()`).
   - Normalizes continuous mouse actions `[-1, 1]` to canvas coordinates.
   - Provides comprehensive observation space (200-dim vector including spatial history, velocities, contact flags, and haptic delta metrics).
   - Features automatic death-unblocking space pulse handling.

---

## 📂 Repository Structure

```
.
├── Getting Over It v1/       # Game assets and project.json (Scratch project directory)
├── vm_bridge/
│   ├── physics_server.js     # High-speed headless Node.js Scratch VM physics engine
│   ├── node_bridge.py        # Python IPC wrapper for Node physics server
│   ├── package.json          # Node.js dependencies (scratch-vm, scratch-storage, etc.)
│   └── PHYSICS_SERVER_BRIDGE_SPEC.md  # Detailed system architecture specification
├── GettingOverItEnv.py       # Gymnasium Environment for RL training
├── train_ppo.py              # PPO training pipeline using Stable-Baselines3
├── StaticCollisionMap.py     # Static terrain collision extractor & visualizer
├── test_node_bridge.py       # Test suite for NodeBridge and Gym environment
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **Node.js**: v18.x or later
- **Python**: 3.10 or 3.11

### 1. Install Node.js Dependencies
Navigate to the `vm_bridge` directory and install the required Scratch VM packages:

```bash
cd vm_bridge
npm install scratch-vm@5.0.300 scratch-storage@2.3.0 ajv@6.12.6 jszip entities format-message htmlparser2 scratch-svg-renderer scratch-render scratch-audio isomorphic-dompurify jsdom --no-audit
cd ..
```

### 2. Install Python Dependencies
Install Python package requirements:

```bash
pip install -r requirements.txt
```

---

## 🧪 Running Verification Tests

Run the full integration test suite to verify the Node bridge, virtual clock advancement, reset mechanics, and Gymnasium environment compatibility:

```bash
python test_node_bridge.py
```

Expected Output:
```
==================================================
1. Testing NodeBridge Standalone & Virtual Clock
==================================================
[NodeBridge] Physics Server ready! (27 targets loaded)
500 steps completed in 0.64s (779.2 steps/sec)
[SUCCESS] Virtual clock patch verified! FRAME advanced properly.

--------------------------------------------------
2. Testing Death-Unblock Space Pulse & Reset
--------------------------------------------------
State after reset: FRAME=201, PLAYER Y=21.00
[SUCCESS] Episode reset verified!

==================================================
3. Testing Gymnasium GettingOverItEnv Integration
==================================================
[RESET] Resetting env...
Env reset successful. Observation shape: (200,)
100 decision steps (400 physics ticks) in 3.78s
[SUCCESS] Gymnasium env integration test passed successfully!
```

---

## 🚀 Training an RL Agent (PPO)

To launch reinforcement learning training using Stable-Baselines3 PPO:

```bash
python train_ppo.py
```

---

## 📜 License

This project is open-source and intended for academic research and reinforcement learning experimentation.

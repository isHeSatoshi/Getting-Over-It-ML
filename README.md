# 🧗 Getting Over It — High-Speed Headless Node.js Physics Bridge & Reinforcement Learning Environment

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Node.js v18+](https://img.shields.io/badge/node.js-v18%2B-green.svg)](https://nodejs.org/)
[![Gymnasium](https://img.shields.io/badge/gymnasium-v0.29%2B-informational.svg)](https://gymnasium.farama.org/)
[![Stable-Baselines3](https://img.shields.io/badge/SB3--contrib-RecurrentPPO-orange.svg)](https://github.com/Stable-Baselines-Team/stable-baselines3-contrib)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An ultra-fast, headless **Scratch VM Physics Server Bridge** and **Gymnasium Reinforcement Learning Environment** for Bennett Foddy's *Getting Over It* (Scratch Edition, ID: 389464290).

By executing `scratch-vm` headlessly under Node.js with virtual clock patching, this framework achieves simulation throughput of **>750 to 4,500+ physics steps per second** — completely eliminating display overhead and native browser rendering bottlenecks.

---

## 📐 Architecture & System Overview

The system is decoupled into three high-performance layers: a headless JavaScript physics worker, a low-latency Python IPC wrapper, and a Gymnasium-compliant RL environment powered by Recurrent PPO (LSTM).

```mermaid
flowchart TD
    subgraph Headless Engine [Layer 1: Node.js Physics Worker]
        JS[physics_server.js] -->|Scratch 3.0 VM Runtime| VM[Virtual Clock & Math Engine]
        VM -->|Overridden Date.now / ioDevices.clock| STEP[_step microsteps]
    end

    subgraph Python IPC [Layer 2: Communication Bridge]
        STEP <-->|JSON IPC via Stdin/Stdout| PY_BRIDGE[node_bridge.py]
    end

    subgraph RL Environment [Layer 3: Gymnasium & Training]
        PY_BRIDGE <-->|200-dim Obs State & Normalized Control| ENV[GettingOverItEnv.py]
        ENV <-->|SubprocVecEnv 8 Parallel Workers| PPO[train_ppo.py - Recurrent PPO / LSTM]
    end

    subgraph Diagnostics & Visualization
        PPO -->|Model Weights| EVAL[visualize_policy.py / Headed Chrome]
        PPO -->|Real-Time Telemetry| STREAM[live_stream_policy.py / HTTP Server :8080]
        ENV -->|Collision Contours| HAPTIC[generate_haptic_graph.py / StaticCollisionMap.py]
    end
```

---

## 🌟 Key Features

1. **Headless Node.js Physics Engine (`vm_bridge/physics_server.js`)**:
   - Executes Scratch 3.0 Runtime headlessly under Node.js without GUI canvas or WebGL rendering overhead.
   - Advances game physics microstep-by-microstep via internal `_step()` calls.
   - Patches `Date.now()` and `ioDevices.clock` to advance virtual game time by ~33.33ms per step, removing real-world wall-clock delays.
   - Uses direct filesystem asset loading for SVG/PNG costumes and stubbed audio primitives to prevent promise-lock thread stalls.

2. **Subprocess IPC Bridge (`vm_bridge/node_bridge.py`)**:
   - Spawns and manages Node.js processes via `subprocess.Popen` using non-blocking line-delimited JSON IPC.
   - Exposes comprehensive real-time telemetry: player coordinates $(X, Y)$, linear velocities $(\dot{X}, \dot{Y})$, hammer angle/angular velocity, contact state, Effort metrics, camera offsets, and stage variables.

3. **Gymnasium RL Environment (`GettingOverItEnv.py`)**:
   - Standard Gymnasium API (`reset()`, `step()`, `render()`, `close()`).
   - Action Space: Continuous 2D target `[-1, 1]` mapped to target Scratch canvas coordinates.
   - Observation Space: 200-dimensional vector incorporating spatial positions, historical movement vectors, terrain raycasts, contact age metrics, and haptic delta signatures.
   - Automatic Space-Pulse recovery for clearing Scratch game intro screens and respawn locks.

4. **PMDP Reward Shaping Redesign**:
   - **Zero-Based Potential**: $\Phi(s) = (Y - Y_{\text{spawn}}) \times 0.01$, eliminating spawn-camping exploits.
   - **Milestone High-Water Mark**: Progressive rewards paid on new altitude gains to encourage active exploration up to the summit ($Y = 16,000$).
   - **Overhead Ledge Alignment**: Bonus rewards for directing the hammer toward hookable overhead terrain.
   - **Stall Truncation**: 300-frame episode budget without altitude gain to prevent getting stuck in local optima.
   - **Respawn Detection**: Instant penalty for falling back to the starting water.

5. **Recurrent PPO Training Pipeline (`train_ppo.py`)**:
   - Implemented via `sb3_contrib.RecurrentPPO` using an `MlpLstmPolicy` with orthogonal initialization.
   - Parallelized across 8 Node physics workers using `SubprocVecEnv` tuned for multi-core CPUs (e.g., Intel i7-12700K).
   - Automated Chrome profile lock cleanup and multi-port allocation (ports 8001–8008).

6. **Visualization & Telemetry Suite**:
   - **Live HTTP Web Streamer (`live_stream_policy.py`)**: Broadcasts live AI actions to a browser tab via port 8080.
   - **Headed Browser Evaluator (`visualize_policy.py`)**: Visual evaluation in a rendered Chrome window.
   - **Terrain & Haptic Analytics (`StaticCollisionMap.py`, `generate_haptic_graph.py`)**: Collision contour extraction and contact force plotting.

---

## 🎯 Reward Function Contract

### Formulation

$$\text{Reward}_t = \sum_{k} \left[ 0.99 \cdot \Phi(s_{t+1}) - \Phi(s_t) + r_{\text{time}} + r_{\text{contact}} + r_{\text{hook}} \right] + R_{\text{milestone}} - R_{\text{smooth}} + R_{\text{terminal}}$$

| Component | Value / Formula | Description |
| :--- | :--- | :--- |
| **Zero-Based Potential** $\Phi(s)$ | $(Y - Y_{\text{spawn}}) \times 0.01$ | Altitude gain relative to spawn; stationary at spawn yields $0$ reward. |
| **Time Penalty** $r_{\text{time}}$ | $-0.01$ per frame | Discourages idling. |
| **Contact Bonus** $r_{\text{contact}}$ | $+0.002$ per frame | Active terrain contact reward. |
| **Hook Alignment** $r_{\text{hook}}$ | $+0.02$ per frame | Reward when hammer angle aligns with overhead ledges ($\cos \theta \ge 0.5$). |
| **Milestone Bonus** $R_{\text{milestone}}$ | $0.5 \times \Delta Y_{\text{new\_high}}$ | Paid only on first-time altitude high-water mark crossings. |
| **Smoothness Penalty** $R_{\text{smooth}}$ | $-0.005 \times \|a_t - a_{t-1}\|$ | Penalizes erratic mouse jitter. |
| **Respawn Penalty** | $-5.0$ | Applied if $Y$ drops $>100$ in one decision window (water fall). |
| **Summit Bonus** | $+100.0$ | Applied when player reaches $Y \ge 16,000$. |

---

## 📂 Repository Structure

```
.
├── Getting Over It v1/                 # Scratch project directory & assets
│   ├── project.json                    # Scratch 3.0 target scripts & physics definitions
│   └── live_action.json                # Live action telemetry stream buffer
├── vm_bridge/                          # Layer 1 & 2: Physics Server & IPC Bridge
│   ├── physics_server.js               # Headless Scratch VM runner with virtual clock patch
│   ├── node_bridge.py                  # Python IPC subprocess wrapper
│   ├── package.json                    # Node dependencies (scratch-vm, jsdom, etc.)
│   └── PHYSICS_SERVER_BRIDGE_SPEC.md   # Headless bridge architectural specification
├── GettingOverItEnv.py                 # Layer 3: Gymnasium RL Environment & PMDP Config
├── train_ppo.py                        # Parallel Recurrent PPO (LSTM) training script
├── visualize_policy.py                 # Headed Chrome policy evaluation tool
├── live_stream_policy.py               # Real-time HTTP web streaming policy visualizer
├── StaticCollisionMap.py               # Static terrain collision map extractor
├── generate_haptic_graph.py            # Haptic collision data visualization tool
├── test_node_bridge.py                 # Verification test suite for bridge & Gym env
├── test_reward_math.py                 # Unit tests for reward shaping math
├── REWARD_FIX_NOTES.md                 # Detailed design document for reward function redesign
├── requirements.txt                    # Python package dependencies
└── README.md                           # System documentation
```

---

## ⚙️ Installation & Prerequisites

### Requirements
- **Node.js**: v18.x or later
- **Python**: 3.10 or 3.11
- **CUDA-compatible GPU** (Recommended for Recurrent PPO training)

### 1. Install Node.js Dependencies
Navigate to the `vm_bridge` directory and install the required Scratch VM packages:

```bash
cd vm_bridge
npm install scratch-vm@5.0.300 scratch-storage@2.3.0 ajv@6.12.6 jszip entities format-message htmlparser2 scratch-svg-renderer scratch-render scratch-audio isomorphic-dompurify jsdom --no-audit
cd ..
```

### 2. Install Python Dependencies
Install Python requirements:

```bash
pip install -r requirements.txt
```

---

## 🧪 Verification & Testing

Before launching RL training, verify the physics server bridge, virtual clock advancement, and reward math:

```bash
# 1. Run Node.js Bridge & Gym Integration Tests
python test_node_bridge.py

# 2. Run Reward Math & Potential Function Tests
python test_reward_math.py
```

### Expected Output (`test_node_bridge.py`)
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

## 🚀 Workflows & Execution Guide

### 1. Train Recurrent PPO Agent
To launch multi-process RL training across 8 parallel headless physics servers:

```bash
python train_ppo.py
```

To resume training from an existing model checkpoint:
```powershell
$env:RESUME_CHECKPOINT = "./models/recurrent_ppo_gettingoverit_131072_steps.zip"
python train_ppo.py
```

### 2. Monitor Training with TensorBoard
Track reward growth, episode lengths, and policy entropy:

```bash
tensorboard --logdir ./ppo_tensorboard/
```

### 3. Evaluate Policy in Headed Browser
Watch the trained policy play in a rendered Chrome window:

```bash
python visualize_policy.py
```

### 4. Watch Live AI Playback via Web Browser
Stream live action telemetry from the headless engine to any modern browser:

```bash
python live_stream_policy.py
```
*Open `http://127.0.0.1:8080` in your browser to view live agent interaction.*

### 5. Generate Terrain & Haptic Analytics
Extract static terrain contours and analyze collision forces:

```bash
# Extract static collision map geometry
python StaticCollisionMap.py

# Generate haptic collision graphs
python generate_haptic_graph.py
```

---

## ⚡ Performance Benchmarks

| Metric | Headless Node.js Physics Bridge | Standard Browser (Selenium/Chrome) |
| :--- | :--- | :--- |
| **Throughput** | **750 – 4,500+ steps/sec** | ~60 steps/sec |
| **Rendering Overhead** | **0% (Headless Virtual Clock)** | High (Canvas / WebGL / Audio) |
| **Multi-Worker Scaling** | **Linear across CPU P-cores** | Heavy memory/CPU footprint |
| **Clock Fidelity** | **Deterministic microstep advances** | Throttled by browser event loop |

---

## 📜 License & Citation

This repository is open-source under the **MIT License** and is intended for academic research in reinforcement learning, continuous control, and simulation engineering.

If you use this work in your research, please cite:

```bibtex
@software{getting_over_it_ml_2026,
  author = {AdityaProCoder},
  title = {Getting Over It — High-Speed Headless Node.js Physics Bridge & Reinforcement Learning Environment},
  year = {2026},
  url = {https://github.com/AdityaProCoder/Getting-Over-It-ML}
}
```

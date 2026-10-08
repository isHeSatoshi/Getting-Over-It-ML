/* Persistent loopback RPC. Authentication is ephemeral and never persisted. */
"use strict";
(async () => {
    const fragment = new URLSearchParams(location.hash.slice(1));
    const port = Number(fragment.get("rpc_port"));
    const token = fragment.get("rpc_token");
    if (!port || !token) return;
    // Remove credentials from the address bar and subsequent screenshots.
    history.replaceState(null, "", location.pathname + location.search);
    if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid RPC endpoint");
    while (!window.researchReady && !window.researchError) {
        await new Promise(resolve => setTimeout(resolve, 10));
    }
    if (window.researchError) throw new Error(window.researchError);
    const socket = new WebSocket("ws://127.0.0.1:" + port);
    let serial = Promise.resolve();
    socket.onopen = () => socket.send(JSON.stringify({token}));
    socket.onmessage = event => {
        serial = serial.then(async () => {
            const request = JSON.parse(event.data);
            try {
                let value;
                if (request.method === "step") value = research.step(request.commands, request.after);
                else if (request.method === "reset") value = await research.reset(request.seed);
                else if (request.method === "state") value = research.state();
                else if (request.method === "snapshot") value = research.snapshot();
                else if (request.method === "restore") value = research.restore(request.snapshot);
                else if (request.method === "drop_snapshot") value = research.dropSnapshot(request.snapshot);
                else if (request.method === "seed_cell") value = research.seedCell(request.cx, request.cy);
                else if (request.method === "explore_segment") value = research.exploreSegment(
                    request.snapshot, request.actions, request.hold, request.cx, request.cy, request.opts);
                else if (request.method === "register_current") value = research.registerCurrent(request.cx, request.cy, request.retained);
                else if (request.method === "rollout_batch") value = research.rolloutBatch(request.snapshot, request.candidates, request.hold, request.goal);
                else if (request.method === "set_phi") value = research.setPhi(request.W, request.H, request.x0, request.y1, request.unit, request.data);
                else if (request.method === "clear_cells") value = research.clearCells();
                else if (request.method === "evaluate") value = await (0, eval)(request.expression);
                else throw new Error("Unknown RPC method");
                socket.send(JSON.stringify({id: request.id, value: value === undefined ? null : value}));
            } catch (error) {
                socket.send(JSON.stringify({id: request.id, error: String(error.stack || error)}));
            }
        });
    };
})().catch(error => {window.researchRpcError = String(error.stack || error);});

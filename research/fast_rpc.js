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
                if (request.method === "step") value = research.step(request.commands);
                else if (request.method === "reset") value = await research.reset(request.seed);
                else if (request.method === "state") value = research.state();
                else if (request.method === "evaluate") value = await (0, eval)(request.expression);
                else throw new Error("Unknown RPC method");
                socket.send(JSON.stringify({id: request.id, value: value === undefined ? null : value}));
            } catch (error) {
                socket.send(JSON.stringify({id: request.id, error: String(error.stack || error)}));
            }
        });
    };
})().catch(error => {window.researchRpcError = String(error.stack || error);});

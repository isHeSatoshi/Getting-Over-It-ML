/* Exact-query memoization, never rounded coordinates or replacement physics.
 * Scope is one synchronous VM tick, so asynchronous skin changes cannot occur.
 */
"use strict";
(function (root) {
    function createMemo(renderer, getPlayer) {
        const identities = new WeakMap();
        let nextIdentity = 1, levelSignature = null, levels = null;
        const cache = new Map();
        const stats = {calls: 0, hits: 0, misses: 0};
        function identity(object) {
            if (!object || typeof object !== "object") throw new Error("Missing collision skin");
            if (!identities.has(object)) identities.set(object, nextIdentity++);
            return identities.get(object);
        }
        function signature(id) {
            const d = renderer._allDrawables[id];
            if (!d || !d._position || !d._scale || !d._skin) throw new Error("Unsupported drawable geometry");
            const u = d._uniforms || {};
            return [id, identity(d._skin), ...d._position, ...d._scale, d._direction, d._visible,
                    d.enabledEffects, ...["u_color", "u_fisheye", "u_whirl", "u_pixelate",
                                         "u_mosaic", "u_brightness", "u_ghost"].map(k => u[k])];
        }
        const original = renderer.isTouchingDrawables.bind(renderer);
        // Any Level transform/skin/effect change invalidates candidate geometry.
        for (const name of ["updateDrawablePosition", "updateDrawableSkinId", "updateDrawableVisible",
                            "updateDrawableDirectionScale", "updateDrawableDirection", "updateDrawableScale",
                            "updateDrawableEffect", "updateDrawableProperties", "destroyDrawable"]) {
            if (typeof renderer[name] !== "function") continue;
            const update = renderer[name].bind(renderer);
            renderer[name] = function (id, ...args) {
                if (levels && levels.has(id)) {
                    levelSignature = null;
                    cache.clear();
                }
                return update(id, ...args);
            };
        }
        renderer.isTouchingDrawables = function (id, candidates) {
            const player = getPlayer();
            if (!player || id !== player.drawableID || !levels ||
                candidates.some(candidate => !levels.has(candidate))) {
                return original(id, candidates);
            }
            const costume = player.getCostumes()[player.currentCostume].name;
            if (costume !== "player hitbox" && costume !== "hammer hitbox") return original(id, candidates);
            stats.calls++;
            if (levelSignature === null) {
                levelSignature = JSON.stringify([
                    renderer.getNativeSize(), [...levels].map(signature)
                ]);
            }
            const key = JSON.stringify([signature(id), candidates, levelSignature]);
            if (cache.has(key)) {
                stats.hits++;
                return cache.get(key);
            }
            stats.misses++;
            const result = original(id, candidates);
            if (cache.size < 4096) cache.set(key, result);
            return result;
        };
        return {
            beginTick(ids) {
                levels = new Set(ids);
                cache.clear();
                levelSignature = null;
            },
            resetStats() { for (const key of Object.keys(stats)) stats[key] = 0; },
            stats: () => ({...stats}),
        };
    }
    root.ResearchCollisionMemo = {createMemo};
    if (typeof module !== "undefined") module.exports = {createMemo};
})(typeof window !== "undefined" ? window : globalThis);

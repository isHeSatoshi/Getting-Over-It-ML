"use strict";
const assert = require("node:assert/strict");
const {createMemo} = require("../research/collision_memo.js");
function drawable(x = 0) {
    return {_position: [x, 0, 0], _scale: [100, 100, 0], _direction: 90,
            _visible: true, enabledEffects: 0, _uniforms: {}, _skin: {}};
}
let calls = 0;
const renderer = {
    _allDrawables: [drawable(), drawable(5)],
    getNativeSize: () => [480, 360],
    isTouchingDrawables: () => {calls++; return renderer._allDrawables[0]._position[0] >= renderer._allDrawables[1]._position[0];},
    updateDrawablePosition(id, position) {this._allDrawables[id]._position = [...position, 0];},
    updateDrawableSkinId(id, skin) {this._allDrawables[id]._skin = skin;},
    updateDrawableVisible(id, value) {this._allDrawables[id]._visible = value;},
    updateDrawableEffect(id, key, value) {this._allDrawables[id]._uniforms[key] = value;},
};
const player = {drawableID: 0, currentCostume: 0, getCostumes: () => [{name: "player hitbox"}]};
const memo = createMemo(renderer, () => player);
memo.beginTick([1]);
assert.equal(renderer.isTouchingDrawables(0, [1]), false);
assert.equal(renderer.isTouchingDrawables(0, [1]), false);
assert.equal(calls, 1);
// No rounding: even a tiny transform change must trigger a fresh query.
renderer.updateDrawablePosition(0, [1e-12, 0]);
renderer.isTouchingDrawables(0, [1]);
assert.equal(calls, 2);
renderer.updateDrawablePosition(1, [-1, 0]);
assert.equal(renderer.isTouchingDrawables(0, [1]), true);
assert.equal(calls, 3);
renderer.updateDrawableSkinId(1, {});
renderer.isTouchingDrawables(0, [1]);
assert.equal(calls, 4);
renderer.updateDrawableEffect(1, "u_ghost", 1);
renderer.isTouchingDrawables(0, [1]);
assert.equal(calls, 5);
memo.beginTick([1]);
renderer.isTouchingDrawables(0, [1]);
assert.equal(calls, 6);
console.log("Exact collision memo invalidation tests passed");

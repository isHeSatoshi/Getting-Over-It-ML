"use strict";
const assert = require("node:assert/strict");
const {install, LIMIT, CODES} = require("../research/procedure_counter.js");
const code = Object.keys(CODES)[0], key = "W" + code;
let tests = 0;
function test(name, body) {body(); tests++; console.log("Passed:", name);}
function fixture(procedures = {}) {
    const runtime = {compilerOptions: {enabled: true}, threads: [],
        _step(value) {return value;}};
    const target = {runtime, isOriginal: true, getName() {return "Player";}};
    class Thread {
        constructor(p = procedures, t = target) {this.target = t; this.isCompiled = true; this.procedures = p;}
        tryCompile(p) {this.procedures = p; this.isCompiled = true; return "compiled";}
    }
    const thread = new Thread();
    runtime.threads.push(thread);
    return {runtime, target, Thread, thread};
}

test("Normal this arguments return values and copied snapshots", () => {
    function original(a, b) {assert.equal(this.marker, 9); return a + b;}
    const f = fixture({[key]: original});
    const c = install(f.runtime, f.Thread.prototype);
    assert.equal(f.thread.procedures[key].call({marker: 9}, 2, 3), 5);
    assert.equal(c.snapshot().counts.blocked_body, 1);
    const snapshot = c.snapshot();
    snapshot.counts.blocked_body = 99;
    assert.equal(c.snapshot().counts.blocked_body, 1);
    c.uninstall();
    assert.equal(f.thread.procedures[key], original);
});
test("Original thrown error object propagates unchanged", () => {
    const error = new Error("fixture");
    const f = fixture({[key]() {throw error;}});
    const c = install(f.runtime, f.Thread.prototype);
    assert.throws(() => f.thread.procedures[key](), e => e === error);
    assert.equal(c.snapshot().counts.blocked_body, 1);
    c.uninstall();
});
test("Generator counts actual execution and preserves yield next return", () => {
    const receiver = {marker: 7};
    function* original(a) {assert.equal(this, receiver); const b = yield a; return b + 1;}
    const f = fixture({[key]: original});
    const c = install(f.runtime, f.Thread.prototype);
    const g = f.thread.procedures[key].call(receiver, 3);
    assert.equal(c.snapshot().counts.blocked_body, 0);
    assert.deepEqual(g.next(), {value: 3, done: false});
    assert.equal(c.snapshot().counts.blocked_body, 1);
    assert.deepEqual(g.next(5), {value: 6, done: true});
    c.uninstall();
});
test("Generator throw and return delegate correctly", () => {
    const error = new Error("fixture");
    let closed = 0;
    function* original() {try {yield 1;} catch (e) {assert.equal(e, error); yield 2;} finally {closed++;}}
    const f = fixture({[key]: original});
    const c = install(f.runtime, f.Thread.prototype);
    const g = f.thread.procedures[key]();
    g.next();
    assert.deepEqual(g.throw(error), {value: 2, done: false});
    assert.deepEqual(g.return(8), {value: 8, done: true});
    assert.equal(closed, 1);
    c.uninstall();
});
test("New and recompiled threads are decorated after original compilation", () => {
    const f = fixture();
    const c = install(f.runtime, f.Thread.prototype);
    const thread = new f.Thread();
    assert.equal(thread.tryCompile({[key]() {return 3;}}), "compiled");
    assert.equal(thread.procedures[key](), 3);
    thread.tryCompile({[key]() {return 4;}});
    assert.equal(thread.procedures[key](), 4);
    assert.equal(c.snapshot().counts.blocked_body, 2);
    c.uninstall();
});
test("Other targets clones and unlisted procedures are untouched", () => {
    const f = fixture({["Wunlisted"]() {}});
    const untouched = f.thread.procedures.Wunlisted;
    const c = install(f.runtime, f.Thread.prototype);
    assert.equal(f.thread.procedures.Wunlisted, untouched);
    for (const target of [{...f.target, isOriginal: false}, {...f.target, getName() {return "Other";}}]) {
        const t = new f.Thread({}, target);
        const original = () => {};
        t.tryCompile({[key]: original});
        assert.equal(t.procedures[key], original);
    }
    assert.equal(c.snapshot().counts.blocked_body, 0);
    c.uninstall();
});
test("Double install rejected and own hooks restored", () => {
    const f = fixture({[key]() {}});
    const compile = f.Thread.prototype.tryCompile, step = f.runtime._step;
    const c = install(f.runtime, f.Thread.prototype);
    assert.throws(() => install(f.runtime, f.Thread.prototype), /already installed/);
    c.uninstall();
    assert.equal(f.Thread.prototype.tryCompile, compile);
    assert.equal(f.runtime._step, step);
    c.uninstall();
});
test("Step clock per-frame counts reset and original return survives", () => {
    const f = fixture({[key]() {}});
    f.runtime._step = function (value) {this.threads[0].procedures[key](); return value;};
    const c = install(f.runtime, f.Thread.prototype);
    assert.equal(f.runtime._step(7), 7);
    assert.equal(f.runtime._step(8), 8);
    assert.equal(c.snapshot().tick, 2);
    assert.equal(c.snapshot().counts.blocked_body, 1);
    c.reset();
    assert.equal(c.snapshot().tick, 0);
    assert.equal(c.snapshot().counts.blocked_body, 0);
    c.uninstall();
});
test("Saturation flags overflow without stopping original calls", () => {
    let calls = 0;
    const f = fixture({[key]() {calls++;}});
    const c = install(f.runtime, f.Thread.prototype);
    for (let i = 0; i < LIMIT + 2; i++) f.thread.procedures[key]();
    assert.equal(calls, LIMIT + 2);
    assert.equal(c.snapshot().counts.blocked_body, LIMIT);
    assert.equal(c.snapshot().overflow, true);
    c.uninstall();
});
test("Unsupported compiler fails installation without hook changes", () => {
    const f = fixture();
    f.runtime.compilerOptions.enabled = false;
    const original = f.runtime._step;
    assert.throws(() => install(f.runtime, f.Thread.prototype), /Unsupported/);
    assert.equal(f.runtime._step, original);
});
test("Unsupported variant fails metadata not physics", () => {
    const original = () => 7;
    const f = fixture({["Q" + code]: original});
    const c = install(f.runtime, f.Thread.prototype);
    assert.equal(f.thread.procedures["Q" + code](), 7);
    assert.deepEqual(c.snapshot().errors, ["unsupported_variant"]);
    c.uninstall();
});
test("Restoration never overwrites intervening external hooks", () => {
    const f = fixture({[key]() {}});
    const c = install(f.runtime, f.Thread.prototype);
    const replacement = () => 3;
    f.thread.procedures[key] = replacement;
    f.runtime._step = replacement;
    f.Thread.prototype.tryCompile = replacement;
    c.uninstall();
    assert.equal(f.thread.procedures[key], replacement);
    assert.equal(f.runtime._step, replacement);
    assert.equal(f.Thread.prototype.tryCompile, replacement);
    assert.equal(c.snapshot().errors.length, 3);
});
test("Original compilation exception is not swallowed", () => {
    const f = fixture();
    const error = new Error("compile fixture");
    f.Thread.prototype.tryCompile = function () {throw error;};
    const c = install(f.runtime, f.Thread.prototype);
    assert.throws(() => new f.Thread().tryCompile({}), e => e === error);
    c.uninstall();
});
test("Compile during a step is counted in that same tick", () => {
    const f = fixture();
    f.runtime._step = () => {const t = new f.Thread(); t.tryCompile({[key]() {}}); t.procedures[key]();};
    const c = install(f.runtime, f.Thread.prototype);
    f.runtime._step();
    assert.equal(c.snapshot().tick, 1);
    assert.equal(c.snapshot().counts.blocked_body, 1);
    c.uninstall();
});
test("Nonwritable table entry fails metadata without altering original", () => {
    const original = () => 9;
    const table = {};
    Object.defineProperty(table, key, {value: original, enumerable: true, writable: false});
    const f = fixture(table);
    const c = install(f.runtime, f.Thread.prototype);
    assert.equal(f.thread.procedures[key](), 9);
    assert.deepEqual(c.snapshot().errors, ["unsupported_table_entry"]);
    c.uninstall();
});
test("Uncompiled Player and unsupported async function fail diagnostic admission only", () => {
    const f = fixture();
    f.thread.isCompiled = false;
    const c = install(f.runtime, f.Thread.prototype);
    assert.deepEqual(c.snapshot().errors, ["uncompiled_player_thread"]);
    const original = async () => 7;
    const t = new f.Thread();
    t.tryCompile({[key]: original});
    assert.equal(t.procedures[key], original);
    assert(c.snapshot().errors.includes("unsupported_function_kind"));
    c.reset();
    assert(c.snapshot().errors.includes("uncompiled_player_thread"));
    c.uninstall();
});
console.log("Procedure counter synthetic tests passed:", tests);

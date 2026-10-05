/* Opt-in compiled-call telemetry. Never changes physics, controls or observations. */
"use strict";
(function (root) {
    const VERSION = "owned-compiled-player-procedure-counter-v1";
    const LIMIT = 4096, TABLE_LIMIT = 8192;
    const CODES = Object.freeze({
        "move player next %s %s": "blocked_body",
        "move hammer first %s %s %s %s": "free_hammer",
        "hammer wall? %s %s": "wall_probe",
        "hammer tick %s %s %s %s %s %s": "hammer_substep",
    });
    const active = new WeakMap();

    function install(runtime, prototype) {
        if (!runtime || !runtime.compilerOptions || runtime.compilerOptions.enabled !== true ||
            !Array.isArray(runtime.threads) || typeof runtime._step !== "function" ||
            !prototype || typeof prototype.tryCompile !== "function") {
            throw new Error("Unsupported compiled counter runtime");
        }
        if (active.has(runtime)) throw new Error("Procedure counter already installed");
        const originalCompile = prototype.tryCompile, originalStep = runtime._step;
        const entries = [], tables = new WeakSet(), variants = new Set(), errors = new Set();
        let tick = 0, counts = {}, overflow = false, installed = true, compiledTables = 0;
        const labels = Object.values(CODES);
        function clear() {counts = Object.fromEntries(labels.map(label => [label, 0]));}
        clear();
        function fail(code) {errors.add(code);}
        function increment(label) {
            if (!installed) return;
            if (counts[label] < LIMIT) counts[label]++;
            else overflow = true;
        }
        function decorate(thread) {
            if (!thread || !thread.target || thread.target.runtime !== runtime ||
                !thread.target.isOriginal || thread.target.getName() !== "Player") return;
            if (!thread.isCompiled || !thread.procedures || typeof thread.procedures !== "object") {
                fail("uncompiled_player_thread");
                return;
            }
            const table = thread.procedures;
            if (tables.has(table)) return;
            tables.add(table);
            compiledTables++;
            for (const key of Object.keys(table)) {
                const code = key.slice(1), label = CODES[code];
                if (!label) continue;
                if (key[0] !== "W" && key[0] !== "Z") {fail("unsupported_variant"); continue;}
                const descriptor = Object.getOwnPropertyDescriptor(table, key);
                const original = table[key];
                if (!descriptor || !descriptor.writable || typeof original !== "function") {
                    fail("unsupported_table_entry");
                    continue;
                }
                if (entries.length >= TABLE_LIMIT) {fail("table_tracking_limit"); continue;}
                const kind = original.constructor && original.constructor.name;
                let wrapper;
                if (kind === "GeneratorFunction") {
                    wrapper = function* (...args) {
                        increment(label);
                        return yield* original.apply(this, args);
                    };
                } else if (kind === "Function") {
                    wrapper = function (...args) {
                        increment(label);
                        return original.apply(this, args);
                    };
                } else {
                    fail("unsupported_function_kind");
                    continue;
                }
                table[key] = wrapper;
                entries.push({table, key, original, wrapper});
                variants.add(key);
            }
        }
        function safeDecorate(thread) {
            try {decorate(thread);} catch (_) {fail("decoration_failure");}
        }
        function compileHook(...args) {
            const result = originalCompile.apply(this, args);
            if (installed) safeDecorate(this);
            return result;
        }
        function stepHook(...args) {
            tick++;
            clear();
            overflow = false;
            return originalStep.apply(this, args);
        }
        prototype.tryCompile = compileHook;
        runtime._step = stepHook;
        for (const thread of runtime.threads) safeDecorate(thread);
        const counter = {
            snapshot() {
                return {version: VERSION, tick, counts: {...counts}, overflow,
                        errors: [...errors].sort(), compiledTables, variants: [...variants].sort(),
                        installed};
            },
            reset() {
                if (!installed) throw new Error("Procedure counter uninstalled");
                tick = 0;
                clear();
                overflow = false;
            },
            uninstall() {
                if (!installed) return;
                installed = false;
                if (prototype.tryCompile === compileHook) prototype.tryCompile = originalCompile;
                else fail("compile_restoration_conflict");
                if (runtime._step === stepHook) runtime._step = originalStep;
                else fail("step_restoration_conflict");
                for (const entry of entries) {
                    if (entry.table[entry.key] === entry.wrapper) entry.table[entry.key] = entry.original;
                    else fail("table_restoration_conflict");
                }
                entries.length = 0;
                active.delete(runtime);
            },
        };
        active.set(runtime, counter);
        return counter;
    }
    const exports = {install, VERSION, LIMIT, TABLE_LIMIT, CODES};
    root.ResearchProcedureCounter = exports;
    if (typeof module !== "undefined") module.exports = exports;
})(typeof window !== "undefined" ? window : globalThis);

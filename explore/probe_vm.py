"""Probe VM structure at tick boundaries: threads, clones, variable/list inventory."""
import json, math
from research.fast_bridge import FastBridge

PROBE = """(() => { const r = vm.runtime;
 const thr = {};
 for (const t of r.threads) { const k = t.target.getName()+'|orig='+t.target.isOriginal+'|st='+t.status+'|comp='+t.isCompiled+'|depth='+t.stack.length;
   thr[k]=(thr[k]||0)+1; }
 const tg = {};
 for (const t of r.targets) { const k=t.getName()+'|orig='+t.isOriginal; tg[k]=(tg[k]||0)+1; }
 const vars = {};
 for (const t of r.targets.filter(t=>t.isOriginal)) {
   vars[t.getName()] = Object.values(t.variables).map(v=>[v.name, v.type, Array.isArray(v.value)?('list'+v.value.length):typeof v.value]);
 }
 return {nthreads:r.threads.length, thr, tg, vars}; })()"""

def circle(i, radius=90):
    a = -i * math.pi / 60
    return {"x": radius*math.cos(a), "y": radius*math.sin(a), "id": i+1}

with FastBridge(headless=True) as b:
    b.reset(0)
    p0 = b.evaluate(PROBE)
    print("== after reset ==")
    print(json.dumps({k: p0[k] for k in ("nthreads","thr","tg")}, indent=1))
    b.step_commands([circle(i) for i in range(150)])
    p1 = b.evaluate(PROBE)
    print("== after 150 ticks of sweep ==")
    print(json.dumps({k: p1[k] for k in ("nthreads","thr","tg")}, indent=1))
    for name, vs in p1["vars"].items():
        print(name, len(vs), "vars;", sum(1 for v in vs if v[2].startswith('list')), "lists")
    json.dump(p1["vars"], open("explore/vm_vars.json","w"), indent=1)

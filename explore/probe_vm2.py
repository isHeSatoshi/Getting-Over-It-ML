import json, math
from research.fast_bridge import FastBridge

LISTS = """(() => { const r = vm.runtime; const out=[];
 for (const t of r.targets) for (const v of Object.values(t.variables)) if (Array.isArray(v.value)) out.push([t.getName(), t.isOriginal, v.name, v.value.length, JSON.stringify(v.value).length]);
 return out; })()"""
CLONES = """(() => { const r = vm.runtime;
 return {n:r.targets.length, ids:r.targets.map(t=>t.id).join(','),
   clones:r.targets.filter(t=>!t.isOriginal).map(t=>[t.getName(), t.currentCostume, Math.round(t.x), Math.round(t.y), t.visible, t.size, Object.keys(t.variables).length]),
   edge:r.targets.map(t=>Object.keys(t._edgeActivatedHatValues||{}).length).reduce((a,b)=>a+b,0),
   hats:Object.keys(r._hats||{}).length, threads:r.threads.length,
   effects:r.targets.filter(t=>Object.values(t.effects||{}).some(v=>v!==0)).map(t=>t.getName())}; })()"""
def circle(i, radius=90, period=120):
    a = -i * 2*math.pi/period
    return {"x": radius*math.cos(a), "y": radius*math.sin(a), "id": i+1}
with FastBridge(headless=True) as b:
    b.reset(0)
    for row in b.evaluate(LISTS):
        if row[3] > 0: print("LIST", row)
    c = b.evaluate(CLONES); print("t=0 clones", json.dumps(c)[:900])
    sigs=set()
    for blk in range(12):
        tr = b.step_commands([circle(blk*100+i) for i in range(100)])
        c = b.evaluate(CLONES)
        s = tr[-1]
        print(blk, "x,y=", round(s["player_world_x"]), round(s["player_world_y"]), "ntargets", c["n"], "edge", c["edge"], "hats", c["hats"], "thr", c["threads"], "fx", c["effects"],
              "clones", [(x[0],x[1],x[2],x[3]) for x in c["clones"]][:4])

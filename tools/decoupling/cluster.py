"""Group booster_ws code files into units that must move together.

Usage (repo root): <graphify python> docs/decoupling/cluster.py . ../wt-k1-tools > docs/decoupling/clusters.json

File-level edges:
  import  (w=3)  absolute, relative and sys.path-style bare imports, resolved to a repo file
  path    (w=2)  a string naming another repo .py/.sh file (shell launchers, subprocess calls)
  ast     (w=1)  graphify calls / inherits / uses between two files (graphify-out/graph.json)
Hard units: strongly connected components (import cycles). Soft units: Louvain communities.
"""
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

HERE = Path(__file__).parent
src = (HERE / "lib_deps.py").read_text().split("# module name -> lib")[0]
exec(src)  # ROOT, CHAT, RULES, lib_of, walk, files

CODE = {k: v for k, v in files.items() if v[0].suffix in (".py", ".sh")}
# final library per file (after lib_deps.py's follow pass: tests + launchers move with what they exercise)
_lj = HERE / "lib_deps.json"
if _lj.exists():
    for lib, ms in json.loads(_lj.read_text())["members"].items():
        for k in ms:
            if k in CODE:
                CODE[k] = (CODE[k][0], lib)
STD = set(sys.stdlib_module_names) | {"torch", "numpy", "mujoco", "rclpy", "launch", "launch_ros", "isaaclab",
                                     "mjlab", "gymnasium", "cv2", "yaml", "pytest", "omni", "pxr", "tyro", "wandb"}
GENERIC = {"cli", "config", "utils", "test", "tests", "main", "app", "env_cfg", "rewards", "mdp", "agents",
           "__init__", "common", "constants", "launch"}

# dotted suffix -> [file keys]
idx = defaultdict(list)
for key, (p, _) in CODE.items():
    if p.suffix != ".py":
        continue
    parts = key.replace("chat:", "").removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    for i in range(len(parts)):
        idx[".".join(parts[i:])].append(key)


def common_prefix(a, b):
    n = 0
    for x, y in zip(a.split("/"), b.split("/")):
        if x != y:
            break
        n += 1
    return n


def resolve(mod, importer):
    cands = idx.get(mod, [])
    if not cands:
        return None
    top = mod.split(".")[0]
    if top in STD:
        return None
    best = max(cands, key=lambda c: common_prefix(c, importer))
    same_top = common_prefix(best, importer) >= 1
    if "." not in mod and (mod in GENERIC or (not same_top and len(cands) > 1)):
        return best if same_top and mod not in GENERIC else None
    return best


G = nx.DiGraph()
for k in CODE:
    G.add_node(k)
why = defaultdict(set)


def add(a, b, w, kind):
    if a == b or b not in CODE:
        return
    d = G.get_edge_data(a, b, {"weight": 0})
    G.add_edge(a, b, weight=d["weight"] + w)
    why[(a, b)].add(kind)


by_name = defaultdict(list)
for k in CODE:
    by_name[k.replace("chat:", "")].append(k)
PATHRE = re.compile(r"([\w./-]*[\w-]+\.(?:py|sh))\b")

for key, (p, _) in CODE.items():
    text = p.read_text(errors="replace")
    if p.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        pkg = key.replace("chat:", "").split("/")[:-1]
        pref = "chat:" if key.startswith("chat:") else ""
        for n in ast.walk(tree) if tree else []:
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                if n.level:
                    base = pkg[: len(pkg) - (n.level - 1)] if n.level > 1 else pkg
                    stem = "/".join(base + (n.module.split(".") if n.module else []))
                    for a in n.names:
                        for cand in (stem + "/" + a.name + ".py", stem + ".py", stem + "/__init__.py"):
                            if pref + cand in CODE:
                                add(key, pref + cand, 3, "import")
                                break
                    continue
                if n.module:
                    mods = [n.module + "." + a.name for a in n.names] + [n.module]
            for m in mods:
                t = resolve(m, key)
                if t:
                    add(key, t, 3, "import")
                    if isinstance(n, ast.ImportFrom):
                        break
    for m in PATHRE.finditer(text):
        ref = m.group(1).lstrip("./")
        hits = [f for name, fs in by_name.items() if name.endswith(ref) and ("/" in ref or name.split("/")[-1] == ref) for f in fs]
        if len(hits) == 1:
            add(key, hits[0], 2, "path")
        elif hits:
            add(key, max(hits, key=lambda c: common_prefix(c, key)), 2, "path")

# graphify AST edges between files
gj = HERE.parent.parent / "graphify-out" / "graph.json"
if gj.exists():
    g = json.loads(gj.read_text())
    nf = {n["id"]: n.get("source_file") for n in g["nodes"]}
    for e in g["links"]:
        if e.get("_origin") != "ast" or e.get("relation") not in ("calls", "inherits", "uses", "indirect_call"):
            continue
        a, b = nf.get(e["source"]), nf.get(e["target"])
        if a and b and a != b and a in CODE and b in CODE:
            add(a, b, 1, "ast")

U = nx.Graph()
U.add_nodes_from(G)
for a, b, d in G.edges(data=True):
    w = U.get_edge_data(a, b, {"weight": 0})["weight"] + d["weight"]
    U.add_edge(a, b, weight=w)

# hard units: cycles through real imports only (path strings and AST calls are soft)
GI = nx.DiGraph([(a, b) for a, b in G.edges if "import" in why[(a, b)]])
sccs = [sorted(c) for c in nx.strongly_connected_components(GI) if len(c) > 1]
sccs_all = [sorted(c) for c in nx.strongly_connected_components(G) if len(c) > 1]
comms = nx.community.louvain_communities(U, weight="weight", resolution=1.0, seed=0)
loc = {k: CODE[k][0].read_text(errors="replace").count("\n") for k in CODE}

out = []
for c in sorted(comms, key=len, reverse=True):
    if len(c) < 2:
        continue
    c = sorted(c)
    libs = Counter(CODE[f][1] for f in c)
    internal = sum(d["weight"] for a, b, d in U.edges(c, data=True) if a in c and b in c)
    external = sum(d["weight"] for a, b, d in U.edges(c, data=True) if (a in c) != (b in c))
    core = [l for l in libs if l != "tests"]
    ext_to = Counter()
    for a, b, d in U.edges(c, data=True):
        o = b if a in c else a
        if o not in c:
            ext_to[CODE[o][1]] += d["weight"]
    out.append({
        "n": len(c), "loc": sum(loc[f] for f in c), "libs": dict(libs.most_common()),
        "split": len(core) > 1, "internal": internal, "external": external,
        "ext_to": dict(ext_to.most_common(5)),
        "hub": sorted(c, key=lambda f: -U.degree(f, weight="weight"))[:5],
        "files": c,
    })
iso = Counter(CODE[k][1] for k in CODE if U.degree(k) == 0)
print(json.dumps({
    "files": len(CODE), "loc_total": sum(loc.values()), "edges": G.number_of_edges(), "isolated": dict(iso),
    "sccs": sccs, "sccs_all": sccs_all, "clusters": out,
    "split_edges": [{"a": a, "b": b, "w": d["weight"], "why": sorted(why[(a, b)])}
                    for a, b, d in G.edges(data=True) if CODE[a][1] != CODE[b][1]],
}, indent=1))

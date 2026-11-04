#!/usr/bin/env python3
"""docs/lib_graph.json -> docs/architecture.html (layered SVG: nodes sized by LOC, edges = measured imports)."""
import json, html
from pathlib import Path
H = Path(__file__).resolve().parent.parent
g = json.load(open(H / "docs/lib_graph.json"))
layers = {"L3": ["deploy_robot", "deploy_laptop", "web_console", "ops"],
          "L2": ["rl_isaac", "rl_mj", "mimic", "teleop", "perception", "vla", "data"],
          "L1": ["utils", "runtime"], "L0": ["common", "description"]}
names = {"L0": "CONTRACT", "L1": "CORE", "L2": "DOMAIN", "L3": "APPS"}
W, RH, NW, NH = 1180, 150, 130, 54
pos = {}
for i, (L, libs) in enumerate(layers.items()):
    gap = W / (len(libs) + 1)
    for j, k in enumerate(libs):
        pos[k] = (gap * (j + 1), 70 + i * RH)
out = [f'<svg viewBox="0 0 {W} {70 + 4 * RH}" xmlns="http://www.w3.org/2000/svg" font-family="monospace">']
for i, L in enumerate(layers):
    y = 70 + i * RH
    out.append(f'<rect x="0" y="{y-45}" width="{W}" height="{RH-20}" fill="#{"2d3142" if i%2==0 else "393e53"}" opacity=".6"/>'
               f'<text x="10" y="{y-28}" fill="#949eb2" font-size="11">{L} {names[L]}</text>')
mx = max([e["n"] for e in g["edges"]] + [1])
for e in g["edges"]:
    (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
    out.append(f'<line x1="{x1}" y1="{y1+NH/2-10}" x2="{x2}" y2="{y2-NH/2+10}" stroke="#f08a59" stroke-opacity=".6" stroke-width="{1+4*e["n"]/mx:.1f}"><title>{e["from"]} imports {e["to"]} ({e["n"]} files)</title></line>')
mloc = max(g["loc"].values())
for k, (x, y) in pos.items():
    r = g["libs"][k]; s = 0.6 + 0.4 * g["loc"][k] / mloc
    out.append(f'<g><title>{html.escape(r["purpose"])}</title><rect x="{x-NW/2}" y="{y-NH/2}" width="{NW}" height="{NH}" rx="4" fill="#f5f5f5" fill-opacity="{s:.2f}" stroke="#f08a59"/>'
               f'<text x="{x}" y="{y-4}" text-anchor="middle" font-size="12" fill="#2d3142">{r["repo"]}</text>'
               f'<text x="{x}" y="{y+14}" text-anchor="middle" font-size="10" fill="#2d3142">{g["files"][k]} files · {g["loc"][k]:,} LOC</text></g>')
out.append("</svg>")
Path(H / "docs/architecture.html").write_text(f"""<!DOCTYPE html><meta charset=utf-8><title>k1-workspace architecture</title>
<body style="background:#2d3142;color:#f5f5f5;font-family:sans-serif;padding:2rem"><h1 style="font-weight:400">k1-workspace: library layers</h1>
<p style="color:#bfc0c0;max-width:70ch">Boxes = repos (shade = LOC). Orange lines = Python imports measured in the extracted code (width = files). Imports only point down a layer; hover for details.</p>
{''.join(out)}<p style="color:#bfc0c0">Full code-level graph: <code>graphify-out/graph.html</code> (400 communities).</p></body>""")

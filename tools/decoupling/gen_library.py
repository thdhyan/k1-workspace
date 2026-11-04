"""Figures for the library-based layout. Reads lib_deps.json (from lib_deps.py).

Usage: python3 gen_library.py template.html booster_ws_dependencies.html
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
exec((HERE / "gen_figures.py").read_text().split("# ---------- Fig 1")[0])  # shared helpers + tokens

D = json.loads((HERE / "lib_deps.json").read_text())
ORDER = ["common", "utils", "runtime", "rl_isaac", "rl_mj", "mimic", "teleop", "perception", "vla", "data",
         "deploy_robot", "deploy_laptop", "web_console", "ops", "tests"]
RANK = {"common": 0, "utils": 1, "runtime": 1, "deploy_robot": 3, "deploy_laptop": 3, "web_console": 3, "ops": 3, "tests": 4}
for k in ["rl_isaac", "rl_mj", "mimic", "teleop", "perception", "vla", "data"]:
    RANK[k] = 2
E = {(e["from"], e["to"]): e["n"] for e in D["edges"]}
FOCAL = ("rl_isaac", "ops")  # largest cell the layering still forbids (path strings only)


def forbidden(a, b):
    return a != "tests" and RANK[a] <= RANK[b]


# ---------- L1: dependency matrix ----------
def fig_matrix():
    cw, ch, gap, X0, Y0 = 60, 28, 2, 150, 84
    n = len(ORDER)
    mx = max(v for k, v in E.items() if k != FOCAL)
    b = f'<text x="{X0 + n*(cw+gap)/2}" y="22" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.14em">IMPORTS / PATH REFS INTO →</text>'
    b += f'<text x="20" y="{Y0-10}" fill="{MUTED}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">FROM ↓</text>'
    for j, c in enumerate(ORDER):
        x = X0 + j*(cw+gap) + cw/2
        b += f'<text x="{x}" y="{Y0-12}" fill="{MUTED}" font-size="8.5" font-family="{MONO}" text-anchor="middle">{c.replace("deploy_", "dep_").replace("web_console", "web")}</text>'
    for i, r in enumerate(ORDER):
        y = Y0 + i*(ch+gap)
        b += f'<text x="{X0-10}" y="{y+ch/2+3}" fill="{INK}" font-size="9" font-family="{MONO}" text-anchor="end">{r}</text>'
        for j, c in enumerate(ORDER):
            x = X0 + j*(cw+gap)
            b += f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="{PAPER}"/>'
            if r == c:
                b += f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="none" stroke="rgba(245,245,245,0.10)"/>'
                continue
            v = E.get((r, c), 0)
            bind = f'data-row="{r}" data-col="{c}" data-value="{v}"'
            if (r, c) == FOCAL:
                b += f'<rect {bind} data-focal="true" x="{x}" y="{y}" width="{cw}" height="{ch}" fill="{ACC}" fill-opacity="0.85" stroke="{ACC}" stroke-width="1.2"/>'
                b += f'<text x="{x+cw/2}" y="{y+ch/2+3}" fill="{PAPER}" font-size="9" font-weight="600" font-family="{MONO}" text-anchor="middle">{v}</text>'
                continue
            op = 0.05 if v == 0 else max(0.10, math.sqrt(v/mx)*0.65)
            dash = ' stroke="rgba(245,245,245,0.55)" stroke-dasharray="3,2" stroke-width="0.8"' if v and forbidden(r, c) else ''
            b += f'<rect {bind} x="{x}" y="{y}" width="{cw}" height="{ch}" fill="{INK}" fill-opacity="{op:.2f}"{dash}/>'
            if v:
                fc = PAPER if op >= 0.40 else INK
                b += f'<text x="{x+cw/2}" y="{y+ch/2+3}" fill="{fc}" font-size="9" font-family="{MONO}" text-anchor="middle">{v}</text>'
    ly = Y0 + n*(ch+gap) + 40
    b += f'<line x1="40" y1="{ly-20}" x2="1060" y2="{ly-20}" stroke="rgba(245,245,245,0.12)"/>'
    b += f'<rect x="40" y="{ly-6}" width="20" height="12" fill="{INK}" fill-opacity="0.10"/><rect x="64" y="{ly-6}" width="20" height="12" fill="{INK}" fill-opacity="0.65"/>'
    b += f'<text x="92" y="{ly+3}" fill="{MUTED}" font-size="9" font-family="{MONO}">LOW → HIGH (1 → {mx}, sqrt)</text>'
    b += f'<rect x="300" y="{ly-6}" width="20" height="12" fill="none" stroke="rgba(245,245,245,0.55)" stroke-dasharray="3,2"/>'
    b += f'<text x="328" y="{ly+3}" fill="{MUTED}" font-size="9" font-family="{MONO}">forbidden by target layering</text>'
    b += f'<rect x="540" y="{ly-6}" width="20" height="12" fill="{ACC}" fill-opacity="0.85"/>'
    b += f'<text x="568" y="{ly+3}" fill="{MUTED}" font-size="9" font-family="{MONO}">task code hard-codes launcher paths</text>'
    w = X0 + n*(cw+gap) + 30
    return svg("lmat", "Cross-library dependency matrix after the moves",
               "Rows import from or hard-code paths into columns; counts measured on the working tree with the final mapping.",
               w, ly + 24, b)


# ---------- L2: layer stack ----------
def chip(x, y, w, name, sub, focal=False):
    st = (ACC, ACCT, 1.2) if focal else (MUTED, "rgba(245,245,245,0.05)", 0.8)
    return (f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="6" fill="{PAPER}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="6" fill="{st[1]}" stroke="{st[0]}" stroke-width="{st[2]}"/>'
            f'<text x="{x+w/2}" y="{y+17}" fill="{INK}" font-size="11.5" font-weight="600" font-family="{SANS}" text-anchor="middle">{name}</text>'
            f'<text x="{x+w/2}" y="{y+31}" fill="{SOFT}" font-size="8.5" font-family="{MONO}" text-anchor="middle">{sub}</text>')


def fig_layers():
    L = [("L3", "APPS", "processes you start", [
            ("deploy_robot", "on the K1 CPU", True), ("deploy_laptop", "ROS 2 jazzy ws", False),
            ("web_console", "one web shell", False), ("ops", "hosts · jobs · CI", False)]),
         ("L2", "DOMAIN", "no cross-imports", [
            ("k1_rl_isaac", "Isaac Lab", False), ("k1_rl_mj", "mjlab", False), ("k1_mimic", "retarget", False),
            ("k1_teleop", "VR · mocap", False), ("k1_perception", "SLAM · depth", False),
            ("k1_vla", "voice · VLM", False), ("k1_data", "bags · frames", False)]),
         ("L1", "CORE", "torch / numpy only", [
            ("k1_runtime", "policy exec · robot IO", True), ("k1_utils", "eval · gates · video", False)]),
         ("L0", "CONTRACT", "no heavy deps", [
            ("k1_common", "joints · gains · obs · manifest", False),
            ("k1_description", "URDF · MJCF · USD", False)])]
    b = ""
    X, W, H, Y = 120, 880, 76, 30
    for i, (idx, name, note, chips) in enumerate(L):
        y = Y + i*H
        b += f'<rect x="{X}" y="{y}" width="{W}" height="{H}" fill="{"rgba(245,245,245,0.03)" if i % 2 else PAPER}" stroke="rgba(245,245,245,0.12)"/>'
        b += f'<text x="{X+14}" y="{y+30}" fill="{MUTED}" font-size="9" font-family="{MONO}" letter-spacing="0.14em">{idx}</text>'
        b += f'<text x="{X+14}" y="{y+46}" fill="{INK}" font-size="10" font-weight="600" font-family="{SANS}" letter-spacing="0.06em">{name}</text>'
        b += f'<text x="{X+14}" y="{y+62}" fill="{SOFT}" font-size="7.5" font-family="{MONO}">{note}</text>'
        n = len(chips)
        cx0, avail, g = X + 112, W - 112 - 12, 8
        cw = (avail - g*(n-1)) / n
        for k, (cn, cs, f) in enumerate(chips):
            b += chip(cx0 + k*(cw+g), y + 18, cw, cn, cs, f)
    b += f'<rect x="{X}" y="{Y}" width="{W}" height="{4*H}" fill="none" stroke="{MUTED}"/>'
    b += f'<line x1="70" y1="{Y+20}" x2="70" y2="{Y+4*H-20}" stroke="{MUTED}" marker-end="url(#arrow)"/>'
    b += f'<text x="56" y="{Y+2*H}" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.12em">IMPORTS</text>'
    b += f'<text x="56" y="{Y+2*H+12}" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.12em">GO DOWN</text>'
    b += legend(Y + 4*H + 44, [("focal", "new or moved code path"), ("leaf", "library")],
                "Domain libraries trade files, not imports.")
    return svg("llay", "Target library layers", "Four layers; imports only point downward.", 1040, Y + 4*H + 64, b)


# ---------- L3: workflow ----------
def fig_flow():
    b = ""
    b += path("M200,180 H232 Q240,180 240,172 V96 Q240,88 248,88 H280")
    b += path("M200,196 H232 Q240,196 240,204 V280 Q240,288 248,288 H280")
    b += path("M440,88 H472 Q480,88 480,96 V172 Q480,180 488,180 H520")
    b += path("M440,288 H472 Q480,288 480,280 V204 Q480,196 488,196 H520")
    b += path("M680,180 H712 Q720,180 720,172 V96 Q720,88 728,88 H760", accent=True)
    b += path("M680,196 H712 Q720,196 720,204 V280 Q720,288 728,288 H760", accent=True)
    b += path("M840,116 V260")
    b += path("M1000,88 H920")
    b += path("M1000,180 H968 Q960,180 960,172 V112 Q960,104 952,104 H920")
    b += path("M1000,196 H968 Q960,196 960,204 V264 Q960,272 952,272 H920")
    b += path("M1000,288 H920")
    b += label(232, 130, "MOTION CLIPS", anchor="end")
    b += label(488, 140, "ONNX+MANIFEST", anchor="start")
    b += label(712, 140, "POLICY", accent=True, anchor="end")
    b += label(848, 188, "UDP PAD :9870", anchor="start")
    b += label(960, 74, "IK TARGETS")
    b += label(968, 140, "HTTP · WS", anchor="start")
    b += label(960, 302, "SKILL CALLS")
    b += node(40, 160, "L2", None, "k1_mimic", "GVHMR · GMR · SOMA", "leaf")
    b += node(280, 60, "L2", None, "k1_rl_mj", "mjlab · dl / zz-bw", "leaf")
    b += node(280, 260, "L2", None, "k1_rl_isaac", "Isaac Lab · dl", "leaf")
    b += node(520, 160, "REGISTRY", None, "k1_policies", "manifest.yaml + blobs", "focal")
    b += node(760, 60, "L3", None, "deploy_laptop", "ROS 2 · sim · pad", "int")
    b += node(760, 260, "L3", None, "deploy_robot", "runner on K1 CPU", "int")
    b += node(1000, 60, "L2", None, "k1_teleop", "VR · PhaseSpace", "leaf")
    b += node(1000, 160, "L3", None, "web_console", "dashboards", "int")
    b += node(1000, 260, "L2", None, "k1_vla", "voice · VLM tools", "leaf")
    b += legend(376, [("focal", "artifact registry"), ("int", "app"), ("leaf", "domain library"), ("arrow", "artifact or message")],
                "Data moves as files and messages.")
    return svg("lflow", "Workflow between libraries",
               "Mimic clips feed both trainers; trained policies go through the registry to the laptop and robot.",
               1200, 400, b)


# ---------- L4: deployment ----------
def dchip(x, y, w, name, ver, focal=False):
    st = (ACC, ACCT) if focal else (MUTED, "rgba(245,245,245,0.05)")
    return (f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="4" fill="{st[1]}" stroke="{st[0]}" stroke-width="{1.2 if focal else 0.8}"/>'
            f'<text x="{x+10}" y="{y+16}" fill="{INK}" font-size="11" font-family="{SANS}">{name}</text>'
            f'<text x="{x+w-10}" y="{y+16}" fill="{SOFT}" font-size="8.5" font-family="{MONO}" text-anchor="end">{ver}</text>')


def dnode(x, y, w, h, tag, name, chips, badge=None):
    tw = len(tag)*6+10
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>'
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="rgba(245,245,245,0.04)" stroke="{INK}"/>'
    s += f'<rect x="{x+10}" y="{y+8}" width="{tw}" height="12" rx="2" fill="none" stroke="rgba(245,245,245,0.40)" stroke-width="0.8"/>'
    s += f'<text x="{x+10+tw/2}" y="{y+17}" fill="{INK}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">{tag}</text>'
    s += f'<text x="{x+18+tw}" y="{y+18}" fill="{INK}" font-size="12" font-weight="600" font-family="{SANS}">{name}</text>'
    if badge:
        s += f'<rect x="{x+w-34}" y="{y+8}" width="24" height="12" rx="2" fill="none" stroke="rgba(245,245,245,0.40)" stroke-width="0.8"/>'
        s += f'<text x="{x+w-22}" y="{y+17}" fill="{INK}" font-size="8" font-family="{MONO}" text-anchor="middle">{badge}</text>'
    for k, (cn, cv, f) in enumerate(chips):
        s += dchip(x+14, y+34+k*32, w-28, cn, cv, f)
    return s


def zone(x, y, w, h, name):
    lw = len(name)*6+12
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="rgba(245,245,245,0.02)" stroke="rgba(245,245,245,0.20)" stroke-dasharray="4,4"/>'
            f'<rect x="{x+12}" y="{y-6}" width="{lw}" height="12" fill="{PAPER}"/>'
            f'<text x="{x+18}" y="{y+3}" fill="{MUTED}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">{name}</text>')


def lpath(d, dash=False):
    da = ' stroke-dasharray="5,4"' if dash else ''
    return f'<path d="{d}" fill="none" stroke="{LINK}" stroke-width="1"{da} marker-end="url(#arrow-link)"/>'


def llabel(cx, cy, t):
    w = len(t)*5.4+10
    return (f'<rect x="{cx-w/2:.0f}" y="{cy-6}" width="{w:.0f}" height="12" rx="2" fill="{PAPER}"/>'
            f'<text x="{cx}" y="{cy+3}" fill="{LINK}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.06em">{t}</text>')


def fig_deploy():
    b = zone(20, 40, 360, 270, "GPU HOSTS") + zone(420, 40, 360, 270, "LAB LAPTOP") + zone(820, 40, 360, 270, "K1 FLEET · WI-FI")
    b += lpath("M460,110 H340") + lpath("M340,150 H460", dash=True)
    b += lpath("M460,242 H340")
    b += lpath("M740,110 H860") + lpath("M740,150 H860") + lpath("M860,200 H740")
    b += llabel(400, 98, "SSH JOBS") + llabel(400, 138, "RSYNC POLICY") + llabel(400, 230, "HTTP :7861")
    b += llabel(800, 98, "UDP :9870") + llabel(800, 138, "WS :51111") + llabel(800, 188, "TCP :7447")
    b += dnode(60, 80, 280, 104, "GPU", "dl · zz-bw", [("k1_rl_isaac", "Isaac Lab 6", False), ("k1_rl_mj", "mjlab", False)])
    b += dnode(60, 204, 280, 76, "ARM64", "DGX Spark", [("k1_mimic service", "docker :7861", False)])
    b += dnode(460, 80, 280, 180, "HOST", "laptop", [("deploy_laptop", "ROS 2 jazzy", False), ("web_console", ":8080 · :8765", False),
                                                    ("ops CLI", "uv · ssh", False)])
    b += dnode(860, 80, 280, 140, "ROBOT", "Booster K1", [("deploy_robot", "torch cpu", True), ("k1_vla agent", ":8091", False),
                                                        ("k1_perception", "cuVSLAM :7447", False)], badge="x6")
    b += legend(352, [("focal", "smallest install: runtime + common"), ("leaf", "artifact")],
                "No DDS across Wi-Fi: TCP relay and UDP only.")
    return svg("ldep", "Where each library runs", "GPU hosts train, the laptop drives, each K1 runs its own policy.", 1200, 376, b)



# ---------- move units (clusters.json from cluster.py) ----------
C = json.loads((HERE / "clusters.json").read_text())
MEM = {k: l for l, ms in D["members"].items() for k in ms}
# name, anchor files (the unit = the Louvain clusters holding them), ships as, why it stays together, cut
UNITS = [
    ("Isaac tasks", ["velocity/velocity_env_cfg.py", "push/push_mdp.py", "agents/squat_ppo_cfg.py"],
     "<code>k1_rl_isaac</code> tasks/ + sim/",
     "gym registration imports every env cfg; push, velocity and kick share MDP terms and <code>sim_backend</code>",
     "<code>src/k1_sim_isaac</code> imports <code>velocity_env_cfg</code>: ships here (it runs in Isaac's own ROS env anyway)"),
    ("Isaac scripts + jobs", ["k1_velocity/scripts/train.py"],
     "<code>k1_rl_isaac</code> scripts/ + jobs/",
     "42 launchers pass task names and script paths; play/train/export scripts share CLI helpers",
     "21 multi-host chain scripts → <code>jobs/*.yaml</code> run by <code>k1_ops</code>"),
    ("mjlab tasks", ["mjlab_k1/tasks_kick.py"],
     "<code>k1_rl_mj</code>",
     "<code>mjlab_k1/__init__</code> registers every task, <code>tasks_track</code> included; 50 <code>scripts_*</code> import tasks",
     "<code>k1_constants</code> → <code>k1_common</code>, <code>wbc.py</code> → <code>k1_runtime</code>; track and YOLO-kick tasks stay here"),
    ("ROS bringup + SLAM", ["k1_locomotion/locomotion_node.py"],
     "<code>deploy_laptop</code> · <code>k1_perception</code> · <code>deploy_robot</code>",
     "launch files are the composition root; SLAM relay ↔ rx ↔ <code>run_slam</code> ↔ <code>laptop_rviz</code> form a path cycle",
     "split is legal: launch files only reference L2 executables; the SLAM chain moves as one package"),
    ("k1_chat", ["k1_chat/brain.py"],
     "<code>k1_vla</code>, own repo",
     "brain, tools, audio and console import each other; 2 edges leave the unit",
     "console/debug stay inside (brain imports them); web_console embeds over HTTP"),
    ("k1m", ["k1m/pipeline.py"],
     "<code>k1_mimic</code>, own repo",
     "pipeline ↔ local/remote stages; <b>0</b> edges leave the unit",
     "<code>app.py</code> (Gradio UI) comes along; clips leave as files in the <code>k1_common</code> schema"),
    ("Push-IK runtime", ["deploy/push_ik_core.py"],
     "<code>k1_runtime</code> + 3 entry points",
     "one UDP :9870 protocol, one set of gains and <code>ArmJog</code>; all 5 importers of <code>k1_gamepad_deploy</code> use only its shared half",
     "split that file: core → <code>k1_runtime</code>; <code>run_robot</code> → deploy_robot; web/sim/pad → deploy_laptop; PhaseSpace → teleop"),
    ("Teleop", ["k1_teleop/teleop_mapping.py"],
     "<code>k1_teleop</code>",
     "XR node, mapping, HMD poser and their test share one config",
     "<code>k1_arm_ik</code> → runtime, <code>soma_retarget_node</code> → mimic, <code>yolo_node</code> → vla"),
    ("Eval gates", ["scripts/mujoco_eval.py"], "<code>k1_utils</code>",
     "height gate imports mujoco_eval; one test", "take policy and asset paths as arguments"),
    ("Recording", ["real_robot/k1_walk_record.sh", "real_robot/record_session.sh"], "<code>k1_data</code> · <code>deploy_robot</code>",
     "record scripts call verify / freshness checks / sftp sync", "on-robot recorders stay in deploy_robot"),
]


def unit_members():
    out = []
    for name, anchors, *rest in UNITS:
        cl = [c for c in C["clusters"] if any(f.endswith(a) for a in anchors for f in c["files"])]
        files = sorted({f for c in cl for f in c["files"]})
        libs = {}
        for f in files:
            libs[MEM.get(f, "?")] = libs.get(MEM.get(f, "?"), 0) + 1
        out.append((name, files, sum(c["loc"] for c in cl), libs, *rest))
    return out


UM = unit_members()


def squarify(vals, x, y, w, h):
    """Bruls et al. squarified treemap; vals sorted descending, sum = w*h."""
    rects, vals = [], list(vals)
    while vals:
        short = min(w, h)
        row, best = [], float("inf")
        for v in vals:
            t = row + [v]
            s = sum(t)
            worst = max(max(short*short*r/(s*s), s*s/(short*short*r)) for r in t)
            if worst > best:
                break
            row, best = t, worst
        s = sum(row)
        if w >= h:  # column on the left
            cw, yy = s/h, y
            for v in row:
                rects.append((x, yy, cw, v/cw)); yy += v/cw
            x, w = x + cw, w - cw
        else:  # row on top
            rh, xx = s/w, x
            for v in row:
                rects.append((xx, y, v/rh, rh)); xx += v/rh
            y, h = y + rh, h - rh
        vals = vals[len(row):]
    return rects


def fig_units():
    named = [u for u in UM if u[0] in ("Isaac tasks", "Isaac scripts + jobs", "mjlab tasks", "ROS bringup + SLAM",
                                       "k1_chat", "k1m", "Push-IK runtime")]
    total = C["loc_total"]
    rest = total - sum(u[2] for u in named)
    rest_names = [u[0] for u in UM if u not in named]
    cells = sorted([(u[2], u[0], u[3], u[4]) for u in named] + [(rest, "Other", None, "")], reverse=True)
    X, Y, W, H = 40, 40, 916, 380
    k = W*H/total
    rects = squarify([c[0]*k for c in cells], X, Y, W, H)
    snap = lambda v: round(v/4)*4
    ramp = [0.14, 0.12, 0.10, 0.09, 0.08, 0.06, 0.05, 0.04]
    b, worst = "", 0.0
    for i, ((v, name, libs, ships), (rx, ry, rw, rh)) in enumerate(zip(cells, rects)):
        x0, y0, x1, y1 = snap(rx), snap(ry), snap(rx+rw), snap(ry+rh)
        x0 += 0 if x0 == X else 2; y0 += 0 if y0 == Y else 2
        x1 -= 0 if x1 == X+W else 2; y1 -= 0 if y1 == Y+H else 2
        cw, ch = x1-x0, y1-y0
        share = 100*v/total
        worst = max(worst, abs(cw*ch/(W*H) - v/total)/(v/total))
        focal = name == "Push-IK runtime"
        fill = ACCT.replace("0.10", "0.16") if focal else f"rgba(245,245,245,{ramp[i]})"
        stroke = f'stroke="{ACC}" stroke-width="1.5"' if focal else 'stroke="rgba(245,245,245,0.30)" stroke-width="1"'
        b += f'<rect x="{x0}" y="{y0}" width="{cw}" height="{ch}" rx="2" fill="{PAPER}"/>'
        b += f'<rect x="{x0}" y="{y0}" width="{cw}" height="{ch}" rx="2" data-share="{share:.2f}" fill="{fill}" {stroke}/>'
        pad = 16 if cw > 140 else 12 if cw > 120 else 10
        fit = lambda t, px: len(t) * px <= cw - 2 * pad
        nl = [name] if fit(name, 7.6) else name.rsplit(" ", 1)
        for j, t in enumerate(nl):
            b += f'<text x="{x0+pad}" y="{y0+28+16*j}" fill="{INK}" font-size="13" font-weight="600" font-family="{SANS}">{t}</text>'
        ty = y0 + 46 + 16 * (len(nl) - 1)
        b += f'<text x="{x0+pad}" y="{ty}" fill="{MUTED}" font-size="9" font-family="{MONO}">{v:,} LOC · {share:.0f}%</text>'
        if libs and ch >= 84:
            parts = [f"{l} {n}" for l, n in sorted(libs.items(), key=lambda t: -t[1])[:4]]
            lines = [""]
            for t in parts:
                t = t if fit(t, 5.4) else t.replace("deploy_", "dep_")
                cand = f"{lines[-1]} · {t}" if lines[-1] else t
                if fit(cand, 5.4):
                    lines[-1] = cand
                elif len(lines) < 3 and fit(t, 5.4):
                    lines.append(t)
            for j, t in enumerate(lines):
                b += f'<text x="{x0+pad}" y="{ty+16+14*j}" fill="{MUTED}" font-size="9" font-family="{MONO}">{t}</text>'
        if name == "Other" and ch >= 84:
            b += f'<text x="{x0+16}" y="{y0+62}" fill="{MUTED}" font-size="9" font-family="{MONO}">teleop · gates · recording</text>'
            b += f'<text x="{x0+16}" y="{y0+76}" fill="{MUTED}" font-size="9" font-family="{MONO}">small clusters · 76 lone files</text>'
    print(f"treemap worst relative area error {worst:.3f}", file=sys.stderr)
    b += f'<line x1="40" y1="442" x2="956" y2="442" stroke="rgba(245,245,245,0.12)"/>'
    b += f'<text x="40" y="462" fill="{MUTED}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">LEGEND</text>'
    b += f'<rect x="40" y="472" width="20" height="12" rx="2" fill="{ACCT}" stroke="{ACC}" stroke-width="1.5"/>'
    b += f'<text x="68" y="481" fill="{MUTED}" font-size="9" font-family="{MONO}">spans four libraries by design</text>'
    b += f'<rect x="300" y="472" width="20" height="12" rx="2" fill="rgba(245,245,245,0.14)" stroke="rgba(245,245,245,0.30)"/>'
    b += f'<rect x="324" y="472" width="20" height="12" rx="2" fill="rgba(245,245,245,0.04)" stroke="rgba(245,245,245,0.30)"/>'
    b += f'<text x="352" y="481" fill="{MUTED}" font-size="9" font-family="{MONO}">stronger contrast is larger · third line = files per library</text>'
    b += f'<text x="956" y="462" fill="{MUTED}" font-size="8" font-family="{MONO}" text-anchor="end">AREA = LOC · {total:,} LOC IN {C["files"]} PY/SH FILES · 2026-11-03</text>'
    return svg("lunits", "Move units: code that must stay together",
               "Louvain clusters of the file graph, sized by lines of code; each unit moves as one piece.", 1000, 500, b)


def units_table():
    th = "".join(f"<th>{h}</th>" for h in ["Unit", "Files", "LOC", "Ships as", "Why it stays together", "Cut at the seam"])
    rows = ""
    for name, files, loc, libs, ships, why, cut in UM:
        tag = ' <span class="tag">focal</span>' if name == "Push-IK runtime" else ""
        rows += (f'<tr><td><b>{name}</b>{tag}</td><td class="m">{len(files)}</td><td class="m">{loc:,}</td>'
                 f"<td>{ships}</td><td>{why}</td><td>{cut}</td></tr>")
    return f'<div class="wrap"><table><tr>{th}</tr>{rows}</table></div>'


# ---------- library table ----------
ROWS = [  # lib, target package, contents, may import
    ("common", "k1_common", "joints, gains, obs/action layout, policy manifest, <code>resolve_model()</code>, <code>k1_constants</code>, <code>k1_wiring</code>, k1_interfaces, k1_description", "nothing"),
    ("utils", "k1_utils", "mujoco_eval, height gate, ckpt inspect + migrate, panel video, ppo_guard, <code>isaac_ros_env</code>", "common"),
    ("runtime", "k1_runtime", "<b>new:</b> <code>wbc.py</code>, <code>push_ik_core</code>, <code>ds4</code>, <code>k1_arm_ik</code>, shared half of <code>k1_gamepad_deploy</code> (gains, Walker, ArmJog, Gamepad)", "common"),
    ("rl_isaac", "k1_rl_isaac", "isaac_tasks/k1_velocity, compass_k1, k1_kicking, booster_train, <code>src/k1_sim_isaac</code>, its launchers and tests", "common, utils, runtime"),
    ("rl_mj", "k1_rl_mj", "mjlab_k1/src tasks_* (track, YOLO-kick included), scripts_* as CLI, MAPPO, its launchers", "common, utils, runtime"),
    ("mimic", "k1_mimic", "k1m pipeline + service + Gradio <code>app.py</code>, GVHMR/GMR/SOMA/Kimodo, motion_feasibility_gate", "common, utils"),
    ("teleop", "k1_teleop", "XR teleop node + mapping, HMD poser, PhaseSpace push-IK", "common, utils, runtime"),
    ("perception", "k1_perception", "whole SLAM chain: cuVSLAM node, TCP relay + rx, nvblox stream + rx, grid map, map_run", "common, data"),
    ("vla", "k1_vla", "k1_chat agent with its console (wt-k1-tools), YOLO node, voice/VLM tools", "common, utils, runtime"),
    ("data", "k1_data", "rosbag + stereo/walk tooling, real_robot converters", "common"),
    ("deploy_robot", "deploy_robot", "<code>run_robot</code> half of k1_gamepad_deploy, tf_service, watchdog, on-robot recorders", "common, runtime, perception, data"),
    ("deploy_laptop", "deploy_laptop", "ROS 2 k1_* packages, push_ik_web + push_ik_sim, pad_udp_send", "common, runtime, teleop, perception"),
    ("web_console", "web_console", "fleet_dashboard, depth_sbs; one shell, plugin pages served by each library", "any L2 over HTTP/WS only"),
    ("ops", "ops", "docker, hosts/*.yaml, jobs runner, CI; 64 scripts left from 113", "CLI entry points only"),
    ("tests", "per package", "3 cross-cutting tests left; 26 followed their library", "its own package"),
]


def table():
    th = "".join(f"<th>{h}</th>" for h in ["Library", "Contents", "May import", "Files", "LOC", "Out-edges", "Joint lists", "sys.path", "Untracked"])
    rows = ""
    for lib, pkg, what, allowed in ROWS:
        g = lambda k: D[k].get(lib, 0)
        out = sum(e["n"] for e in D["edges"] if e["from"] == lib)
        tag = ' <span class="tag">new</span>' if lib == "runtime" else ""
        rows += (f"<tr><td><code>{pkg}</code>{tag}</td><td>{what}</td><td class=\"m\">{allowed}</td>"
                 + "".join(f'<td class="m">{v}</td>' for v in (g("files"), g("loc"), out, g("joint_lists"), g("sys_path"), g("untracked")))
                 + "</tr>")
    return f'<div class="wrap"><table><tr>{th}</tr>{rows}</table></div>'


tpl = Path(sys.argv[1]).read_text()
out = (tpl.replace("{{L1}}", fig_matrix()).replace("{{L2}}", fig_layers())
          .replace("{{L3}}", fig_flow()).replace("{{L4}}", fig_deploy())
          .replace("{{LTABLE}}", table()).replace("{{LUNITS}}", fig_units()).replace("{{UTABLE}}", units_table()))
Path(sys.argv[2]).write_text(out)
print("wrote", sys.argv[2], len(out))

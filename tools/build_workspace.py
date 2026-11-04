#!/usr/bin/env python3
"""Generate the k1-* library repos from ~/Projects/booster_ws (read-only source).

    python3 tools/build_workspace.py [--src ~/Projects/booster_ws] [--chat ~/Projects/wt-k1-tools] [--out libs]

Steps: membership (docs/decoupling/lib_deps.py rules) -> place files -> split k1_gamepad_deploy
-> rewrite imports / drop sys.path hacks -> pyproject + README per repo -> docs/migration_map.tsv.
Idempotent: wipes <out> first. Never writes to the source trees.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--src", default=str(Path.home() / "Projects/booster_ws"))
ap.add_argument("--chat", default=str(Path.home() / "Projects/wt-k1-tools"))
ap.add_argument("--out", default=str(HERE / "libs"))
args = ap.parse_args()
SRC, CHAT, OUT = Path(args.src), Path(args.chat), Path(args.out)

OWNER = "thdhyan"
REPOS = {  # lib key -> (repo name, python package, layer, may-import, one-line purpose)
    "common": ("k1-common", "k1_common", "L0", [], "Robot contract: joints, gains, obs/action layout, wiring, motion-clip schema."),
    "description": ("k1-description", "k1_description", "L0", [], "K1 URDF / MJCF / USD description (ROS 2 package); meshes via the booster_assets submodule."),
    "utils": ("k1-utils", "k1_utils", "L1", ["common"], "Eval gates, checkpoint inspect/migrate, parity checks, Isaac ROS env helper."),
    "runtime": ("k1-runtime", "k1_runtime", "L1", ["common"], "Torch/numpy-only policy runtime: WBC, push-IK core, arm IK, DS4 pad, gamepad core."),
    "rl_isaac": ("k1-rl-isaac", "k1_velocity", "L2", ["common", "utils", "runtime"], "Isaac Lab tasks (velocity, push, kick, COMPASS) and Isaac sim nodes."),
    "rl_mj": ("k1-rl-mj", "mjlab_k1", "L2", ["common", "utils", "runtime"], "mjlab (MuJoCo Warp) tasks, probes and train/play CLI."),
    "mimic": ("k1-mimic", "k1m", "L2", ["common", "utils"], "Video/text -> K1 motion retargeting pipeline (GVHMR, GMR, SOMA, Kimodo) + Gradio UI."),
    "teleop": ("k1-teleop", "k1_teleop", "L2", ["common", "utils", "runtime"], "XR / PhaseSpace teleop nodes, HMD poser, mapping."),
    "perception": ("k1-perception", "k1_perception", "L2", ["common", "data"], "SLAM chain: cuVSLAM, TCP relay, nvblox stream, grid map."),
    "vla": ("k1-vla", "k1_chat", "L2", ["common", "utils", "runtime"], "k1_chat voice/VLM agent, tools, YOLO node."),
    "data": ("k1-data", "k1_data", "L2", ["common"], "Rosbag, stereo/walk tooling, real-robot converters."),
    "deploy_robot": ("k1-deploy-robot", "k1_deploy_robot", "L3", ["common", "runtime", "perception", "data"], "Runs on the K1 CPU: policy runner, TF service, watchdog, recorders."),
    "deploy_laptop": ("k1-deploy-laptop", "k1_deploy_laptop", "L3", ["common", "runtime", "teleop", "perception"], "ROS 2 jazzy workspace, push-IK web/sim, pad sender, sim-to-sim."),
    "web_console": ("k1-web-console", "k1_web_console", "L3", [], "Fleet dashboard, camera tools; one web shell, plugin pages over HTTP/WS."),
    "ops": ("k1-ops", "k1_ops", "L3", [], "Host launchers, containers, CI, job chains."),
}

# ---------------------------------------------------------------- membership
deps_json = HERE / "docs/_membership.json"
subprocess.run([sys.executable, "-I", str(SRC / "docs/decoupling/lib_deps.py"), str(SRC), str(CHAT)],
               stdout=open(deps_json, "w"), check=True)
members = json.load(open(deps_json))["members"]
deps_json.unlink()

file_lib = {}  # key ("path" or "chat:path") -> lib
for lib, keys in members.items():
    for k in keys:
        file_lib[k] = "description" if k.startswith("src/k1_description/") else lib
# tests that were not claimed by a library stay in the umbrella
UMBRELLA = "umbrella"
for k, lib in list(file_lib.items()):
    if lib == "tests":
        file_lib[k] = UMBRELLA


def src_path(key):
    return CHAT / key[5:] if key.startswith("chat:") else SRC / key


# ---------------------------------------------------------------- destination rules
def dest(lib, key):
    """Destination path inside the repo. Preserve relative paths unless a Python package is imported."""
    p = key[5:] if key.startswith("chat:") else key
    chat = key.startswith("chat:")
    base = os.path.basename(p)
    pkg = REPOS[lib][1] if lib in REPOS else None
    R = [
        ("common", r"mjlab_k1/src/mjlab_k1/k1_constants\.py$", "src/k1_common/k1_constants.py"),
        ("common", r"scripts/k1_wiring\.py$", "src/k1_common/k1_wiring.py"),
        ("common", r"k1m/schema\.py$", "src/k1_common/clip_schema.py"),
        ("common", r"src/k1_interfaces/(.*)", r"ros/k1_interfaces/\1"),
        ("description", r"src/k1_description/(.*)", r"\1"),
        ("utils", r"k1_teleop/isaac_ros_env\.py$", "src/k1_utils/isaac_ros_env.py"),
        ("utils", r"scripts/([^/]+\.py)$", r"src/k1_utils/\1"),
        ("runtime", r"mjlab_k1/src/mjlab_k1/wbc\.py$", "src/k1_runtime/wbc.py"),
        ("runtime", r"mjlab_k1/deploy/(push_ik_core|ds4)\.py$", r"src/k1_runtime/\1.py"),
        ("runtime", r"k1_teleop/k1_arm_ik\.py$", "src/k1_runtime/k1_arm_ik.py"),
        ("rl_isaac", r"isaac_tasks/[^/]+/source/(.*)", r"src/\1"),
        ("rl_isaac", r"isaac_tasks/[^/]+/scripts/(.*)", r"scripts/\1"),
        ("rl_isaac", r"isaac_tasks/[^/]+/(README\.md|setup\.cfg|pyproject\.toml)$", r"docs/legacy_\1"),
        ("rl_isaac", r"compass_k1/(.*)", r"src/compass_k1/\1"),
        ("rl_isaac", r"src/k1_sim_isaac/(.*)", r"ros/k1_sim_isaac/\1"),
        ("rl_isaac", r"scripts/([^/]+\.sh)$", r"jobs/\1"),
        ("rl_mj", r"mjlab_k1/src/mjlab_k1/(.*)", r"src/mjlab_k1/\1"),
        ("rl_mj", r"mjlab_k1/scripts_([^/]+)$", r"scripts/\1"),
        ("rl_mj", r"mjlab_k1/(test|tests)/(.*)", r"tests/\2"),
        ("rl_mj", r"scripts/([^/]+\.sh)$", r"jobs/\1"),
        ("mimic", r"k1m/(.*)", r"src/k1m/\1"),
        ("mimic", r"app\.py$", "src/k1m/app.py"),
        ("mimic", r"k1_teleop/soma_retarget_node\.py$", "src/k1m/soma_retarget_node.py"),
        ("mimic", r"docker/k1m_service\.py$", "service/k1m_service.py"),
        ("teleop", r"k1_teleop/(.*)", r"src/k1_teleop/\1"),
        ("teleop", r"mjlab_k1/deploy/push_ik_phasespace\.py$", "src/k1_teleop/push_ik_phasespace.py"),
        ("teleop", r"mjlab_k1/(test|tests)/(.*)", r"tests/\2"),
        ("vla", r"k1_teleop/yolo_node\.py$", "src/k1_chat/yolo_node.py"),
        ("deploy_robot", r"mjlab_k1/deploy/k1_gamepad_deploy\.py$", "deploy/k1_gamepad_deploy.py"),
        ("deploy_robot", r"mjlab_k1/(test|tests)/(.*)", r"tests/\2"),
        ("deploy_robot", r"src/k1_control/k1_control/(sdk_bridge_node\.(py|cpp))$", r"sdk_bridge/\1"),
        ("deploy_laptop", r"mjlab_k1/deploy/(.*)", r"deploy/\1"),
        ("deploy_laptop", r"mjlab_k1/(test|tests)/(.*)", r"tests/\2"),
        ("deploy_laptop", r"src/(k1_[a-z_]+/.*)", r"src/\1"),
    ]
    for rl, pat, tpl in R:
        if rl != lib:
            continue
        m = re.match(pat, p)
        if m:
            return m.expand(tpl)
    if lib in ("rl_isaac", "rl_mj", "mimic", "teleop", "deploy_robot", "deploy_laptop", "utils", "runtime", "common"):
        if p.startswith("tests/"):
            return p
    if lib == "vla":
        m = re.match(r"src/k1_chat/(.*)", p)
        if m:
            return f"src/k1_chat/{m.group(1)}"
        return p  # robot/, scripts/, tools/ keep their layout (own repo)
    if lib == UMBRELLA:
        return p
    # keep original relative path: scripts/, docker/, real_robot/, tools/, .github/, docs/velocity_grid/
    return p


# ---------------------------------------------------------------- non-code companions
COMP_EXT = {".md", ".yaml", ".yml", ".json", ".toml", ".cfg", ".xml", ".urdf", ".xacro", ".msg", ".srv", ".txt",
            ".cmake", ".rviz", ".service", ".launch", ".sdf", ".world", ".ini", ".example", ".css"}
COMP_NAMES = {"CMakeLists.txt", "package.xml", "setup.cfg", "Dockerfile", ".gitignore"}
COMP_SKIP = ("uv.lock", "MUJOCO_LOG", ".env", "__pycache__", "/outputs/", "/runs/", "/wandb/", "/videos/", "egg-info",
             "/build/", "/logs/", "/log/", "/install/", "audio_dumps", "k1_description/assets/", "booster_train_ref",
             "graphify-out", "docs/decoupling/", "/vendor/", "slam_runs/")
COMP_ROOTS = [(SRC, p) for p in ("isaac_tasks", "mjlab_k1", "k1_teleop", "k1m", "src", "real_robot", "scripts",
                                 "docker", "tools", "compass_k1", "tests", ".github", "docs/velocity_grid")]
CAP_BYTES = 500_000


def tracked_or_untracked(base, sub):
    r = subprocess.run(["git", "-C", str(base), "ls-files", "-co", "--exclude-standard", sub],
                       capture_output=True, text=True)
    return [x for x in r.stdout.split("\n") if x]


def is_companion(rel, p):
    if any(s in "/" + rel for s in COMP_SKIP):
        return False
    if not p.is_file() or p.stat().st_size > CAP_BYTES:
        return False
    return p.suffix in COMP_EXT or p.name in COMP_NAMES


def lib_for_dir(rel, dir_votes):
    d = os.path.dirname(rel)
    while True:
        if d in dir_votes:
            return dir_votes[d].most_common(1)[0][0]
        if d in ("", "."):
            return None
        d = os.path.dirname(d)


dir_votes = defaultdict(Counter)
for k, lib in file_lib.items():
    if lib in ("tests", UMBRELLA):
        continue
    kk = k[5:] if k.startswith("chat:") else k
    if k.startswith("chat:"):
        continue
    d = os.path.dirname(kk)
    while True:
        dir_votes[d][lib] += 1
        if d in ("", "."):
            break
        d = os.path.dirname(d)
# a directory votes only if it is not the repo root / top-level folder with mixed ownership: use deepest-first lookups

plan = {}  # (lib, dest) -> (src Path, key)
for k, lib in file_lib.items():
    d = dest(lib, k)
    plan[(lib, d)] = (src_path(k), k)

skipped_comp = []
for base, sub in COMP_ROOTS:
    for rel in tracked_or_untracked(base, sub):
        p = base / rel
        if rel in file_lib or not is_companion(rel, p):
            continue
        if rel.startswith("src/k1_description/"):
            lib = "description"
        elif rel.startswith("src/k1_sim_isaac/"):
            lib = "rl_isaac"
        elif rel.startswith("src/k1_interfaces/"):
            lib = "common"
        elif rel.startswith("src/k1_control/") and "sdk_bridge" in rel:
            lib = "deploy_robot"
        elif rel.startswith(("isaac_tasks/", "compass_k1/")):
            lib = "rl_isaac"
        elif rel.startswith("mjlab_k1/") and not rel.startswith("mjlab_k1/deploy/") and not rel.startswith("mjlab_k1/src/"):
            lib = "rl_mj"
        elif rel.startswith("mjlab_k1/deploy/"):
            lib = "deploy_laptop"
        elif rel.startswith("mjlab_k1/src/"):
            lib = "rl_mj"
        elif rel.startswith("tests/"):
            lib = UMBRELLA
        elif rel.startswith(("scripts/", "docker/", ".github/")):
            lib = "ops"
        else:
            lib = lib_for_dir(rel, dir_votes)
        if lib is None:
            skipped_comp.append(rel)
            continue
        if lib == "rl_mj" and rel.endswith(("pyproject.toml",)):
            continue  # regenerated
        try:
            d = dest(lib, rel)
        except Exception:
            skipped_comp.append(rel)
            continue
        plan.setdefault((lib, d), (p, rel))

# chat worktree companions (own repo layout, kept as is)
for rel in tracked_or_untracked(CHAT, "."):
    p = CHAT / rel
    if rel.startswith(("src/", "tools/", "robot/", "scripts/", "docs/", "tests/")) or rel in (
            "README.md", "PLAN.md", "PLAN_TOOLS.md", "HANDOFF.md", "fleet.json", ".env.example", ".gitignore"):
        if is_companion(rel, p) and ("vla", rel) not in plan and "chat:" + rel not in file_lib:
            plan.setdefault(("vla", rel if not rel.startswith("tests/") else rel), (p, "chat:" + rel))
# chat tests (python) belong to vla
for rel in tracked_or_untracked(CHAT, "tests"):
    p = CHAT / rel
    if p.is_file() and p.suffix == ".py" and "__pycache__" not in rel:
        plan.setdefault(("vla", rel), (p, "chat:" + rel))

# ---------------------------------------------------------------- write files
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
migration = []
for (lib, d), (sp, key) in sorted(plan.items()):
    repo = OUT / (REPOS[lib][0] if lib in REPOS else "_umbrella")
    t = repo / d
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sp, t)
    migration.append((key, lib, d))

# ---------------------------------------------------------------- split k1_gamepad_deploy
gd = (SRC / "mjlab_k1/deploy/k1_gamepad_deploy.py").read_text()
i_run_sim = gd.index("\ndef run_sim(args):")
i_robot_mark = gd.index("# ---------------------------------------------------------------- robot")
i_run_robot = gd.index("\ndef run_robot(args):")
i_main = gd.index('\nif __name__ == "__main__":')
i_hdr_end = gd.index("from __future__ import annotations")
header_doc = gd[:i_hdr_end]
core_body = gd[i_hdr_end:i_run_sim] + "\n\n" + gd[i_robot_mark:i_run_robot]
sim_body = gd[i_run_sim:i_robot_mark]
robot_body = gd[i_run_robot:i_main]
main_body = gd[i_main:]

(OUT / "k1-runtime/src/k1_runtime").mkdir(parents=True, exist_ok=True)
core_doc = ('"""Shared half of the K1 gamepad deploy: gains, Walker, Body FSM, ArmJog, Gamepad (evdev / K1 remote / UDP / keyboard).\n\n'
            'Split out of mjlab_k1/deploy/k1_gamepad_deploy.py. The robot runner (k1-deploy-robot) and the laptop sim-to-sim\n'
            '(k1-deploy-laptop) both import this module; torch + numpy only.\n"""\n')
(OUT / "k1-runtime/src/k1_runtime/gamepad_core.py").write_text(core_doc + core_body.rstrip() + "\n")
migration.append(("mjlab_k1/deploy/k1_gamepad_deploy.py (shared half)", "runtime", "src/k1_runtime/gamepad_core.py"))

core_names = set()
for n in ast.parse(core_body).body:
    if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
        core_names.add(n.name)
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            for x in ast.walk(t):
                if isinstance(x, ast.Name):
                    core_names.add(x.id)


def free_names(body):
    mod = ast.parse(body)
    defined = set(dir(__builtins__)) | set()
    for n in ast.walk(mod):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defined.add(n.name)
            if isinstance(n, ast.FunctionDef):
                for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs:
                    defined.add(a.arg)
                if n.args.vararg:
                    defined.add(n.args.vararg.arg)
                if n.args.kwarg:
                    defined.add(n.args.kwarg.arg)
        elif isinstance(n, ast.Lambda):
            for a in n.args.args:
                defined.add(a.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            defined.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                defined.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            defined.add(n.name)
        elif isinstance(n, ast.arg):
            defined.add(n.arg)
    return {n.id for n in ast.walk(mod) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined}


def derived(body, doc, name_doc, with_main=None):
    body = re.sub(r"(?<![\w.])CAP\b", "_core.CAP", body)
    need = sorted((free_names(body) & core_names) - {"CAP", "wbc"})
    stdlib_imports = ("import argparse\nimport math\nimport sys\nimport threading\nimport time\nfrom pathlib import Path\n\n"
                      "import numpy as np\nimport torch\n\n")
    imp = ("from k1_runtime import gamepad_core as _core\nfrom k1_runtime import wbc\n"
           "from k1_runtime.gamepad_core import (  # noqa: F401\n" + "".join(f"    {n},\n" for n in need) + ")\n\n")
    return doc + "from __future__ import annotations\n\n" + stdlib_imports + imp + body


robot_doc = ('"""K1 robot runner (runs on the robot CPU): walk the real K1 from a gamepad with the mjlab walk base.\n\n'
             'Shared pieces (gains, Walker, Body, Gamepad, ArmJog) live in k1_runtime.gamepad_core; sim-to-sim moved to\n'
             'k1-deploy-laptop (gamepad_sim.py). Usage on the robot:\n'
             '    source /opt/booster/BoosterRos2Interface/install/setup.bash\n'
             '    python3 k1_gamepad_deploy.py --policy walk.pt --udp 9870 [--dry] [--task] [--getup getup.pt]\n"""\n')
robot_main = main_body.replace('  ap.add_argument("--sim", action="store_true", help="MuJoCo sim-to-sim with a scripted stick")\n', "")
for opt in ("--video", "--pad", "--terrain"):
    robot_main = re.sub(r'  ap\.add_argument\("%s".*?\n(?:\s{18}.*\n)?' % opt, "", robot_main)
robot_main = robot_main.replace("  CAP = tuple(a.cap)", "  _core.CAP = tuple(a.cap)").replace(
    "sys.exit(run_sim(a) if a.sim else run_robot(a))", "sys.exit(run_robot(a))")
robot_main = re.sub(r"(?<![\w.])CAP\b", "_core.CAP", robot_main)
robot_main = robot_main.replace("default=_core.CAP", "default=_core.CAP")
rb = OUT / "k1-deploy-robot/deploy/k1_gamepad_deploy.py"
rb.parent.mkdir(parents=True, exist_ok=True)
rb.write_text(derived(robot_body + robot_main, robot_doc, "robot"))

sim_doc = ('"""Sim-to-sim for the K1 walk base: MuJoCo K1_22dof_mjlab.xml, scripted stick or live gamepad (viewer), get-up FSM test.\n\n'
           'Split out of mjlab_k1/deploy/k1_gamepad_deploy.py (--sim). Usage:\n'
           '    python gamepad_sim.py --policy flat_swing10.pt [--video walk.mp4] [--pad] [--terrain rough] [--getup getup.pt]\n"""\n')
sim_main = '''

if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("--policy", required=True, help="mjlab walk-base rsl-rl checkpoint (model_*.pt)")
  ap.add_argument("--video", help="write an mp4")
  ap.add_argument("--pad", action="store_true", help="drive live with the gamepad in the viewer")
  ap.add_argument("--terrain", choices=("flat", "rough"), default="flat",
                  help="rough = rough_heights() field (rough +x, stairs -x, slope +y, waves -y)")
  ap.add_argument("--keyboard", action="store_true", help="drive from this terminal's keyboard (with --pad)")
  ap.add_argument("--cap", type=float, nargs=3, default=_core.CAP, metavar=("VX", "VY", "WZ"), help="command limits (m/s, rad/s)")
  ap.add_argument("--getup", help="Mjlab-GetUp checkpoint: fall -> get-up FSM instead of Damping")
  a = ap.parse_args()
  _core.CAP = tuple(a.cap)
  sys.exit(run_sim(a))
'''
sm = OUT / "k1-deploy-laptop/deploy/gamepad_sim.py"
sm.parent.mkdir(parents=True, exist_ok=True)
sm.write_text(derived(sim_body, sim_doc, "sim") + sim_main)
migration.append(("mjlab_k1/deploy/k1_gamepad_deploy.py (run_sim*)", "deploy_laptop", "deploy/gamepad_sim.py"))
# the robot copy copied above by the plan is replaced by the derived one
migration = [m for m in migration if not (m[0] == "mjlab_k1/deploy/k1_gamepad_deploy.py")]
migration.append(("mjlab_k1/deploy/k1_gamepad_deploy.py (run_robot)", "deploy_robot", "deploy/k1_gamepad_deploy.py"))

# ---------------------------------------------------------------- rewrite imports
# (old dotted/bare module) -> new import statement target
MODMAP = {
    "k1_constants": "k1_common.k1_constants", "mjlab_k1.k1_constants": "k1_common.k1_constants",
    "k1_wiring": "k1_common.k1_wiring", "k1m.schema": "k1_common.clip_schema",
    "wbc": "k1_runtime.wbc", "mjlab_k1.wbc": "k1_runtime.wbc",
    "push_ik_core": "k1_runtime.push_ik_core", "ds4": "k1_runtime.ds4",
    "k1_arm_ik": "k1_runtime.k1_arm_ik", "k1_teleop.k1_arm_ik": "k1_runtime.k1_arm_ik",
    "k1_teleop.isaac_ros_env": "k1_utils.isaac_ros_env", "isaac_ros_env": "k1_utils.isaac_ros_env",
    "k1_gamepad_deploy": "k1_runtime.gamepad_core",
}
SYSPATH_HINT = re.compile(r"mjlab_k1|deploy|\"source\"|'source'|k1_velocity|\bREPO\b|\bWS\b|\bROOT\b|\bSCRIPTS\b|\bDEPLOY\b|scripts")
rewrites = Counter()
removed_syspath = 0


def rewrite_py(path, lib):
    global removed_syspath
    s = path.read_text(errors="replace")
    o = s
    rel_pkg = lambda m: MODMAP.get(m)
    # relative: from .k1_constants import X / from .wbc import X (inside mjlab_k1)
    def rel(m):
        mod = m.group(2)
        new = MODMAP.get(mod)
        return f"{m.group(1)}from {new} import" if new else m.group(0)
    s = re.sub(r"^(\s*)from \.(k1_constants|wbc) import", rel, s, flags=re.M)
    # from X import ...
    def frm(m):
        mod, names = m.group(2), m.group(3)
        if mod == "k1_gamepad_deploy" and lib in ("deploy_robot",):
            return m.group(0)
        new = MODMAP.get(mod)
        if mod in ("mjlab_k1", "k1_teleop") and False:
            return m.group(0)
        return f"{m.group(1)}from {new} import {names}" if new else m.group(0)
    s = re.sub(r"^(\s*)from ([\w.]+) import ([^\n]*)", frm, s, flags=re.M)
    # from mjlab_k1 import k1_constants  /  from k1_teleop import k1_arm_ik
    s = re.sub(r"^(\s*)from (mjlab_k1) import (k1_constants|wbc)\b", lambda m: f"{m.group(1)}from {MODMAP[m.group(3)].rsplit('.', 1)[0]} import {m.group(3)}", s, flags=re.M)
    s = re.sub(r"^(\s*)from (k1_teleop) import (k1_arm_ik)\b", r"\1from k1_runtime import k1_arm_ik", s, flags=re.M)
    s = re.sub(r"^(\s*)from (k1_teleop) import (isaac_ros_env)\b", r"\1from k1_utils import isaac_ros_env", s, flags=re.M)
    # import X [as Y]
    def imp(m):
        mod, alias = m.group(2), m.group(3)
        if mod == "k1_gamepad_deploy" and lib == "deploy_robot":
            return m.group(0)
        new = MODMAP.get(mod)
        if not new:
            return m.group(0)
        pkg, name = new.rsplit(".", 1)
        as_ = alias or ""
        if as_:
            return f"{m.group(1)}from {pkg} import {name}{as_}{m.group(4)}"
        return f"{m.group(1)}from {pkg} import {name}{m.group(4)}"
    s = re.sub(r"^(\s*)import ([\w.]+)( as \w+)?([^\n]*)$", imp, s, flags=re.M)
    # drop top-level sys.path.insert(...) statements that pointed at now-moved siblings
    try:
        tree = ast.parse(s)
    except SyntaxError:
        tree = None
    if tree:
        lines = s.split("\n")
        kill = []
        for n in tree.body:
            if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                    and n.value.func.attr == "insert" and "sys.path" in ast.unparse(n.value.func.value)):
                seg = "\n".join(lines[n.lineno - 1:n.end_lineno])
                if SYSPATH_HINT.search(seg):
                    kill.append((n.lineno, n.end_lineno))
        for a, b in reversed(kill):
            del lines[a - 1:b]
            removed_syspath += 1
        s = "\n".join(lines)
    if s != o:
        rewrites[lib] += 1
        path.write_text(s)


for lib, (repo, *_r) in REPOS.items():
    for p in (OUT / repo).rglob("*.py"):
        if "k1_runtime/gamepad_core.py" in str(p):
            rewrite_py(p, lib)
            continue
        rewrite_py(p, lib)
# umbrella tests
for p in (OUT / "_umbrella").rglob("*.py"):
    rewrite_py(p, UMBRELLA)

# aliasing: `from k1_runtime.gamepad_core import ArmJog` fine; `import k1_gamepad_deploy as D` -> `from k1_runtime import gamepad_core as D`
# (handled by the generic import rule: name = gamepad_core)

# scripts_X references -> scripts/X in rl_mj
rlmj = OUT / "k1-rl-mj"
for p in rlmj.rglob("*"):
    if p.is_file() and p.suffix in (".sh", ".py", ".md", ".txt"):
        t = p.read_text(errors="replace")
        n = re.sub(r"mjlab_k1/scripts_(\w+)\.py", r"scripts/\1.py", t)
        n = re.sub(r"\bscripts_(\w+)\.py", r"scripts/\1.py", n)
        if n != t:
            p.write_text(n)

json.dump({"rewritten_files": rewrites, "sys_path_removed": removed_syspath, "skipped_companions": skipped_comp},
          open(HERE / "docs/build_report.json", "w"), indent=1)

# ---------------------------------------------------------------- migration map
mm = HERE / "docs/migration_map.tsv"
mm.parent.mkdir(exist_ok=True)
with open(mm, "w") as f:
    f.write("source (booster_ws)\tlibrary\tnew path\n")
    for key, lib, d in sorted(migration, key=lambda x: (x[1], x[2])):
        name = REPOS[lib][0] if lib in REPOS else "k1-workspace"
        f.write(f"{key}\t{name}\t{d}\n")
print(f"files placed: {len(migration)}; rewritten: {dict(rewrites)}; sys.path removed: {removed_syspath}; "
      f"skipped companions: {len(skipped_comp)}")

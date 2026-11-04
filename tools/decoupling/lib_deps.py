"""Map booster_ws files to proposed libraries and measure cross-library deps.

Usage: python3 lib_deps.py [repo_root] [k1_chat_worktree] > lib_deps.json
An edge is a Python import resolved to a file of another library, or a
hard-coded path string pointing into another library's folder.
"""
import ast
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CHAT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None

SKIP = ("sdk/", "install/", "build/", "log/", "logs/", "wandb/", ".venv/", "models/",
        "videos/", "assets/", "patches/", "graphify-out/", "k1m_out", ".git/",
        "src/k1_description/assets/", "isaac_tasks/booster_train_ref/", "docs/decoupling/")

# First match wins. Order matters: specific files before folders.
RULES = [
    # common: the robot contract
    (r"mjlab_k1/src/mjlab_k1/k1_constants\.py", "common"),
    (r"scripts/k1_wiring\.py", "common"),
    (r"src/k1_interfaces/", "common"),
    (r"src/k1_description/", "common"),
    (r"k1m/schema\.py", "common"),
    # runtime: torch/numpy-only code shared by robot, laptop, sim and web (move unit "push-IK runtime")
    (r"mjlab_k1/src/mjlab_k1/wbc\.py", "runtime"),
    (r"mjlab_k1/deploy/(push_ik_core|ds4)\.py", "runtime"),
    (r"mjlab_k1/(tests/test_wbc|test/test_arm_ik)\.py", "runtime"),
    (r"k1_teleop/k1_arm_ik\.py", "runtime"),  # pure-math arm IK: teleop + Isaac teleop sim
    (r"k1_teleop/isaac_ros_env\.py", "utils"),
    (r"scripts/(flatten_k1|probe_k1)", "rl_isaac"),  # import booster_train assets
    (r"app\.py$", "mimic"),  # k1m Gradio UI, imports k1m.pipeline: a mimic plugin page
    # tests pinned to the side they exercise
    (r"mjlab_k1/tests/test_deploy\.py", "deploy_robot"),
    (r"mjlab_k1/test/test_push_ik_web\.py", "deploy_laptop"),
    (r"mjlab_k1/test/test_push_ik_node\.py", "teleop"),
    # mjlab tasks stay in rl_mj even when they serve mimic/VLA (they import env_cfg, frozen_base, mdp)
    (r"mjlab_k1/src/mjlab_k1/tasks_track\.py", "rl_mj"),
    (r"mjlab_k1/scripts_(track|carry_clips|kick_yolo)", "rl_mj"),
    # web-console
    (r"tools/fleet_dashboard/", "web_console"),
    (r"tools/k1_camera/", "web_console"),
    (r"docker/k1m_ui\.py", "web_console"),
    (r"docs/velocity_grid/", "web_console"),
    # k1_chat console/debug stay in vla: brain.py and llm.py import them (web_console embeds over HTTP)
    # mimic (motion retargeting)
    (r"k1m/", "mimic"),
    (r"docker/(k1m_service\.py|Dockerfile\.k1m)", "mimic"),
    (r"scripts/(gmr_|soma_|mk_soma|motion_feasibility|record_k1_motion)", "mimic"),
    (r"scripts/spark_(gmr|soma|gvhmr|kimodo|k1m|t2m|video|smplx)", "mimic"),
    (r"k1_teleop/soma_retarget_node\.py", "mimic"),
    # VLA / voice
    (r"chat:", "vla"),
    (r"k1_teleop/yolo_node\.py", "vla"),
    # perception / SLAM
    # one SLAM unit, robot side + laptop side (relay <-> rx are a cycle by path refs)
    (r"real_robot/slam_", "perception"),
    (r"real_robot/map_run/", "perception"),
    (r"docker/Dockerfile\.nvblox", "perception"),
    # deploy_robot: runs on the K1's own CPU
    (r"mjlab_k1/deploy/k1_gamepad_deploy\.py", "deploy_robot"),
    (r"real_robot/(tf_service|watchdog|install_watchdog|k1_stereo_record|k1_walk_record|rosbag_record|record_session)", "deploy_robot"),
    (r"src/k1_control/k1_control/sdk_bridge", "deploy_robot"),
    # data tools
    (r"real_robot/", "data"),
    # teleop
    (r"k1_teleop/", "teleop"),
    (r"mjlab_k1/deploy/push_ik_phasespace", "teleop"),
    (r"docker/Dockerfile\.teleop-xr", "teleop"),
    # deploy_laptop: ROS + gamepad side
    (r"mjlab_k1/deploy/", "deploy_laptop"),
    # Isaac sim nodes run in Isaac Sim's own ROS env and import velocity_env_cfg: they ship with rl_isaac
    (r"src/k1_sim_isaac/", "rl_isaac"),
    (r"src/k1_", "deploy_laptop"),
    # RL backends
    (r"mjlab_k1/", "rl_mj"),
    (r"scripts/(spark_mjlab|zzbw_mjlab|dl_mjlab)", "rl_mj"),
    (r"isaac_tasks/", "rl_isaac"),
    (r"compass_k1/", "rl_isaac"),
    (r"tests/", "tests"),
    # utils: generic training/eval helpers
    (r"scripts/(eval_push|reward_probe|zero_step_check|gait_gate)", "rl_isaac"),  # import k1_velocity / booster_train tasks; gait_gate wraps the isaac copy
    (r"scripts/(mujoco_eval|gait_gate|height_gate|zero_step|inspect_ppo|migrate_ppo|push_export)", "utils"),
    # ops: host launchers, containers, CI
    (r"scripts/", "ops"),
    (r"docker/", "ops"),
    (r"\.github/", "ops"),
]

FOLDER_OWNER = {  # path string prefix -> library, for hard-coded path refs
    "isaac_tasks/": "rl_isaac", "mjlab_k1/deploy/": "deploy_laptop", "mjlab_k1/": "rl_mj",
    "src/k1_description": "common", "k1_teleop/": "teleop", "real_robot/": "data",
    "k1m/": "mimic", "scripts/": "ops", "tools/": "web_console", "compass_k1": "rl_isaac",
}


def lib_of(rel):
    for pat, lib in RULES:
        if re.match(pat, rel) or (pat.startswith("chat:") and rel.startswith("chat:") and re.match(pat, rel)):
            return lib
    return None


def walk(base, prefix=""):
    out = {}
    ls = subprocess.run(["git", "-C", str(base), "ls-files", "-co", "--exclude-standard"],
                        capture_output=True, text=True).stdout.split("\n")
    for rel in filter(None, ls):
        p = base / rel
        if "__pycache__" in rel or not p.is_file():
            continue
        if any(rel.startswith(s) for s in SKIP) or p.suffix not in (".py", ".sh", ".html", ".js", ".cpp"):
            continue
        key = prefix + rel
        lib = lib_of(key)
        if lib:
            out[key] = (p, lib)
    return out


files = walk(ROOT)
if CHAT:
    files.update({k: v for k, v in walk(CHAT, "chat:").items()
                  if k.startswith(("chat:src/", "chat:tools/", "chat:robot/", "chat:scripts/"))})

# module name -> lib (by last path components)
mod_index = {}
for key, (p, lib) in files.items():
    if p.suffix != ".py":
        continue
    parts = key.replace("chat:", "").removesuffix(".py").split("/")
    for i in range(len(parts)):
        mod_index.setdefault(".".join(parts[i:]), lib)
PKG_ROOTS = {"k1_velocity": "rl_isaac", "mjlab_k1": "rl_mj", "k1m": "mimic", "k1_teleop": "teleop",
             "k1_chat": "vla", "k1_locomotion": "deploy_laptop", "k1_control": "deploy_laptop",
             "k1_wbc": "deploy_laptop", "k1_fleet_rviz": "deploy_laptop", "k1_interfaces": "common",
             "push_ik_core": "runtime", "ds4": "runtime", "wbc": "runtime",
             # after the split its importers use only the runtime half (gains, Walker, ArmJog, Gamepad)
             "k1_gamepad_deploy": "runtime", "k1_wiring": "common",
             "k1_constants": "common", "booster_train": "rl_isaac", "k1_arm_ik": "runtime",
             "isaac_ros_env": "utils"}

GENERIC = {"launch", "launch_ros", "cli", "config", "utils", "test", "tests", "main", "app",
           "env_cfg", "rewards", "mdp", "agents", "__init__"}
edges = Counter()
examples = defaultdict(list)
JOINT = re.compile(r"Left_Hip_Pitch")
loc, nfiles, joints, syspath = Counter(), Counter(), Counter(), Counter()
untracked = set(subprocess.run(["git", "-C", str(ROOT), "ls-files", "-o", "--exclude-standard"],
                               capture_output=True, text=True).stdout.split())
untr = Counter()

TG, SRC = {}, {}
for key, (p, lib) in files.items():
    try:
        src = p.read_text(errors="replace")
    except OSError:
        continue
    SRC[key] = src
    targets = []
    if p.suffix == ".py":
        try:
            tree = ast.parse(src)
        except SyntaxError:
            tree = None
        for n in ast.walk(tree) if tree else []:
            names = []
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                # "from pkg import mod": the imported module decides when it is a known root
                subs = {PKG_ROOTS[a.name] for a in n.names if a.name in PKG_ROOTS}
                names = [f"{n.module}.{a.name}" for a in n.names if a.name in PKG_ROOTS][:1] if len(subs) == 1 else [n.module]
            for m in names:
                # most specific known component wins (k1_teleop.k1_arm_ik -> runtime)
                t = next((PKG_ROOTS[c] for c in reversed(m.split(".")) if c in PKG_ROOTS), None)
                if t is None and m.split(".")[0] in ("mjlab",):
                    continue
                if t is None and m not in GENERIC:
                    t = mod_index.get(m)
                if t:
                    targets.append((t, f"import {m}"))
    for pref, t in FOLDER_OWNER.items() if not key.startswith("chat:") else []:
        # root-anchored only: "scripts/..", ' scripts/', booster_ws/scripts, ../scripts
        for m in re.finditer(r"(?:[\"' =:]|booster_ws/|\.\./)(" + re.escape(pref) + r"[\w./-]*)", src):
            hit = files.get(m.group(1).rstrip("./"))  # exact file -> its library, else folder owner
            targets.append((hit[1] if hit else t, f"path {pref}"))
    TG[key] = targets

# Follow pass: a test or a host launcher moves with the library it exercises,
# when >= 60 % of its imports / path refs point at one library.
moved = {}
for key, (p, lib) in list(files.items()):
    if lib == "tests" or (lib == "ops" and key.startswith("scripts/") and p.suffix == ".sh"):
        c = Counter(t for t, _ in TG.get(key, []) if t not in ("tests", "ops"))
        if c:
            t, n = c.most_common(1)[0]
            if n >= 0.6 * sum(c.values()):
                files[key] = (p, t)
                moved[key] = (lib, t)

for key, (p, lib) in files.items():
    if key not in SRC:
        continue
    src = SRC[key]
    nfiles[lib] += 1
    if p.suffix in (".py", ".sh", ".cpp"):
        loc[lib] += src.count("\n")
    if JOINT.search(src):
        joints[lib] += 1
    if "sys.path" in src:
        syspath[lib] += 1
    if key in untracked:
        untr[lib] += 1
    for t, why in TG[key]:
        if t != lib:
            edges[(lib, t)] += 1
            if len(examples[(lib, t)]) < 3 and (key, why) not in examples[(lib, t)]:
                examples[(lib, t)].append((key, why))

print(json.dumps({
    "files": nfiles, "loc": loc, "joint_lists": joints, "sys_path": syspath, "untracked": untr,
    "edges": [{"from": a, "to": b, "n": n, "eg": examples[(a, b)]} for (a, b), n in edges.most_common()],
    "moved": {f"{a}->{b}": sum(1 for v in moved.values() if v == (a, b)) for a, b in set(moved.values())},
    "members": {lib: sorted(k for k, (_, l) in files.items() if l == lib) for lib in nfiles},
}, indent=1))

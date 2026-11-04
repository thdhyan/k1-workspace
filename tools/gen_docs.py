#!/usr/bin/env python3
"""Generate README.md (repo + per directory) for every libs/k1-* repo and write docs/lib_graph.json
(measured import edges). pyproject.toml files are maintained by hand: the sibling libraries a repo may
import are read from its [project].dependencies. Hand-written usage text comes from tools/usage/<repo>.md;
robots, IPs and control procedures live in docs/ROBOTS.md.

python3 tools/gen_docs.py   (needs Python >= 3.11 for tomllib)
"""
import ast
import json
import os
import re
import shutil
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LIBS = HERE / "libs"
sys.path.insert(0, str(HERE / "tools"))
OWNER = "thdhyan"
USAGE = HERE / "tools" / "usage"
ROBOTS = f"https://github.com/{OWNER}/k1-workspace/blob/main/docs/ROBOTS.md"

# lib key -> (repo, main package, layer, may-import (filled from pyproject.toml below), purpose)
R = {
    "common": ("k1-common", "k1_common", "L0", None, "Robot contract: joints, gains, obs/action layout, wiring, motion-clip schema."),
    "description": ("k1-description", "k1_description", "L0", None, "K1 URDF / MJCF / USD description (ROS 2 package); meshes come from the booster_assets submodule."),
    "utils": ("k1-utils", "k1_utils", "L1", None, "Eval gates, checkpoint inspect/migrate, parity checks, Isaac ROS env helper."),
    "runtime": ("k1-runtime", "k1_runtime", "L1", None, "Torch/numpy-only policy runtime: WBC, push-IK core, arm IK, DS4 pad, gamepad core."),
    "rl_isaac": ("k1-rl-isaac", "k1_velocity", "L2", None, "Isaac Lab tasks (velocity, push, kick, COMPASS) and Isaac sim nodes."),
    "rl_mj": ("k1-rl-mj", "mjlab_k1", "L2", None, "mjlab (MuJoCo Warp) tasks, probes and train/play CLI."),
    "mimic": ("k1-mimic", "k1m", "L2", None, "Video/text to K1 motion retargeting (GVHMR, GMR, SOMA, Kimodo) with a Gradio UI."),
    "teleop": ("k1-teleop", "k1_teleop", "L2", None, "XR / PhaseSpace teleop nodes, HMD poser, mapping."),
    "perception": ("k1-perception", "k1_perception", "L2", None, "SLAM chain: cuVSLAM, TCP relay, nvblox stream, grid map."),
    "vla": ("k1-vla", "k1_chat", "L2", None, "k1_chat voice/VLM agent, tools and YOLO node."),
    "data": ("k1-data", "k1_data", "L2", None, "Rosbag, stereo/walk tooling, real-robot converters."),
    "deploy_robot": ("k1-deploy-robot", "k1_deploy_robot", "L3", None, "Runs on the K1 CPU: policy runner, TF service, watchdog, recorders."),
    "deploy_laptop": ("k1-deploy-laptop", "k1_deploy_laptop", "L3", None, "ROS 2 jazzy workspace, push-IK web/sim, pad sender, sim-to-sim."),
    "web_console": ("k1-web-console", "k1_web_console", "L3", None, "Fleet dashboard and camera tools; one web shell, plugin pages over HTTP/WS."),
    "ops": ("k1-ops", "k1_ops", "L3", None, "Host launchers, containers, CI, job chains."),
}
BY_REPO = {v[0]: k for k, v in R.items()}
REPO = {k: v[0] for k, v in R.items()}
LAYER_NAME = {"L0": "Contract (no heavy deps)", "L1": "Core (torch / numpy only)", "L2": "Domain (no cross-imports)", "L3": "Apps (processes you start)"}
LIB_FOR_PKG = {"k1_description": "description", "k1_common": "common", "k1_utils": "utils", "k1_runtime": "runtime", "k1_velocity": "rl_isaac",
               "k1_kicking": "rl_isaac", "compass_k1": "rl_isaac", "mjlab_k1": "rl_mj", "k1m": "mimic",
               "k1_teleop": "teleop", "k1_chat": "vla"}

PIP = {"numpy": "numpy", "scipy": "scipy", "torch": "torch", "mujoco": "mujoco", "yaml": "pyyaml", "gradio": "gradio",
       "requests": "requests", "flask": "flask", "fastapi": "fastapi", "uvicorn": "uvicorn", "websockets": "websockets",
       "aiohttp": "aiohttp", "matplotlib": "matplotlib", "cv2": "opencv-python", "PIL": "pillow", "evdev": "evdev",
       "tqdm": "tqdm", "imageio": "imageio", "trimesh": "trimesh", "onnx": "onnx", "onnxruntime": "onnxruntime",
       "gymnasium": "gymnasium", "openai": "openai", "sounddevice": "sounddevice", "serial": "pyserial",
       "pytest": "pytest", "pandas": "pandas", "paramiko": "paramiko", "httpx": "httpx", "pydantic": "pydantic",
       "tyro": "tyro", "wandb": "wandb", "mink": "mink", "pinocchio": "pin", "jax": "jax", "einops": "einops"}
STDLIB = set(sys.stdlib_module_names)
SKIPDIRS = {".git", "__pycache__", "build", "vendor", "node_modules", ".venv", "third_party"}


def py_files(root):
    for p in root.rglob("*.py"):
        if not (set(p.relative_to(root).parts) & SKIPDIRS):
            yield p


def top_imports(p):
    try:
        tree = ast.parse(p.read_text(errors="replace"))
    except (SyntaxError, ValueError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            out.add(n.module.split(".")[0])
    return out


def first_doc(p):
    try:
        if p.suffix == ".py":
            d = ast.get_docstring(ast.parse(p.read_text(errors="replace")))
            if d:
                return re.sub(r"\s+", " ", d.strip().split("\n\n")[0])[:140]
        elif p.suffix in (".sh", ".bash"):
            for line in p.read_text(errors="replace").split("\n")[:12]:
                if line.startswith("#") and not line.startswith("#!") and len(line.strip("# ")) > 3:
                    return line.strip("# ").strip()[:140]
        elif p.suffix == ".md":
            for line in p.read_text(errors="replace").split("\n")[:5]:
                if line.startswith("#"):
                    return line.strip("# ").strip()[:140]
    except Exception:
        pass
    return ""


local_pkgs = set(LIB_FOR_PKG)
for repo in LIBS.glob("k1-*"):
    for d in (repo / "src").glob("*") if (repo / "src").exists() else []:
        if d.is_dir():
            local_pkgs.add(d.name)
    for d in (repo / "ros").glob("*") if (repo / "ros").exists() else []:
        local_pkgs.add(d.name)

# ---------------------------------------------------------------- pyproject.toml (read only)
pyproj = {}
for lib, (repo, *_r) in R.items():
    f = LIBS / repo / "pyproject.toml"
    pyproj[lib] = tomllib.loads(f.read_text()) if f.exists() else {}
    deps = [re.split(r"[ <>=\[;]", d)[0] for d in pyproj[lib].get("project", {}).get("dependencies", [])]
    R[lib] = R[lib][:3] + ([BY_REPO[d] for d in deps if d in BY_REPO],) + R[lib][4:]

report = {}
edges = Counter()
nfiles, nloc = {}, {}
for lib, (repo, pkg, layer, may, purpose) in R.items():
    root = LIBS / repo
    files = [p for p in root.rglob("*") if p.is_file() and p.name not in ("README.md", "pyproject.toml", ".gitignore") and not (set(p.relative_to(root).parts) & SKIPDIRS)]
    nfiles[lib] = len(files)
    nloc[lib] = sum(p.read_text(errors="replace").count("\n") for p in files if p.suffix in (".py", ".sh", ".cpp"))
    imps = Counter()
    for p in py_files(root):
        for m in top_imports(p):
            imps[m] += 1
            if m in LIB_FOR_PKG and LIB_FOR_PKG[m] != lib:
                edges[(lib, LIB_FOR_PKG[m])] += 1
    third = {m for m in imps if m not in STDLIB and m not in local_pkgs and not m.startswith("_")}
    pip = sorted({PIP[m] for m in third if m in PIP})
    env = sorted(m for m in third if m not in PIP)
    pkgs = sorted(d.name for d in (root / "src").glob("*") if d.is_dir() and (d / "__init__.py").exists()) if (root / "src").exists() else []
    # packages w/o __init__ but with .py (namespace-style)
    if (root / "src").exists():
        pkgs = sorted({d.name for d in (root / "src").glob("*") if d.is_dir() and any(d.glob("*.py"))})
    envvars = set()
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".sh", ".launch") and not (set(f.relative_to(root).parts) & SKIPDIRS):
            envvars |= set(re.findall(r"\b(K1_[A-Z0-9_]+)\b", f.read_text(errors="replace")))
    report[lib] = dict(pip=pip, env=env, pkgs=pkgs, envvars=sorted(envvars))


# ---------------------------------------------------------------- per-directory READMEs
def tree(root, depth=2):
    out = []
    def walk(d, pre, lvl):
        items = sorted(x for x in d.iterdir() if x.name not in SKIPDIRS and not x.name.startswith("."))
        for x in items:
            if x.is_dir():
                n = sum(1 for _ in x.rglob("*") if _.is_file())
                out.append(f"{pre}{x.name}/  ({n} files)")
                if lvl + 1 < depth:
                    walk(x, pre + "  ", lvl + 1)
            else:
                out.append(f"{pre}{x.name}")
    walk(root, "", 0)
    return "\n".join(out)


def table(d):
    rows = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix in (".py", ".sh", ".md", ".html", ".cpp") and p.name != "README.md":
            rows.append(f"| `{p.name}` | {first_doc(p).replace('|', '/')} |")
    return rows


dir_readmes = 0
for lib, (repo, *_r) in R.items():
    root = LIBS / repo
    for d in sorted([root] + [x for x in root.rglob("*") if x.is_dir()]):
        if set(d.relative_to(root).parts) & SKIPDIRS or d == root:
            continue
        if len(d.relative_to(root).parts) > 3:
            continue
        rows = table(d)
        rel = d.relative_to(root)
        old = (d / "README.md").read_text() if (d / "README.md").exists() else None
        generated = old is None or old.startswith(f"# {rel}\n\nPart of [{repo}]")
        if len(rows) >= 3 and generated:
            (d / "README.md").write_text(f"# {rel}\n\nPart of [{repo}](https://github.com/{OWNER}/{repo}).\n\n| File | What it does |\n|---|---|\n" + "\n".join(rows) + "\n")
            dir_readmes += 1

# ---------------------------------------------------------------- path refs into other repos (known seams)
OWN_PREFIX = {"isaac_tasks/": "rl_isaac", "mjlab_k1/deploy/": "deploy_laptop", "mjlab_k1/": "rl_mj", "k1_teleop/": "teleop",
              "real_robot/": "data", "k1m/": "mimic", "tools/": "web_console", "compass_k1": "rl_isaac"}
LEGACY = re.compile(r"booster_ws|isaac_tasks/|booster_train_ref")
seams = defaultdict(list)
legacy = defaultdict(list)
for lib, (repo, *_r) in R.items():
    root = LIBS / repo
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in (".py", ".sh", ".yaml", ".yml", ".md") or set(p.relative_to(root).parts) & SKIPDIRS:
            continue
        txt = p.read_text(errors="replace")
        if p.name != "README.md" and "legacy" not in p.relative_to(root).parts and LEGACY.search(txt):
            legacy[lib].append(str(p.relative_to(root)))
        for pref, owner in OWN_PREFIX.items():
            if owner == lib:
                continue
            if re.search(r"[\"' =:/]" + re.escape(pref) + r"[\w./-]+", txt):
                seams[lib].append((str(p.relative_to(root)), pref, owner))

# ---------------------------------------------------------------- repo READMEs
mm = [l.rstrip("\n").split("\t") for l in open(HERE / "docs/migration_map.tsv")][1:]
orig = defaultdict(list)
for src, repo, new in mm:
    orig[repo].append((src, new))

for lib, (repo, pkg, layer, may, purpose) in R.items():
    root = LIBS / repo
    rep = report[lib]
    imports_down = ", ".join(f"[{R[m][0]}](https://github.com/{OWNER}/{R[m][0]})" for m in may) or "nothing"
    install = (f"```bash\nuv add git+https://github.com/{OWNER}/{repo}\n# or, from a checkout\nuv sync\n```" if rep["pkgs"]
               else f"Not an installable library: clone it and run the scripts in place.\n```bash\ngit clone https://github.com/{OWNER}/{repo}\n```")
    sm = sorted(set(seams[lib]))
    seam_txt = ("None.\n" if not sm else "These files still name paths that now live in another repo (hard-coded path strings, not imports). "
                "Pass them as arguments / config when you touch the file:\n\n| File | Refers to | Owner |\n|---|---|---|\n" +
                "\n".join(f"| `{f}` | `{pref}` | {R[o][0]} |" for f, pref, o in sm[:40]) + ("\n\n…and %d more." % (len(sm) - 40) if len(sm) > 40 else "") + "\n")
    usage_f = USAGE / f"{repo}.md"
    usage = usage_f.read_text().strip() + "\n" if usage_f.exists() else "Not written yet: add `tools/usage/%s.md` in k1-workspace.\n" % repo
    tests = ""
    if (root / "tests").is_dir():
        ini = pyproj[lib].get("tool", {}).get("pytest", {}).get("ini_options", {})
        marks = "".join(f"\n- marker `{m.split(':')[0]}`: {m.split(':', 1)[1].strip()}" for m in ini.get("markers", []))
        tests = (f"From a k1-workspace checkout (see its README, \"Run the tests\"):\n```bash\ncd libs/{repo} && python -m pytest -q tests\n```\n"
                 + (f"\nDefault options: `{ini['addopts']}`.\n" if ini.get("addopts") else "") + marks.lstrip("\n") + ("\n" if marks else ""))
    else:
        tests = "No tests yet.\n"
    envs = ", ".join(f"`{e}`" for e in rep["envvars"]) or "none"
    lg = sorted(set(legacy[lib]))
    legacy_txt = ("" if not lg else "\n## Old `booster_ws` layout still referenced\n\nThese files still name `booster_ws`, `isaac_tasks/` or `booster_train_ref` paths "
                  "(container scripts not ported yet, or docstrings):\n\n" + "\n".join(f"- `{f}`" for f in lg[:30])
                  + ("\n- …and %d more" % (len(lg) - 30) if len(lg) > 30 else "") + "\n")
    used_by = [R[o][0] for o in R if lib in R[o][3]]
    mer = ["```mermaid", "flowchart TB"]
    mer += [f"  {R[o][0].replace('-', '_')}[{R[o][0]}]" for o in R if o in may or o in R and lib in R[o][3]]
    mer += [f"  {repo.replace('-', '_')}(({repo}))", f"  style {repo.replace('-', '_')} fill:#e8833a,color:#000"]
    mer += [f"  {R[o][0].replace('-', '_')} --> {repo.replace('-', '_')}" for o in R if lib in R[o][3]]
    mer += [f"  {repo.replace('-', '_')} --> {R[m][0].replace('-', '_')}" for m in may]
    mer.append("```")
    sits = ("\n".join(mer) + f"\n\nUsed by: {', '.join(used_by) or 'nothing (top layer)'}.\n\n"
            f"![k1-workspace layers](https://raw.githubusercontent.com/{OWNER}/k1-workspace/main/docs/img/architecture.png)\n")
    body = f"""# {repo}

{purpose}

| | |
|---|---|
| Layer | **{layer}**: {LAYER_NAME[layer]} |
| May import | {imports_down} |
| Files / LOC | {nfiles[lib]} files · {nloc[lib]:,} lines (py, sh, cpp) |
| Part of | [k1-workspace](https://github.com/{OWNER}/k1-workspace) (architecture and layering rules live there) |

## Where it sits

{sits}
## Install

{install}

## Usage

{usage}
## Tests

{tests}
## Robots and hosts

Robot IPs, SSH aliases, network, safety and how to control each robot: [docs/ROBOTS.md]({ROBOTS}) in k1-workspace.

## Environment variables read

{envs}

## Layout

```
{tree(root)}
```

## Dependencies

- Declared sibling libraries: {", ".join(R[m][0] for m in may) or "none"} (see `pyproject.toml`, `[tool.uv.sources]`).
- PyPI: {", ".join(rep["pip"]) or "none detected"}.
- Provided by the environment (ROS 2, Isaac, mjlab, robot SDK) or unresolved: {", ".join(f"`{e}`" for e in rep["env"]) or "none"}.

## Hard-coded paths into other repos

{seam_txt}{legacy_txt}
## Origin

Extracted from `booster_ws` (branch `dev/push-training-wip`, working tree of 2026-11-03{"; k1_chat from `wt-k1-tools`" if lib == "vla" else ""}) by
`tools/build_workspace.py` in k1-workspace. Old path to new path for every file: [`docs/migration_map.tsv`](https://github.com/{OWNER}/k1-workspace/blob/main/docs/migration_map.tsv) (filter on `{repo}`).
History was not carried over: the working tree was copied as is, including previously untracked files.
"""
    (root / "README.md").write_text(body)

# ---------------------------------------------------------------- umbrella
um = LIBS / "_umbrella"
if um.exists():
    for p in um.rglob("*"):
        if p.is_file():
            t = HERE / p.relative_to(um)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, t)
    shutil.rmtree(um)

json.dump({"edges": [{"from": a, "to": b, "n": n} for (a, b), n in edges.most_common()],
           "files": nfiles, "loc": nloc,
           "libs": {k: {"repo": v[0], "layer": v[2], "may": v[3], "purpose": v[4]} for k, v in R.items()},
           "seams": {k: len(set(v)) for k, v in seams.items()}, "deps": report},
          open(HERE / "docs/lib_graph.json", "w"), indent=1)
# layering violations (measured on python imports)
rank = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
bad = [(a, b, n) for (a, b), n in edges.items() if b not in R[a][3]]
print(f"dir READMEs: {dir_readmes}; cross-library import edges: {sum(edges.values())}; not allowed by 'may import': {bad}")

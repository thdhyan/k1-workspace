"""Checkout-level regression checks for the 15-library extraction.

Run: python3 -m pytest tests/test_refactor_contracts.py -q
No robot, network service, GPU, checkpoint, or old checkout is used. Syntax and
layout checks need only pytest; behavioral checks need existing numpy/torch.
Failures deliberately remain visible until the corresponding source is fixed.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPOS = sorted((ROOT / "libs").glob("k1-*"))
SOURCES = [str(p) for p in sorted((ROOT / "libs").glob("k1-*/src"))]


def python(code, *paths):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(SOURCES + list(paths)),
               PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1")
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("repo", REPOS, ids=lambda p: p.name)
def test_python_sources_compile(repo):
    errors = []
    for path in sorted(repo.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            compile(path.read_bytes(), str(path), "exec")
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("repo", REPOS, ids=lambda p: p.name)
def test_shell_sources_parse(repo):
    scripts = sorted(repo.rglob("*.sh"))
    if not scripts:
        pytest.skip("no shell scripts")
    errors = []
    for path in scripts:
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(result.stderr)
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("repo", REPOS, ids=lambda p: p.name)
def test_explicit_relative_modules_exist(repo):
    """Catch moved modules left behind in relative imports (e.g. k1m.schema)."""
    errors = []
    for path in sorted(repo.rglob("*.py")):
        if {"tests", "test", "__pycache__"} & set(path.parts):
            continue
        try:
            tree = ast.parse(path.read_bytes())
        except SyntaxError:
            continue  # reported independently by the compilation test
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level or not node.module:
                continue  # `from . import name` may refer to an exported symbol
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
            target = base.joinpath(*node.module.split("."))
            if not target.is_dir() and not target.with_suffix(".py").is_file():
                errors.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.module}")
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("repo", REPOS, ids=lambda p: p.name)
def test_sibling_imports_are_declared(repo):
    owners = {}
    for sibling in REPOS:
        for package in (sibling / "src").glob("*"):
            if package.is_dir():
                owners[package.name] = sibling.name
    meta = tomllib.loads((repo / "pyproject.toml").read_text())
    dependencies = set(meta["project"]["dependencies"]) | {repo.name}
    errors = []
    for path in sorted(repo.rglob("*.py")):
        try:
            tree = ast.parse(path.read_bytes())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            imports = []
            if isinstance(node, ast.Import):
                imports = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                imports = [node.module]
            for name in imports:
                owner = owners.get(name.split(".")[0])
                if owner and owner not in dependencies:
                    errors.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name} needs {owner}")
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("module", [
    "k1_description", "k1_common.paths", "k1_common.k1_wiring", "k1_common.clip_schema",
    "k1_utils.height_gate", "k1_utils.mujoco_eval",
    "k1_runtime.wbc", "k1_runtime.gamepad_core", "k1_runtime.push_ik_core",
    "k1_runtime.ds4", "k1_runtime.k1_arm_ik", "k1_teleop.teleop_mapping",
    "k1_teleop.push_ik_phasespace", "k1m",
])
def test_cpu_library_import(module):
    python(f"import importlib; importlib.import_module({module!r})")


def test_runtime_arm_ik_default_resource():
    python("from k1_runtime.k1_arm_ik import ArmIK; ArmIK()")


def test_runtime_arm_ik_with_explicit_existing_urdf():
    urdf = ROOT / "libs/k1-description/assets/robots/K1/K1_22dof-ZED.urdf"
    python(f"""
import numpy as np
from pathlib import Path
from k1_runtime.k1_arm_ik import ArmIK
ik = ArmIK(Path({str(urdf)!r}))
state = {{'Left_Shoulder_Roll': -1.3, 'Right_Shoulder_Roll': 1.3}}
for side in ('left', 'right'):
    goal = ik.fk(side, state)
    goal[:3, 3] += (0.01, 0, 0)
    q, error = ik.solve(side, goal, state)
    assert error < 0.005
    lo, hi = ik._lim[side].T
    assert np.all(q >= lo) and np.all(q <= hi)
""")


def test_motion_csv_round_trip_and_joint_order(tmp_path):
    python(f"""
import numpy as np
from k1_common import clip_schema as s, k1_wiring as w
from k1_runtime import wbc
assert s.K1_JOINT_NAMES == w.JOINTS == list(wbc.JOINTS)
m = np.zeros((3, 29)); m[:, 6] = 1; m[:, 7:] = wbc.HOME
p = {str(tmp_path / 'motion.csv')!r}
s.write_csv(p, m, fps=30)
actual, fps = s.read_csv(p)
np.testing.assert_allclose(actual, m)
assert fps == 30
m[0, 0] = np.nan
assert not s.validate(m)['ok']
""")


def test_runtime_wbc_checkpoint_and_reset(tmp_path):
    python(f"""
import torch
from k1_runtime import wbc as w
p = {str(tmp_path / 'zero.pt')!r}
torch.save({{'actor_state_dict': {{'mlp.0.weight': torch.zeros(12, 225),
    'mlp.0.bias': torch.zeros(12), 'obs_normalizer._mean': torch.zeros(225),
    'obs_normalizer._std': torch.ones(225)}}}}, p)
body = w.DecoupledWBC(p, num_envs=2)
state = w.Proprio(torch.zeros(2, 3), torch.tensor([[0., 0., -1.]]).repeat(2, 1),
    torch.tensor(w.HOME).repeat(2, 1), torch.zeros(2, 22))
cmd = w.LocoCmd(torch.tensor([0.3, 0.4]), torch.zeros(2), torch.zeros(2))
obs = body.loco.obs(state, cmd)
assert obs.shape == (2, 225)
torch.testing.assert_close(obs[:, -15:], cmd.tensor().repeat(1, 5))
torch.testing.assert_close(body.step(state, cmd), torch.tensor(w.HOME).repeat(2, 1))
body.reset(); assert body.loco.fresh.all(); assert not body.loco.last.any()
q = torch.randn(4, 22)
torch.testing.assert_close(w.mirror_joints(w.mirror_joints(q)), q)
""")


def test_gamepad_split_preserves_math_and_shared_configuration():
    python("""
import numpy as np
import torch
from k1_runtime import gamepad_core as g, wbc
import k1_gamepad_deploy as robot
assert robot.Gamepad is g.Gamepad and robot.Body is g.Body
original = g.CAP
try:
    g.CAP = (0.2, 0.1, 0.3)
    # The split runner exports the classes, while command math belongs to core.
    np.testing.assert_allclose(g.stick_to_cmd(0, -1, 0), [0.2, 0, 0])
finally:
    g.CAP = original
for side in (1., -1.):
    q = np.array([-0.3, -1.25 * side, 0., -1.4 * side])
    p, jac, _ = g.hand_fk(q, side)
    pt, jt, _ = wbc.hand_fk(torch.tensor(q)[None], side)
    np.testing.assert_allclose(p, pt[0].numpy(), atol=1e-8)
    np.testing.assert_allclose(jac, jt[0].numpy(), atol=1e-8)
""", str(ROOT / "libs/k1-deploy-robot/deploy"))


def test_push_web_imports_with_declared_packages():
    # Its own deploy directory is available when invoked as a script. Sibling
    # packages must resolve by their installed names, without extra path hacks.
    python("import push_ik_web", str(ROOT / "libs/k1-deploy-laptop/deploy"))


def test_mimic_local_stage_scripts_resolve():
    # local_stages runs the gate and renderer as `python -m <module>`; every
    # such target must be an importable module of the installed package.
    import re
    src = (ROOT / "libs/k1-mimic/src/k1m/local_stages.py").read_text()
    targets = re.findall(r'"-m",\s*"([\w.]+)"', src)
    assert {"k1m.gate", "k1m.render"} <= set(targets), targets
    python("import importlib.util as u; "
           f"missing = [m for m in {targets!r} if u.find_spec(m) is None]; "
           "assert not missing, missing")


def test_description_assets_registered_for_recursive_clone():
    # README advertises a separate asset repo. Recursive clone alone currently
    # cannot provide it unless its gitlink and .gitmodules entry exist.
    repo = ROOT / "libs/k1-description"
    assert (repo / "assets/robots/K1/K1_22dof.xml").is_file(), "K1 MJCF/assets absent"
    assert "assets" in (repo / ".gitmodules").read_text()


def test_description_cmake_install_sources_exist():
    repo = ROOT / "libs/k1-description"
    # Every install(DIRECTORY ...) source listed in CMakeLists.txt.
    import re
    cmake = (repo / "CMakeLists.txt").read_text()
    names = [n for m in re.findall(r"install\(DIRECTORY ([^)]*?) DESTINATION", cmake)
             for n in m.split()]
    assert names, "no install(DIRECTORY) found"
    missing = [n for n in names if not (repo / n).is_dir()]
    assert not missing, f"CMake install(DIRECTORY ...) sources absent: {missing}"


def test_description_default_view_robot_has_robot_joints():
    import re
    launch = (ROOT / "libs/k1-description/launch/view_robot.launch.py").read_text()
    parts = re.search(r"URDF = os\.path\.join\(([^)]*)\)", launch).group(1)
    urdf = ROOT / "libs/k1-description" / Path(*re.findall(r"'([^']+)'", parts))
    tree = ET.parse(urdf)
    assert len([j for j in tree.findall("joint") if j.get("type") != "fixed"]) == 22, (
        f"view_robot URDF {urdf} lacks the 22 actuated joints")


def test_ops_default_training_target_exists():
    path = ROOT / "libs/k1-ops/docker/entrypoint.sh"
    import re
    target = re.search(r'TRAIN_SCRIPT="\$\{K1_TRAIN_SCRIPT:-([^}]+)\}"', path.read_text()).group(1)
    assert (ROOT / target).is_file(), f"container default points outside new layout: {target}"
    # every path the workspace layout installs from must exist in the umbrella
    text = path.read_text()
    block = text[text.index("  workspace)"):text.index("  legacy)")]
    paths = [p for arr in re.findall(r"(?:TRAIN_LIBS|EXT_PKGS)=\(([^)]*)\)", block) for p in arr.split()]
    assert len(paths) >= 6, paths
    missing = [p for p in paths if not ((ROOT / p / "pyproject.toml").is_file() or (ROOT / p / "setup.py").is_file())]
    assert not missing, f"workspace layout installs non-packages: {missing}"


def test_workspace_installer_includes_every_buildable_library():
    installer = (ROOT / "scripts/dev-install.sh").read_text()
    missing = [p.name for p in REPOS
               if "build-system" in tomllib.loads((p / "pyproject.toml").read_text())
               and p.name not in installer]
    assert not missing, f"buildable libraries absent from editable install script: {missing}"


def test_isaac_kicking_package_is_distributed():
    repo = ROOT / "libs/k1-rl-isaac"
    meta = tomllib.loads((repo / "pyproject.toml").read_text())
    packages = meta["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "src/k1_kicking" in packages, "k1_kicking source exists but is omitted from wheel"


def test_isaac_gait_gate_can_load():
    path = ROOT / "libs/k1-rl-isaac/scripts/gait_gate.py"
    python(f"import runpy; runpy.run_path({str(path)!r})")


def test_data_freshness_detects_frozen_and_advancing_stamps(tmp_path):
    path = ROOT / "libs/k1-data/real_robot/check_bag_freshness.py"
    python(f"""
import runpy, sqlite3, struct
analyse = runpy.run_path({str(path)!r})['analyse']
db = {str(tmp_path / 'bag.db3')!r}
with sqlite3.connect(db) as con:
    con.executescript('CREATE TABLE topics(id INTEGER, name TEXT); '
                     'CREATE TABLE messages(topic_id INTEGER, data BLOB);')
    con.executemany('INSERT INTO topics VALUES(?, ?)', [(1, '/frozen'), (2, '/live')])
    for i in range(3):
        for topic, stamp in [(1, 10), (2, 10 + i)]:
            blob = b'\\x00\\x01\\x00\\x00' + struct.pack('<iI', stamp, 0) + b'0000'
            con.execute('INSERT INTO messages VALUES(?, ?)', (topic, blob))
result = analyse(db, ['/frozen', '/live'])
assert result['/frozen'] == (3, 1, 1)
assert result['/live'] == (3, 3, 3)
""")


def test_web_console_heartbeat_parser():
    pytest.importorskip("websockets")
    path = ROOT / "libs/k1-web-console/tools/fleet_dashboard/dashboard.py"
    python(f"""
import runpy
d = runpy.run_path({str(path)!r})
def field(n, value):
    return bytes([(n << 3) | 2, len(value)]) + value
data = field(1, b'SERIAL') + field(6, b'127.0.0.1') + field(12, b'Booster_A2')
info = d['robot_info'](d['pb'](data))
assert info['sn'] == 'SERIAL' and info['ip'] == '127.0.0.1'
assert d['short'](info['name']) == 'A2'
""")


@pytest.mark.parametrize("repo,code", [
    ("k1-vla", "from k1_chat import fleet; fleet.load()"),
    ("k1-deploy-laptop", "import importlib.util; assert importlib.util.find_spec('k1_wbc.wbc_node') is not None"),
])
def test_noneditable_wheel_runtime_contract(repo, code, tmp_path):
    pytest.importorskip("hatchling")
    from hatchling.builders.wheel import WheelBuilder
    builder = WheelBuilder(str(ROOT / "libs" / repo))
    wheel = Path(next(builder.build(directory=str(tmp_path), versions=["standard"])))
    target = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(target)
    # No checkout source paths: this must exercise the distribution itself.
    env = dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr

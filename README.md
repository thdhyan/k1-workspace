# k1-workspace

Umbrella for the Booster K1 code base, split from the monolithic `booster_ws` into 15 layered libraries (git submodules under `libs/`).

| Repo | Layer | Purpose | Files | LOC |
|---|---|---|---|---|
| [k1-common](https://github.com/thdhyan/k1-common) | L0 | Robot contract: joints, gains, obs/action layout, wiring, motion-clip schema. | 12 | 719 |
| [k1-description](https://github.com/thdhyan/k1-description) | L0 | K1 URDF / MJCF / USD description (ROS 2 package); meshes come from the booster_assets submodule. | 9 | 141 |
| [k1-utils](https://github.com/thdhyan/k1-utils) | L1 | Eval gates, checkpoint inspect/migrate, parity checks, Isaac ROS env helper. | 8 | 1,030 |
| [k1-runtime](https://github.com/thdhyan/k1-runtime) | L1 | Torch/numpy-only policy runtime: WBC, push-IK core, arm IK, DS4 pad, gamepad core. | 7 | 1,352 |
| [k1-rl-isaac](https://github.com/thdhyan/k1-rl-isaac) | L2 | Isaac Lab tasks (velocity, push, kick, COMPASS) and Isaac sim nodes. | 213 | 30,838 |
| [k1-rl-mj](https://github.com/thdhyan/k1-rl-mj) | L2 | mjlab (MuJoCo Warp) tasks, probes and train/play CLI. | 75 | 7,576 |
| [k1-mimic](https://github.com/thdhyan/k1-mimic) | L2 | Video/text to K1 motion retargeting (GVHMR, GMR, SOMA, Kimodo) with a Gradio UI. | 19 | 3,722 |
| [k1-teleop](https://github.com/thdhyan/k1-teleop) | L2 | XR / PhaseSpace teleop nodes, HMD poser, mapping. | 10 | 2,292 |
| [k1-perception](https://github.com/thdhyan/k1-perception) | L2 | SLAM chain: cuVSLAM, TCP relay, nvblox stream, grid map. | 23 | 1,272 |
| [k1-vla](https://github.com/thdhyan/k1-vla) | L2 | k1_chat voice/VLM agent, tools and YOLO node. | 71 | 5,976 |
| [k1-data](https://github.com/thdhyan/k1-data) | L2 | Rosbag, stereo/walk tooling, real-robot converters. | 10 | 877 |
| [k1-deploy-robot](https://github.com/thdhyan/k1-deploy-robot) | L3 | Runs on the K1 CPU: policy runner, TF service, watchdog, recorders. | 14 | 1,415 |
| [k1-deploy-laptop](https://github.com/thdhyan/k1-deploy-laptop) | L3 | ROS 2 jazzy workspace, push-IK web/sim, pad sender, sim-to-sim. | 56 | 5,520 |
| [k1-web-console](https://github.com/thdhyan/k1-web-console) | L3 | Fleet dashboard and camera tools; one web shell, plugin pages over HTTP/WS. | 8 | 554 |
| [k1-ops](https://github.com/thdhyan/k1-ops) | L3 | Host launchers, containers, CI, job chains. | 68 | 2,479 |

## Visualisations

- [`docs/architecture.html`](docs/architecture.html): layered repo graph from measured imports.
- `graphify-out/graph.html` + `GRAPH_REPORT.md`: code-level knowledge graph (6k nodes, 400 communities).

## Docs

[Architecture](docs/ARCHITECTURE.md) · [Migration](docs/MIGRATION.md) · [Known issues](docs/KNOWN_ISSUES.md) · [Old docs](docs/legacy/)

## Use

```bash
git clone --recurse-submodules git@github.com:thdhyan/k1-workspace.git
scripts/dev-install.sh   # editable installs in dependency order
```

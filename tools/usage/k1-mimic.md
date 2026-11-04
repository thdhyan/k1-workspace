Video or text to K1 joint angles. The heavy stages (GVHMR, Kimodo, GMR) run on a DGX Spark over SSH. The gate and
the MuJoCo replay run locally.

No console script is installed; use `python -m k1m.cli`.
```bash
python -m k1m.cli doctor                        # which remote stages can be used
python -m k1m.cli video dance.mp4               # video -> CSV + replay
python -m k1m.cli text "a person dances"        # text  -> CSV + replay
python -m k1m.cli csv motion.csv                # existing retarget, no GPU
python -m k1m.gate  out/foo_k1.csv
python -m k1m.render out/foo_k1.csv
python -m k1m.app                 # Gradio UI (scripts/restart_k1m_app.sh restarts it)
```
Clip format: `k1_common.clip_schema`.

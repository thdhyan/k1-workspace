# K1 voice agent with tool calling (OpenRouter) — runbook

Sets up the voice chat agent (ASR → OpenRouter LLM with robot tools → Kokoro TTS) on any Booster K1
(fw 1.8.x). `<r>` = a1 | a2 | a3 | b1 | b2 | b3, ssh alias `boosterk1.<r>`.

## 0. Laptop prerequisites

- Robots reach the internet through the laptop NAT (`k1nat`, see `docs/network_robotics_5G_2026-10-26.md`).
  `k1voice.sh start` re-creates it if missing. Robot DNS must be 8.8.8.8 / 1.1.1.1.
- Run everything from ONE code tree containing tools + vision code. `k1voice.sh` rsyncs `src/` from the
  directory it is run in. Until `wt-k1-vision` is merged into `wt-k1-tools`, use the merged staging tree
  (`wt-k1-tools` + `vision.py` / `test_vision.py` from `wt-k1-vision`).

## 1. `.env` in the code tree root (never commit)

```
OPENROUTER_API_KEY=sk-or-...
K1_CHAT_MODEL=nvidia/nemotron-3.5-super-vl:free
K1_VISION_MODEL=nvidia/nemotron-3.5-super-vl:free   # optional: enables look + move_and_watch
```

Free (`:free`) models only. The key reaches the robot over ssh stdin into a 0600 temp file that the
launcher sources and deletes at once; it is never on the command line.

Self-hosted LLM instead of OpenRouter: `K1_CHAT_BASE_URL=http://192.168.50.250:8000/v1` (and
`K1_VISION_BASE_URL`), see `scripts/serve_llm.sh`.

## 2. One-time install per robot

```bash
bash scripts/k1voice_install.sh <r>     # ~/k1_chat venv, faster-whisper tiny.en, Kokoro TTS (GPU onnxruntime)
```

Optional, much better speech recognition: Nemotron ASR 0.6B daemon (`nemo-asrd.service`, 127.0.0.1:8090).
The opencode installer (`/Storage/tmp/opencode/k1-asr-install.sh <r>`) needs two fixes, already applied on
A1/A2 by hand:

- write the systemd unit with `ssh $host sudo -n bash`, and `ExecStartPre=/usr/bin/sudo -n ...` for drop_caches;
- pin `coverage==7.16.2` in `/home/booster/nemo-asr` (system coverage 6.2 crashes numba:
  `AttributeError: module 'coverage' has no attribute 'types'`).

Without a healthy Nemo daemon the agent falls back to Whisper automatically.

## 3. Start / check / stop

```bash
K1_BACKEND=ros bash scripts/k1voice.sh start <r> agent   # K1_CHAT_ASR=whisper to skip Nemo
bash scripts/k1voice.sh log <r>                          # tail ~/k1_chat/voice.log
bash scripts/k1voice.sh stop <r>                         # always restores the robot audio service
```

- Web console: `http://<robot-ip>:8091` — chat motion ON/OFF (e-stop latch), stand up / prepare,
  walking mode, live camera, event log.
- `K1_BACKEND=sim` = dry run, no motion.
- Switching ASR = stop, then start with the other `K1_CHAT_ASR` (nemo | whisper).

## 4. Smoke test (voice)

1. "What's your battery?" → `robot_status` (mode, chat motion, gesture, battery %).
2. Walking mode via remote or "switch to walking mode" (`set_mode`). Gestures and walking need WALKING.
3. "Turn left 90 degrees" → `turn` (or `move_and_watch` when vision is on: frames at ~1 fps while moving).
4. "Wave" → `wave`. "What do you see?" → `look`.

## Safety (enforced in code)

- Motion only via tools through the VelocityArbiter (0.4 m/s cap); console STOP latches the e-stop.
- Mode changes only through ModeFSM, one edge at a time; chat never commands DAMPING.
- Never run `booster-cli upgrade` or `upload_log`.

## Memory on 8 GB robots (Orin NX)

- Nemo ASR (~2.5 GB GPU + ~1.7 GB CPU at fp16) + Kokoro (GPU capped 512 MB) + robot system is tight.
- Stop the desktop first: `sudo systemctl stop gdm` (restore: `sudo systemctl start gdm`).
- Nemo must finish loading (~60 s) before the agent starts; `robot/run.sh` waits for `/health` itself.
  Loading both at once got nemo-asrd OOM-killed on A2.
- No local tool-calling LLM fits next to these: use OpenRouter, or host the LLM on the laptop.

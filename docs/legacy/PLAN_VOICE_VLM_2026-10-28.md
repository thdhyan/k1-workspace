# Plan: voice (ASR + per-robot wake word) and Cosmos3-Edge on K1 fleet

Date: 2026-10-28. Status: PLAN, nothing built. Evening session when connected to robots.

## 0. Facts (checked)

Robot (docs/k1_hardware_camera_findings.md): Orin NX, aarch64, 7.4 GiB RAM (~4.5 GiB free), JetPack 6 / CUDA 12.6, ROS 2 Humble. USB C-Media mic (`0d8c:0012`) + UAC speaker (`1d6b:a4a7`). cuVSLAM + k1-tf already resident.

Nemotron-Labs-Unified-ASR-0.6b (HF card):
- 600M FastConformer + RNNT, 25 EU languages, one ckpt offline + streaming, latency 160 ms to 2080 ms.
- Runtime = NeMo 3.1.0 only. No ONNX/TRT/Riva mentioned. aarch64/Jetson NOT mentioned. No wake word, no real VAD.
- Streaming is buffered (not cache-aware) = more compute at same latency.
- WER EN: 4.68 offline, 7.87 at 160 ms.
- License OpenMDW 1.1 (commercial OK).

Cosmos3-Edge-INT4-AWQ (HF card, third-party quant by ubr-physical-ai):
- ~2.44B reasoner, image+text in, text out. No video. No tool calling mentioned.
- NOT loadable in transformers/vLLM. Only TensorRT-Edge-LLM v0.10.1: export to ONNX, build engine ON device (~2m21s on Orin Nano).
- Orin Nano 8GB: decode 52.8 tok/s, prefill 222 ms/512 tok, vision enc 260 ms @896x448. Peak mem 3.4 GB (AWQ/TRT), system-wide ~4.8 GB (unreconciled).
- Structured JSON only reliable with `enableThinking` on (24/24 vs 11/24 off). Unvalidated on live robot.

## 1. Recommendations

1. **ASR: do not run on robot.** Orin NX has no free RAM/GPU headroom for NeMo and it is unvalidated on Jetson. Run ASR on a GPU box (laptop first, later dl/lambda) and stream audio from robots. Robot only does wake word + VAD + audio streaming.
   - Is it better than what we have? Unknown, no current ASR in repo (grep found none). Compare against `faster-whisper` small/large-v3-turbo and `parakeet-tdt-0.6b-v3` on 20 robot-recorded clips (real mic, motor noise, walking). Pick on WER + latency. Nemotron wins only if its streaming at 160-480 ms beats the rest. Not worth it for English-only if Whisper-turbo is close.
2. **Wake word per robot: on-robot openWakeWord** (Apache-2.0, ONNX/tflite, CPU, ~tens of MB, runs fine on Orin CPU). Porcupine is easier but per-keyword licence/AccessKey, 6 custom words = friction. Each robot gets a distinct word.
3. **Cosmos3-Edge: tight on RAM. Do a feasibility test first (Phase C0)**. 4.5 GiB free vs 3.4-4.8 GB peak means it can only run if cuVSLAM/other stacks shrink or it is loaded on demand. Fallback = run the same model (or full Cosmos3-Edge / another VLM) on the laptop/GPU box, robot sends JPEG + request. Tool calling is NOT a native feature of this checkpoint: do it by prompting for JSON + validating (see Phase C3).

## 2. Phase A: ASR service (off-robot)

A1. Spike on laptop (use `uv`, never base python3): `uv run --with "nemo_toolkit[asr]"` load model, transcribe 5 test wavs, measure RTF + VRAM. Also run faster-whisper + parakeet on same wavs.
A2. Record 20-30 clips from a K1 (mic at robot, standing + walking + arm motion): `arecord -D <c-media dev> -f S16_LE -r 16000 -c 1`. Save under `real_robot/voice/clips/`.
A3. Pick winner. Wrap as one service: WebSocket (or ROS 2 topic) in, text + `is_final` out. Single process on one GPU box, serves all 6 robots. GPU budget rule: laptop OK for dev; production on dl GPU0/1 or zz-bw GPU0 (see memory gpu-budget-shared-boxes).
A4. Streaming config: 160-480 ms chunk, EOU timeout ~800 ms. Send audio only between wake and end-of-speech (saves WiFi and ASR load, also privacy).

## 3. Phase B: wake word, no cross talk (6 robots)

Design:
- Each robot has a unique name/wake phrase, e.g. "hey Alpha / hey Bravo ..." (A1-A3, B1-B3). Pick words that are phonetically distinct (avoid A/B pairs sounding alike; use e.g. names with different vowels and 3+ syllables). Train per-phrase openWakeWord models (synthetic TTS data, ~1 hr each, done on laptop).
- Robot runs `k1_voice` node: mic -> VAD (silero or webrtcvad) -> openWakeWord -> on hit: publish `/{robot_ns}/voice/wake`, open stream to ASR service tagged `robot_ns`, speaker mute/duck while robot is speaking (echo guard).
- Only the woken robot streams to ASR and replies. Others never open a stream, so no cross talk by construction.
- Second safety layer: ASR service takes ownership by `robot_ns`; a global "address lock" (first wake within 1.5 s wins, by highest score) so two robots that both false-trigger do not both answer. Needs all robots on same network (robotics_5G ok); use a small UDP/ROS 2 topic `/fleet/voice_claim`.
- Also support "all robots" word (e.g. "everyone") if wanted: ask later.
- Mic hardware: K1 body is noisy (fans, gait). Test false accepts/rejects per robot at 1 m, 3 m, while walking. Target <1 false wake/hour, >90% recall at 2 m standing.
- Mic is robot-mounted C-Media USB: confirm it is the same on all 6 (`lsusb`), and ALSA device name stable (udev rule or `hw:CARD=` by name).
- Follow CLAUDE.md: node param `robot_ns` (default `k1_0`), topics `/{robot_ns}/voice/...`, package `k1_voice`, ament_python. ROS env: system jazzy on laptop; robot is Humble: check which distro the robot node runs under (docs say Humble) and keep message types std_msgs only to stay portable.

Topics (per robot):
- `/{ns}/voice/wake` (std_msgs/String: phrase + score)
- `/{ns}/voice/transcript` (std_msgs/String, final)
- `/{ns}/voice/say` (std_msgs/String, text to speak)
- `/{ns}/voice/state` (idle/listening/thinking/speaking)

TTS (not asked but needed for "talk back"): SDK has `robot.play_audio(file)` (ROBOTS.md:191). Use Piper TTS (CPU, small) on robot or on server; play via SDK or `aplay` to UAC speaker. Verify SDK vs ALSA conflict tonight.

## 4. Phase C: Cosmos3-Edge on robot + tool calling

C0 (tonight, 30 min, gate): on ONE robot, `free -h`, `tegrastats`, stop non-essential services, check disk, check TensorRT version in JetPack 6.2 vs what TensorRT-Edge-LLM v0.10.1 needs. If it needs TRT/CUDA newer than JetPack 6.2 supplies, STOP and go fallback (server-side VLM). Do not reflash the robot.
C1: Install TensorRT-Edge-LLM v0.10.1, export + build engine on device (use NVMe, 396 GB free), run model card sample. Measure peak RAM with cuVSLAM running. Decide: resident / on-demand / offloaded.
C2: Camera: findings doc says Jetson CSI camera stack absent; check which image source exists (RGBD topic used by cuVSLAM, see memory k1-cuvslam-status). VLM input = one RGB frame resized to ~896x448 on `/{ns}/...image` topic.
C3: Tool calling by prompt + constrained JSON (the checkpoint has no native tool API):
  - System prompt lists tools as JSON schema; model must output `{"tool": "...", "args": {...}}` or `{"say": "..."}`.
  - `enableThinking` on for JSON (card: 24/24 vs 11/24). Costs latency; budget ~1-2 s.
  - Validator in node: parse, check against schema, reject unknown tool, clamp args. Never pass raw model text to the robot SDK.
  - Initial safe tool set (no locomotion at first): `describe_scene`, `look_at(yaw,pitch)` (head only), `wave`, `say(text)`, `get_battery`. Add `walk` etc. only behind explicit confirmation and the existing safety layer (policy/SDK mode switch).
C4: Wire: wake -> ASR text -> `k1_agent` node (grabs latest frame + text, calls VLM) -> validated tool call -> executor (SDK) / `say` -> TTS.
C5: Evaluate: 30 scripted commands + scenes, measure JSON valid rate, correct tool rate, end-to-end latency (wake to first audio), RAM. Compare to server-side bigger VLM. Card says it is unvalidated live and tested on only two benchmarks, so treat accuracy as unknown.

## 5. Evening checklist (in order)

1. [ ] Pick one robot (non-A1/A2, those are out of commission). `ssh` alias per ROBOTS.md. Confirm net/NAT per header note (k1nat is lost on reboot).
2. [ ] `lsusb`, `arecord -l`, `aplay -l`; record 10 clips; record while walking.
3. [ ] C0 gate for Cosmos (RAM, TRT version).
4. [ ] Laptop: run ASR bake-off on clips (Nemotron vs faster-whisper vs parakeet).
5. [ ] Install openWakeWord on robot (`uv`/venv, aarch64 wheels, onnxruntime CPU); test with stock "hey jarvis" first to validate mic path before custom words.
6. [ ] Train 6 custom wake words on laptop; deploy 1, test cross talk with 2 robots.
7. [ ] Log results in this file; add Slides/Drive note per memory report-cadence.

## 6. Risks

- RAM on Orin NX (4.5 GiB free) is the main blocker for on-robot VLM.
- Nemotron ASR on Jetson unproven; server-side avoids it but needs WiFi latency + a GPU box always on.
- Motor/fan noise degrades wake word; may need beamforming/better mic placement or noise suppression (RNNoise).
- Echo: robot speaker into own mic; mute during TTS.
- TensorRT-Edge-LLM version vs JetPack 6.2 compatibility unknown until C0.
- Third-party quant, OpenMDW licence "derivative work": fine for research, check before shipping.

## 7. Open questions for user

- Wake phrase scheme (names per robot? a shared "everyone" word?).
- Languages needed (English only? then Nemotron's 25-language edge is moot).
- Is internet/offboard compute acceptable for ASR, or must everything run onboard?
- Should VLM be allowed to trigger walking, or perception/gesture/speech only for now?

---

## 8. Decisions after user feedback (2026-10-28, later)

### 8.1 Languages: EN + ES + ZH + HI
- **Nemotron-Unified-ASR is OUT as primary.** Its 25 languages are European only: EN and ES yes, ZH and HI no.
- Default candidate: **Whisper large-v3-turbo** via faster-whisper (CTranslate2, fp16) on GPU box. Covers all 4, has language ID. Not natively streaming: VAD-segment the utterance, transcribe after end-of-speech. Commands are short, so ~0.3-0.8 s after speech ends. Acceptable.
- Bake-off candidates (verify existence/licence/Hindi+Chinese quality before relying on them): Whisper large-v3 / turbo, SenseVoice (strong ZH, also EN), a Hindi-specialised model (AI4Bharat IndicConformer or similar) if Whisper Hindi WER is bad, Nemotron for EN+ES only as speed baseline. Router option: language-ID first, then per-language model.
- Test set: 10 commands x 4 languages x (standing, walking) recorded on a K1. Metrics: WER/CER, command-intent accuracy (what matters), latency.
- **Latency verdict:** offboard is fine. LAN WiFi RTT + audio upload for a 2-3 s command is ~100-300 ms. Total wake->transcript ~0.5-1.2 s with Whisper-turbo on GPU. No need for single-language on-robot ASR. Keep wake word + VAD on robot so it still reacts (LED/beep/"yes?") instantly and works if the ASR box is down.
- Fallback if WiFi is flaky: on-robot `whisper.cpp`/faster-whisper small, one language. Not planned, only if measured latency > ~1.5 s.
- VLM multilingual: unverified. Cosmos3-Edge is likely English-strong. Pipeline option: ASR transcript (any lang) -> small server LLM/or VLM prompt "reply in the user's language", tools names always English. Test ES/ZH/HI intent in C5.
- TTS needs ES/ZH/HI voices too (Piper has ES/ZH/HI voices of varying quality; verify). Reply in detected language.

### 8.2 Wake word names
"A1/B1" as spoken words are poor wake words: ultra short (2 syllables with "ay-one"/"bee-one"), differ by one consonant, and "one/two/three" repeat across robots. Keep IDs A1..B3 for `robot_ns`/SSH, but add spoken names starting with the same letter, 3 syllables, distinct vowels, easy for ES/ZH/HI speakers, no brand names (not Alexa/Siri/Jarvis):

| ID | Spoken name | Wake phrase |
|----|-------------|-------------|
| A1 | Atlas   | "Hey Atlas" |
| A2 | Apollo  | "Hey Apollo" |
| A3 | Aurora  | "Hey Aurora" |
| B1 | Bravo   | "Hey Bravo" |
| B2 | Bamboo  | "Hey Bamboo" |
| B3 | Bonita  | "Hey Bonita" |

Rationale: A-set differ in stressed vowel (AT-las / a-POL-lo / au-RO-ra); B-set (BRA-vo / bam-BOO / bo-NI-ta). "Hey" prefix lengthens the phrase and cuts false triggers. Alternatives if any fail tests: Orion, Nova, Beacon, Bolt, Delta. Final check = confusion matrix: play each phrase from TTS in 4 languages/accents at each robot, count wrong-robot triggers (target 0). Swap names that confuse.
Note: A1/A2 currently out of commission, so names only matter for working robots first (A3, B1-B3).

### 8.3 Tool calling via built-in Booster SDK API
Executor maps validated JSON to SDK calls (ROBOTS.md key APIs):
| Tool | SDK call | Guard |
|------|----------|-------|
| `walk(vx,vy,vyaw,duration)` | `set_velocity` | only in WALK mode; clamp vx/vy/vyaw to conservative limits; auto stop (0,0,0) after `duration` (max few s); watchdog; stop on new "stop" |
| `stop()` | `set_velocity(0,0,0)` | always allowed, highest priority, also triggered by wake+"stop"/"alto"/"停"/"रुको" |
| `set_mode(mode)` | `set_mode` | allow PREP/WALK/DAMP only; confirm before leaving DAMP->WALK |
| `action(name)` | `execute_action` | whitelist of known action names (wave, etc.), list them tonight from the robot |
| `say(text)` | TTS + `play_audio` | mute mic while speaking |
| `look(yaw,pitch)` | head cmd | clamp |
| `get_battery`, `get_pose`, `describe_scene` | `get_battery`, `get_odometry`, VLM on `get_image('rgb')` | read-only |
Rules: model never emits raw SDK calls; JSON validated against schema; unknown tool = reject + say "didn't understand"; walking requires robot already in WALK and (first version) spoken confirmation for distance > 1 m; low battery / fall / PROTECT mode blocks motion; hard stop word always works. The ROS 2 path (`/{ns}/cmd_vel`, `/{ns}/leg_commands`) from CLAUDE.md is for our own policy stack; the voice agent uses the SDK so it does not fight the locomotion policy. Decide tonight which owner holds control when a custom policy is running (voice must not call `set_velocity` while CUSTOM mode runs).

### 8.4 Updated evening checklist additions
- [ ] Dump `execute_action` names + SDK mode list from a robot into `docs/`.
- [ ] Record 4-language clips (EN/ES/ZH/HI), run Whisper-turbo bake-off; check Hindi/Chinese quality.
- [ ] Check TTS voices for ES/ZH/HI.
- [ ] Test wake names confusion matrix before training all 6.

---

## 9. NeMo on the robot: live system analysis + install plan (2026-10-28)

Question: *can we install NeMo (to run Nemotron-Unified-ASR) ON the K1s?*
Method: **live probe of A1 over `ssh boosterk1.a1`** (only robot up; A3/B1/B2/B3 were
mid firmware-upgrade/offline, A2 charging). Laptop `enp2s0` cable re-plugged,
`robotics-lan` reactivated (192.168.50.125 + .250 + 192.168.123.222). All K1s are
identical hardware, so A1 answers the system question for the fleet.

### 9.1 What is actually on the robot (measured, A1)

| Item | Measured |
|---|---|
| Host / arch | `robot`, **aarch64**, L4T **R36.4.3** (JetPack 6.x), Ubuntu 22.04.5 |
| SoC GPU | Orin (sm_87), CUDA **12.6** toolkit in `/usr/local/cuda-12.6`, `nvcc` + `/usr/sbin/nvidia-smi` present |
| Python | **3.10.12**, pip 25.1.1, `python3 -m venv` OK, gcc/g++/git/curl present |
| **PyTorch** | **`torch 2.7.0+cu126` ALREADY INSTALLED, `cuda.is_available()=True`, device name "Orin"** (+ `torchvision 0.22.0`, `onnxruntime-gpu 1.22.0`, `onnx 1.18`, `numpy 1.26.3`) |
| Missing | `nemo`, `transformers`, `torchaudio` — none installed (clean slate) |
| RAM | 7.4 GiB total; **3.5 GiB available now** (3.6 GiB used by Booster stack; idle ~4.5 GiB per camera-findings doc); **zram swap 3.7 GiB, 0 B used** |
| Disk | NVMe `/` 467 G, **393 G free** |
| Runtime | no docker CLI; Booster's own `containerd`/`container` under `/opt/booster/bin`; ROS 2 Humble; `/opt/booster/{bin,BoosterAgent,BoosterAudio}` |
| Internet | **robot has NO internet now**: default gw = 192.168.50.1 (router has no uplink), DNS 127.0.0.53 stub, `curl pypi.org` → 000 |

### 9.2 NeMo requirements vs the robot (the actual "can we")

Checked against PyPI live (2026-10-28):
- `nemo_toolkit` current = **3.0.0, requires_python ≥3.10** → robot 3.10.12 ✅.
- `torch>=2.6.0`, **no upper bound** → robot's `torch 2.7.0+cu126` satisfies it; pip will
  **not** try to reinstall/replace the Jetson torch ✅ (biggest Jetson hazard is gone).
- Model card's runtime "NeMo Speech 3.1.0" = the `NVIDIA-NeMo/Speech` example runtime;
  pip entry point is still `nemo_toolkit[asr]`. If 3.0.0 ever refuses the checkpoint,
  pin to the version the card was built against.
- aarch64 wheel availability: `torchaudio 2.7.0 cp310 manylinux_aarch64` exists on PyPI
  ✅ (needed only if collections.asr imports it — it was NOT in the core requires we
  sampled; `soundfile` covers wav IO, `sentencepiece<1.0.0`, `transformers`,
  `soundfile` all have aarch64 wheels ✅).
- **Not needed for inference**: `apex`, `transformer-engine`, fused RNNT loss kernels —
  training-only. Greedy RNNT decoding is plain torch.
- GPU compute: FastConformer 0.6B on sm_87 fine; `.nemo` file = 2.5 GB (fp32 weights) →
  fp32 load ≈ 2.5–4 GB process peak (weights + activations, shared UMA with RAM).
- Disk: install ≈ 2–4 GB + 2.5 GB model → 393 G free is a non-issue.

**VERDICT: YES — NeMo is installable on the K1, and the preconditions are unusually
good (Jetson torch already there, CUDA works, py3.10, disk, aarch64 wheels exist).**
The real constraints are **RAM** and **internet-for-the-one-time-download**, not arch.

### 9.3 Risks / constraints (ranked)

1. **RAM**: 3.5–4.5 GiB available vs 2.5–4 GiB model process. v1 = **offline mode, load
   on demand, robot idle** (BoosterAgent/cuVSLAM up is the worst case — measure both).
   Streaming buffered mode recomputes 5.6 s left context per chunk = strictly MORE
   compute → **do not attempt streaming on the Orin in v1** (offline only).
2. **Internet for install only**: robot can't reach PyPI/HF until the laptop NAT +
   robot default route are fixed (§9.4 N0). Nothing at runtime needs internet.
3. **pip must not clobber Jetson torch**: install into a `--system-site-packages` venv
   WITH a constraints file pinning `torch==2.7.0`/`torchvision==0.22.0` as belt+braces.
4. **Firmware upgrades rewrite `/opt/booster`** → venv + model cache live in `/home`
   (or a data dir), never under `/opt`, so `booster-cli upgrade` can't wipe them.
5. Scope vs §8.1: Nemotron stays **OUT as primary** (no ZH/HI). On-robot NeMo is an
   **EN/ES experiment + fallback** — it must beat the off-robot bake-off on quality or
   latency to matter. Do not let this install silently become the architecture.
6. Only A1 probed; re-run the §9.1 table on B1 after its upgrade before trusting RAM
   numbers fleet-wide (hardware identical, background load may differ).

### 9.4 Install plan (phases, run when robots reachable)

**N0 — restore robot internet (laptop side + robot side, ~5 min):**
```bash
# laptop (persists only until reboot — commands also in docs/network_robotics_5G_2026-10-26.md):
sudo sysctl -w net.ipv4.ip_forward=1
sudo nft add table ip k1nat
sudo nft 'add chain ip k1nat post { type nat hook postrouting priority srcnat; policy accept; }'
sudo nft add rule ip k1nat post oifname "wlo1" ip saddr 192.168.50.0/24 masquerade
# robot A1 (runtime route, was default via router .1):
ssh boosterk1.a1 'sudo ip route replace default via 192.168.50.250 metric 100; sudo resolvectl dns wlP1p1s0 8.8.8.8 1.1.1.1'
# gate: ssh boosterk1.a1 'curl -sI https://pypi.org -o /dev/null -w "%{http_code}\n"'  → 200
```

**N1 — venv + NeMo (tmux on robot, ~10–20 min, ~3 GB):**
```bash
ssh -t boosterk1.a1 tmux new -d -s nemo 'bash -lc "
  python3 -m venv --system-site-packages /home/robot/nemo-asr &&
  printf \"torch==2.7.0\ntorchvision==0.22.0\n\" > /home/robot/nemo-asr/constraints.txt &&
  /home/robot/nemo-asr/bin/pip install -c /home/robot/nemo-asr/constraints.txt \"nemo_toolkit[asr]\" &&
  /home/robot/nemo-asr/bin/python -c \"import torch, nemo; print(\"nemo\", nemo.__version__, \"torch\", torch.__version__, torch.cuda.is_available())\" > /home/robot/nemo-asr/install.log 2>&1"'
```
Gate: `install.log` prints nemo version + `torch 2.7.0 True`. If pip wants to build an
sdist (fails for lack of an aarch64 wheel) note WHICH package — that is the finding,
not a blocker to force through.

**N2 — model download (2.5 GB, via NAT):**
```bash
ssh -t boosterk1.a1 'HF_HOME=/home/robot/.cache/huggingface huggingface-cli download nvidia/nemotron-labs-unified-asr-0.6b nemotron-labs-unified-asr-0.6b.nemo'
# or copy the .nemo from the laptop over scp (already-cached copy) to skip the robot-side download.
```

**N3 — offline smoke + measurement (the gate):**
- Script: load via `nemo_asr.models.ASRModel.from_pretrained(<local .nemo path>)`,
  `transcribe()` the §8.2 test clips (16 kHz mono), `target_lang="en"`.
- Record: model load time, **RTF** per clip, peak RSS (`tegrastats`/`/proc`), WER vs the
  same clips on faster-whisper tiny.en (current) — idle AND with BoosterAgent running.
- Try fp16 (`model.half()`) only if fp32 OOMs; note any accuracy change.
- Gate to proceed: RTF ≤ 0.5 on Orin, peak RSS ≤ 3 GiB idle, WER ≤ tiny.en.

**N4 — decision:** if N3 passes AND §8.1 bake-off wants EN/ES on-robot → wrap as the
same `asr` callable interface `robot_audio.py` already uses (swap `WhisperModel` for the
NeMo transcriber, venv python in `robot/run.sh`). If it fails → **delete nothing, keep
off-robot plan (Phase A) as the architecture**; on-robot stays tiny.en.

### 9.5 Checklist (added)
- [x] N0 internet restore + pypi 200 gate — **DONE 2026-10-28**, now **persistent**: A1 route
  `via .250 metric 100` + DNS `8.8.8.8/1.1.1.1` auto-restored on every boot by
  `k1-nat-route.service` (unit + `/home/booster/nat-route.sh`, rolled out to all 6 by
  `/Storage/tmp/opencode/nat-all6-watcher.sh`; details in `docs/network_robotics_5G_2026-10-26.md`).
  Gates pypi 200 / HF 200 re-verified on A1 after battery swap + reboot.
- [x] N1 venv install in tmux + install.log gate — **PASSED**: `PIP_EXIT=0`,
  `VERIFY nemo 3.0.0 torch 2.7.0 cuda True`, venv 1.8 GB. No sdist builds, no aarch64 gaps.
- [x] N2 model to /home — **PASSED**: `/home/booster/nemo-asr/model.nemo` 2,507,735,040 B,
  sha256 `1718cc1b…46936` **SHA256_OK** (direct curl + sha check, 2.5 GB in ~2.5 min via NAT).
- [x] N3 offline smoke: RTF/RSS/WER, idle vs running, fp32 vs fp16 — **PASSED (fp16)**:
  fp32 OOM-killed → laptop fp16 conversion → robot: cuda/fp16, load 28 s, **peak RSS 2.0 GB**,
  **warm RTF 0.11–0.13**, transcription correct (0 errors vs known text, beats tiny.en ~7%).
  Full numbers + the `transcribe` prompt-key workaround: §9.6.
- [ ] Re-probe B1 after firmware upgrade; compare §9.1 RAM (all 6 now on fw 1.8.1.2 per §10 —
  re-probe = spot check only)
- [x] N4 decision recorded here (§9.6): **NeMo = approved EN/ES on-robot fallback experiment,
  NOT primary** — keep §8.1 "Nemotron OUT as primary" (no ZH/HI); primary ASR stays server-side
  Whisper-class per §2/§10.

### 9.6 Execution log (2026-10-28/29 session)

**Path correction**: plan §9.4 wrote `/home/robot/…`; actual robot user is `booster` →
**`/home/booster/nemo-asr`** (venv, model, logs all live there).

**N1 findings (fixed on the way):**
- `--system-site-packages` shadowing: stale Ubuntu **`coverage` 5.x** in dist-packages broke
  `numba 0.68` (`coverage.types` missing) at `nemo.collections.asr` import → fixed with venv
  `pip install "coverage>=7"`. Belt-and-braces for any other stale stdlib-ish shadowing.
- NeMo **3.0 dropped `restore_model`**: loader is
  `ASRModel.from_pretrained(model_name=…, map_location=…)` (rejects a local file path with
  `HFValidationError` — repo-id only) → for local `.nemo` files use
  **`ASRModel.restore_from(path, map_location=torch.device(...))`**.

**N3 attempt 1 — fp32 → OOM-killed (exit 137), the §9.3 #1 risk, measured:**
- tegrastats peak: **RAM 7276/7621 MB + SWAP 3810/3810 MB full** during `restore_from` on cuda.
  Steady need ≈ 8.6 GiB raw with the Booster stack (3.6 GiB) resident — not survivable on-robot.
- Decision: **never stop Booster/motor services to free RAM** (standing robot could collapse) →
  **fp32→fp16 conversion moved to the laptop** (16 GB RAM, CPU torch), robot only ever loads the
  fp16 file (~1.25 GB weights → load peak ≈ 2.5 GiB + stack ≈ 6.7 GiB < 7.4 GiB).

**Laptop conversion venv bug (found + fixed, worth remembering):**
- `torch 2.7.0+cpu` in `/Storage/tmp/opencode/nemo-conv` failed with
  `AttributeError: module 'torch._C' has no attribute 'OutOfMemoryError'` — NOT a bad wheel:
  the shell's **`LD_LIBRARY_PATH` (from ROS colcon env) ends in
  `…/thesis/g1_perception_ws/.venv/…/torch/lib/`**, whose `libtorch_python.so` hijacked the
  venv's `torch/_C` shim (RUNPATH `$ORIGIN` loses to `LD_LIBRARY_PATH`) → mixed torch build.
  Fix: run with `env -u LD_LIBRARY_PATH -u PYTHONPATH`. **Any torch/nemo run on this laptop
  shell must strip those two vars** (robot env verified clean — install VERIFY passed there).

**N3 attempt 2 — PASSED (all gates), 2026-10-28/29:**

*fp16 conversion (laptop, `/Storage/tmp/opencode/`):* plain `m.half()` + `save_to` was NOT enough —
round-trip `restore_from` **rebuilt the model fp32** (state dict cast on load). Working recipe:
`torch.set_default_dtype(torch.float16)` **before** `restore_from` (model instantiates fp16) →
`m.half()` (folds 48 leftover fp32 `pos_bias_u/v` params, 0.2 MB) → reset default dtype →
transcribe under `torch.autocast("cuda", fp16)`. Files: `model_fp32.nemo` (2,507,735,040 B,
sha `1718cc1b…`) → `model_fp16.nemo` (**1,254,307,840 B**, sha `0fe71f62…`, verified on both
laptop and A1).

*Upstream bug found:* `ASRModel.transcribe()` on the prompt variant fails with
`ValueError: Unknown prompt key: 'None'` — the Lhotse dataloader **ignores `default_lang`**
(log says: "configuration keys are ignored … default_lang") and reads
`cut.supervisions[0].language`, which NeMo's temp transcribe manifest leaves `None`.
Workaround (in `smoke.sh`): monkeypatch `_get_prompt_index_for_cut` → fall back to
`self.cfg.get("default_lang")` (i.e. our `target_lang="en"`). Prompt keys available:
`en, en-US, en-GB, es, es-ES, zh-CN/ZH/TW, hi-IN, English` (+`auto` idx 101).

*Gates (measured with the full Booster stack resident — worst case; cache dropped first):*

| Gate | Target | Measured | Verdict |
|---|---|---|---|
| device / dtype | cuda fp16 | `device cuda`, `param_dtypes ['torch.float16']` | ✅ |
| load time | — | 27.9–28.6 s (import 19 s + restore) | (one-time, load-on-demand) |
| peak RSS | ≤ 3 GiB | **1.98–2.02 GB** | ✅ |
| RTF cold | ≤ 0.5 | 0.476 (includes dataloader build) | ✅ |
| RTF warm | ≤ 0.5 | **0.134 / 0.107** (1.39 s / 1.11 s per 10.44 s clip) | ✅ |
| transcription correctness | ≈ reference | see below | ✅ |

*Correctness check:* `ref_sample.flac` (Narsil/asr_dummy 1.flac) → NeMo: *"He hoped there would
be stew for dinner, turnips and carrots and bruised potatoes and fat mutton pieces to be ladled
out in thick, peppered, flour fattened sauce,"* — cross-checked with faster-whisper **tiny.en**
on the same file (identical sentence; tiny.en differs on 2 words: "and/in", "flower/flour" →
tiny.en ≈ 7% WER, **NeMo ≈ 0** on the known LibriSpeech text). The earlier "a man said to the
universe" reference expectation was wrong (different dummy clip).

*Mic clip for a real-noise test — resolved by §9 findings/§11 below: the C-Media USB (0d8c:0012)
is the **speaker** (card 0, playback only); the mic is the NationalChip card 1 array, held
exclusively by Booster's `container/audio`. Capture without takeover = `/booster/audio` RPC
(`init_capture_stream`); with takeover = `k1voice.sh` (already mic-tested in §11). No plain
`arecord` path exists — noted for the WER-vs-live-noise step, not a NeMo blocker.*

**N3 verdict: PASS.** On-robot fp16 NeMo inference is viable on the K1 within all plan gates
(even with the stack live). Robot-side state survived the battery swap; NAT restored via the new
persistent `k1-nat-route.service` (see `docs/network_robotics_5G_2026-10-26.md`).

**N4 — decision:** N3 passes technically, BUT the scope gates from §8.1 and §10 (parallel
workstream) still stand: Nemotron/NeMo has **no ZH/HI**, while the assistant needs EN+ES+ZH+HI
server-side. So: **keep off-robot Whisper-class ASR (§2 Phase A / §10 revised plan) as the
architecture; keep this on-robot NeMo install as the EN/ES low-latency fallback experiment**
(RTF 0.11 on-device beats any round-trip). Wiring into `robot_audio.py` as primary = **not
approved by this plan**; revisit only if the 4-language bake-off fails server-side.

---

### 9.7 Step-4 live voice chat results (2026-10-29, A1)

**Step 4 achieved — live conversation with Nemotron backend instead of Whisper.**

Setup on A1 (2026-10-29):
- `gdm3` disabled (`systemctl disable --now gdm3`) + reboot → 5.7 Gi available, swap 0
- `k1-nat-route.service` enabled+active → route auto-restored on boot, pypi 200 / hf 200
- `nemo-asrd.service` started → daemon ready, fp16, load ~48–61 s
- `k1voice.sh start a1` → `K1_CHAT_ASR=nemo` (default in `run.sh`), `NemotronAsr` HTTP to `:8090`
- `K1_KOKORO_DEVICE=cpu` → Kokoro TTS on CPU (frees GPU arena for NeMo; uncapped CUDA arena OOM-killed daemon)
- Voice log: `/home/booster/k1_chat/voice.log`

**Live results (user talked to robot, Nemotron ASR → OpenRouter LLM → Kokoro TTS):**

| Utterance (Nemotron heard) | ASR wall_s | TTS wall_s | Notes |
|---|---|---|---|
| "Oh." | 1.56 | 5.50 | first utterance |
| "Finally broke out of sand." | 1.55 | 4.68 | |
| "Can you please go to help?" | 1.81 | — | session cut at timeout |

- Empty/noise segments return `""` (filtered by `_HALLUCINATIONS` = `{""}`), do **not** reach LLM/TTS — no Whisper-style hallucination on silence.
- **0 OOM kills** during the session (daemon `OOMScoreAdjust=500`, torch cache free before transcribe, Kokoro CPU).
- RAM tight (~90–200 Mi available with voice + daemon + stack) but stable.

**What still needs fixing (low priority, conversation works):**
- Mic gain low (~-37 dBFS speech peaks) → some quiet segments return empty. Raise `K1_CHAT_MIC_GAIN` (currently 16) if needed.
- Daemon not enabled at boot (manual start only) — intentional to avoid OOM at boot; `postboot.sh` starts it.
- A2 install not done (user instructed: don't touch A2). Run `/Storage/tmp/opencode/k1-asr-install.sh a2` when ready.

---

## 9. Findings on A1 / A2 (2026-10-29 ~07:20, read-only probes, nothing changed)

Both reachable (A1 192.168.50.82, A2 192.168.50.215). Identical: Orin NX, JetPack 6.2 (L4T R36.4.3), TensorRT 10.3.0.30 / CUDA 12.5 pkgs, py3.10, NVMe ~390 GB free, 7.4 GiB RAM.

RAM: only **~3.4 GiB available** with Booster stack running (1.1-1.6 GiB truly free). Cosmos3-Edge peak 3.4-4.8 GB => **C0 gate = does NOT fit on-robot** as-is. Server-side VLM is the path unless Booster services are stopped. TRT 10.3 vs TensorRT-Edge-LLM v0.10.1 requirement still unchecked (likely needs newer TRT).

Audio hardware:
- Mic = **NationalChip "UAC Speaker" USB, 6-ch 16 kHz** (ALSA card 1, capture-only; pulse source `alsa_input.usb-NationalChip...multichannel-input`). Looks like a mic ARRAY with DOA.
- Speaker = C-Media USB (card 0, playback only).
- The mic is **held exclusively** by Booster `/opt/booster/bin/container/audio` (pid per boot). `arecord` => "Device or resource busy"; pulse capture returns empty file. Do NOT kill it blindly.

Booster already has a voice stack:
- `lui` process (container/lui), `booster_agent_manager` + default agent (`com.boosterobotics.default`), topic `/lui_asr_chunk` (booster_interface/AsrChunk, field `text`), `/ai_subtitle` (Subtitle), `/LuiApiTopicReq/Resp`, `/LuiApiOperationEvent`.
- Audio RPC server `/booster/audio/*` (RpcReqMsg/RpcRespMsg): `init_capture_stream`, `start_capture_stream`, `stop/destroy_capture_stream`, **`get_doa_angle`**, `init_player`, `send_pcm_data`, `start_player`, `set_system_volume`, `set_system_mute`, `register_client`. => We can get PCM from the mic and play audio WITHOUT stealing the device, via these RPCs (ROS 2 Humble, ROS_DOMAIN_ID=0, FASTRTPS profile /opt/booster/BoosterRos2/fastdds_profile.xml).
- Preinstalled skills (actions) found in `/opt/booster/BoosterAgent/skills/official_skills`: wave, shake_hand, cheer, respect, chest_salute, lucky_cat, point_to_sky, arms_crossed, dabbing, siuuu, lie_down, carry, dances, kicks. These are the `execute_action`/agent-skill whitelist candidates.

Implications:
1. Open: does Booster's built-in LUI already do wake word + cloud ASR/LLM? If yes, our assistant and theirs would both answer. Need test: speak near A1 while echoing `/lui_asr_chunk` and `/ai_subtitle`.
2. Capture path = `/booster/audio/init_capture_stream` RPC (schema unknown, dump from `booster_msgs` / BoosterAudio libs). Fallback = disable `lui` + audio holder (needs sudo/root + risk to Booster app features).
3. DOA gives direction of speaker: useful extra cross-talk filter and for turning head toward the speaker.
4. Real-time safety: mic streaming must not load the Booster motion containers; keep our node niced and CPU-light (openWakeWord ONNX on 1 core).

---

## 10. Prior work found in sibling worktrees (supersedes parts of sections 1-9)

Worktrees: `~/Projects/wt-k1-chat` (feat/k1-chatbot, HANDOFF.md), `wt-asr`, `wt-k1-tools` (tools/brain/arbiter), `wt-k1-vision` (PLAN_VISION.md). All 6 robots on fw 1.8.1.2 (A1/A2 confirmed 2026-10-29). A1 and A2 already have `~/k1_chat` (venv, models, run.sh).

### Mic lock takeover (wt-k1-chat/robot/run.sh)
- `audio` is supervised by Booster `containerd`; killing the pid just respawns it. Use its HTTP API on the robot: `http://127.0.0.1:20001/service/{status,kill,boot}` with body `{"service":"audio"}` (fw 1.8.x only).
- run.sh: preflight (API answers + `~/k1_chat/venv` exists) -> `kill` -> wait OFFLINE -> run our process on `plughw:CARD=Speaker` -> `trap EXIT/TERM/INT/HUP` => `boot` audio again, so audio comes back even if ssh drops.
- Laptop wrapper: `wt-k1-chat/scripts/k1voice.sh start|stop|smoke|log|fetch|calibrate|mic-test|status|restore <robot>`. `restore` = just make sure audio is running.
- Cost: while we hold the mic, Booster's own LUI/ASR/TTS and `/booster/audio/*` RPCs are down. `/booster/audio` capture RPC route (section 9) is the alternative that avoids the takeover; not tried.

### Already built (do not redo)
- Local voice on all 6: mic 6ch mean ch0-3 -> energy VAD -> faster-whisper tiny.en (CPU) -> OpenRouter LLM -> Kokoro-82M TTS (GPU) -> aplay. Known issue: Whisper hallucinates on noise, 6-12 s on some clips, English only.
- Tools/arbiter/e-stop (feat/k1-tools): chat clamped 0.4/0.2/0.5, 1 s expiry, 2 s manual hold-off, e-stop -> PREPARE latch. Rule: chat never changes locomotion mode except e-stop.
- On-prem models via laptop proxy `llm_panel` on :8000 (dl GPU3): Cosmos-Reason2-2B vision (~1 s/look), Bolt E4B / gemma-4-E4B-it tool calls (3/3 tests).
- Wake word: NOT built (k1voice is always-listening VAD; no per-robot names). That part of this plan is still new.

### Cosmos3-Edge on-robot: second blocker
Edge-LLM v0.10.1 supports Orin only on JetPack 7.2; K1 is JP6.2/CUDA 12.6 and cannot be reflashed. Documented JP6.2 path is v0.10.0 flags (`-DCUDA_CTK_VERSION=12.6`). Plus RAM (~3.4 GiB available). So: server-side Cosmos (Reason2-2B already works; dl has `nvidia/Cosmos3-Edge` + `vllm/vllm-omni:cosmos3`) first; on-robot only as a stretch.

### Revised plan
1. Re-use k1voice + tools stack. Add only: wake word gate (openWakeWord, per-robot phrase, names in 8.2), multilingual ASR (Whisper-turbo/other on server instead of tiny.en), multilingual TTS check, DOA-based tie-break.
2. ASR: stream utterance to laptop/dl service; Nemotron-unified is EN/ES only, Whisper-class needed for ZH/HI (8.1). Wt-asr notes list Nemotron-unified as the ASR candidate, which does not cover the 4 languages requested.
3. Vision/tools: use the llm_panel endpoints; no on-robot VLM tonight.

## 11. A1 mic-test (2026-10-29, wt-k1-chat run.sh mic-test, speaker ~1-2 m, said "Hey Apollo" x3)
- Takeover + auto restore of Booster audio worked twice (status "running" after).
- ch0 rms 57/peak 408, ch1 58/440, ch2 60/464, ch3 60/464 (ch2 == ch3 identical peaks), ch4 4/65, ch5 3/64 => ch0-3 live, ch4-5 dead/reference. Speech peak only ~-37 dBFS: LOW level.
- tiny.en: ch0 "Hey, boost, you know..." ch2/3/mean "Hey, Bustin Stephen. Hey Apollo." ch1 empty. Wake name was misheard 2 of 3 times => tiny.en unusable for wake word; use a dedicated keyword model (openWakeWord) + bigger ASR on server.
- First run (silent) rms 3-19: mic noise floor is very low, so SNR is fine; just raise gain / normalise.
- TODO: `calibrate a1`, `fetch a1` (wavs in audio_dumps/a1), try ch2 alone vs mean(ch0-3), test while walking, 3 m distance.

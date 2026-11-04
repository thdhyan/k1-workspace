`k1_chat`: voice and VLM agent with tool calls, plus a YOLO and depth service. It runs on the robot and is started
from the laptop.

```bash
bash scripts/demo.sh up      # STT on the laptop :8090, NAT, YOLO :8092 and agent + console :8091 on A1
bash scripts/demo.sh down    # [robot] [--all: also stops laptop STT]
```
- Console: http://192.168.50.82:8091/. Start every command with "Apollo". "Stop" always works.
- Runbook: [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md). Access and fleet: `docs/ACCESS.md`, `docs/FLEET.md`.
- Fleet registry: `src/k1_chat/fleet.json` (package data).
- Tests: `pytest tests` (markers `robot`, `net`, `onprem` are deselected by default).

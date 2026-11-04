#!/usr/bin/env python3
"""Run existing test files separately, retaining collection failures and JUnit.

Usage: python3 scripts/audit-tests.py --output /tmp/k1-test-audit
Use the desired environment's Python to run this script. Live robot/network
tests are deselected. Existing local fake-server tests can bind localhost/UDP.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in sorted((root / "libs").glob("k1-*/src")))
    files = sorted(p for p in (root / "tests").glob("test_*.py")
                   if p.name != "test_refactor_contracts.py")
    files += sorted(p for p in (root / "libs").rglob("test_*.py")
                    if "tests" in p.parts or "test" in p.parts)

    def run(path):
        rel = str(path.relative_to(root))
        slug = rel.replace("/", "__").removesuffix(".py")
        cmd = [sys.executable, "-m", "pytest", rel, "-q", "--tb=short",
               "-m", "not robot and not net and not onprem", "-p", "no:cacheprovider",
               f"--junitxml={out / (slug + '.xml')}"]
        start = time.monotonic()
        with (out / (slug + ".log")).open("w") as log:
            log.write("COMMAND: " + repr(cmd) + "\n")
            log.flush()
            proc = subprocess.Popen(cmd, cwd=root, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            try:
                rc = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                rc = proc.wait()
                log.write(f"\nAUDIT: {args.timeout}-second timeout; process group killed.\n")
        result = dict(file=rel, returncode=rc, timeout=timed_out,
                      seconds=round(time.monotonic() - start, 2), log=slug + ".log",
                      junit=slug + ".xml", command=cmd)
        print(f"{rc:2} {result['seconds']:5.1f}s {rel}", flush=True)
        return result

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, files))
    (out / "existing_results.json").write_text(json.dumps(dict(
        python=sys.version, pythonpath=env["PYTHONPATH"],
        excluded_marks=["robot", "net", "onprem"], results=results), indent=2) + "\n")
    return int(any(r["returncode"] != 0 for r in results))


if __name__ == "__main__":
    sys.exit(main())

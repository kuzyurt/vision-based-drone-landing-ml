"""Run a chosen subset of the bounded search suite with N parallel trials.

The revision's own entry point runs cases one after another. Each trial is
already isolated in its own subprocess (own output directory, own PX4 instance,
own renderer), so the same `_trial` worker can be started several times at once.

Usage:

    python -B -m training_runs.search_frames_20261108.replay_benchmark.parallel_trials \
        --name subset_20261108 --workers 3 --cases case-a case-b ...
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from benchmark.common import ROOT, sha, utc, write  # noqa: E402
from benchmark.revisions.bounded_search_20261026.spec import HERE, verify  # noqa: E402
from benchmark.revisions.bounded_search_20261026.student import policy  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--cases", nargs="+", required=True)
    args = parser.parse_args()
    if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.name):
        parser.error("unsafe run name")

    plan = verify()
    by_id = {case["id"]: case for case in plan["cases"]}
    unknown = [c for c in args.cases if c not in by_id]
    if unknown:
        parser.error(f"unknown cases: {unknown}")
    cases = [by_id[c] for c in args.cases]

    job_policy = policy()
    context = dict(
        plan_sha256=plan["plan_sha256"],
        runtime_sha256=sha(ROOT / "environments/runtime.json"),
        revision_receipts_sha256=sha(HERE / "source_receipts.json"),
        inference_device=args.device,
        control_hz=25,
        backend="windows_mujoco_px4",
        scenario_revision="bounded_search_20261026",
    )
    out = HERE / "runs" / args.name
    out.mkdir(parents=True, exist_ok=False)
    write(out / "run.json", dict(created_utc=utc(), context=context, policies=[job_policy["id"]],
                                 cases=[c["id"] for c in cases], training_eligible=False,
                                 parallel_workers=args.workers))
    (out / "jobs").mkdir()

    pending = list(cases)
    running: list[tuple[str, subprocess.Popen, float, int]] = []
    free_slots = list(range(args.workers))
    results = []
    started = time.time()

    def launch(case: dict) -> None:
        destination = out / job_policy["id"] / case["id"]
        job = out / "jobs" / f"{case['id']}.json"
        write(job, dict(policy=job_policy, case=case, output=str(destination), context=context))
        log = (out / f"{case['id']}.log").open("ab")
        slot = free_slots.pop(0)
        process = subprocess.Popen(
            [sys.executable, "-B", "-u", "-m", "benchmark.revisions.bounded_search_20261026",
             "_trial", "--job", str(job)],
            cwd=ROOT.parent, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        running.append((case["id"], process, time.time(), slot))
        print(f"[{time.time()-started:6.0f}s] start {case['id']} slot={slot}", flush=True)

    while pending or running:
        while pending and len(running) < args.workers:
            launch(pending.pop(0))
        time.sleep(5)
        for entry in list(running):
            case_id, process, began, slot = entry
            if process.poll() is None:
                continue
            running.remove(entry)
            free_slots.append(slot)
            destination = out / job_policy["id"] / case_id
            result_path = destination / "result.json"
            if result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                results.append(result)
                print(f"[{time.time()-started:6.0f}s] done  {case_id} "
                      f"{result.get('outcome', result.get('status'))} "
                      f"({(time.time()-began)/60:.1f} min)", flush=True)
            else:
                print(f"[{time.time()-started:6.0f}s] FAIL  {case_id} rc={process.returncode} "
                      f"(no evidence; see {case_id}.log)", flush=True)
            write(out / "summary.json", dict(context=context, training_eligible=False,
                                             results=results,
                                             wall_minutes=round((time.time() - started) / 60, 1)))

    landed = sum(1 for r in results if r.get("outcome") == "landed")
    print(f"finished {len(results)}/{len(cases)} in {(time.time()-started)/60:.1f} min, landed={landed}",
          flush=True)


if __name__ == "__main__":
    main()

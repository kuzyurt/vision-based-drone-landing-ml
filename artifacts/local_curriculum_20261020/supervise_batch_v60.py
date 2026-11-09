"""Unattended review batch: fly, measure, digest, approve - one episode at a time.

Why this wrapper exists
-----------------------
The v60 runner is deliberately frozen and refuses to rerun a case directory, so a
flight lost to external RAM pressure leaves a preserved failure and no result.  The
machine here has 16 GiB shared with the user's own applications, so free memory
moves by gigabytes while a flight is running.  This supervisor:

* waits for a real admission margin before starting (measured, not assumed);
* retries a memory-aborted flight under a NEW name, so the failed attempt stays in
  the record exactly as it happened;
* after every successful flight runs the microscope (truth timeline + acceptance
  checks + video join), the LLM digest (readable transcript) and the approval gate;
* writes a heartbeat every poll so an unattended run can be supervised, and a
  queue_state.json that names exactly which episodes were approved.

It never edits sources, never deletes a case directory, never kills another
process, and never marks an episode training-eligible on its own: only
``approve_episode.py`` can do that, and only from measured checks.

Usage
    python supervise_batch_v60.py --situations E01 E02 E03
    python supervise_batch_v60.py --situations E01..E11 --admission-gib 3.2
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "review_v60"
JOBS = REVIEW / "jobs"
LOGS = REVIEW / "logs"
TOOLS = ROOT.parent / "teacher_repair_20261020" / "tools"
HEARTBEAT = REVIEW / "batch_heartbeat.json"
STATE = REVIEW / "batch_state.json"
RUNNER = ROOT / "run_windows_review_v60.py"
SITUATION_JOBS = {
    "E01": "E01_nominal",
    "E02": "E02_distractors",
    "E03": "E03_yaw",
    "E04": "E04_close_loss",
    "E05": "E05_visible_start",
    "E06": "E06_search_near",
    "E07": "E07_search_mid",
    "E08": "E08_search_far",
    "E09": "E09_terminal_handoff",
    "E10": "E10_natural_rescue",
    "E11": "E11_expired_memory",
}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path: Path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    os.replace(tmp, path)


def free_gib():
    return psutil.virtual_memory().available / 2 ** 30


def my_flights():
    """Only flight processes this user started, never other applications."""
    found = []
    for process in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(process.info["cmdline"] or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "run_windows_review_v60.py" in cmd and "--job" in cmd:
            found.append(process.pid)
    return found


def job_for(situation: str, name: str, instance: int) -> dict:
    template = json.loads((ROOT / "review_batch_v1/jobs" / f"{SITUATION_JOBS[situation]}.json").read_text())
    template["name"] = name
    template["instance"] = instance
    template["purpose_contract_version"] = "v60"
    template["mode"] = "expert"          # teacher repair phase: expert demonstrations only
    template["training_eligible"] = False
    path = JOBS / f"{name}.json"
    path.write_text(json.dumps(template, indent=2))
    return template


def run_step(command, log_path: Path, timeout=None):
    with log_path.open("a") as log:
        log.write(f"\n=== {utc()} {' '.join(str(c) for c in command)}\n")
        log.flush()
        process = subprocess.run(command, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    return process.returncode


def analyse(case: Path, situation: str):
    """Microscope -> digest -> approval, all recorded; failures are not hidden."""
    log = LOGS / f"{case.name}_analysis.log"
    report = {}
    report["microscope"] = run_step([sys.executable, "-u", str(TOOLS / "flight_microscope.py"), str(case)],
                                    log, timeout=3600)
    report["digest"] = run_step([sys.executable, "-u", str(TOOLS / "llm_flight_digest.py"), str(case)],
                                log, timeout=1800)
    report["approve"] = run_step([sys.executable, "-u", str(TOOLS / "approve_episode.py"), str(case),
                                  "--situation", situation], log, timeout=900)
    approval = case / "APPROVAL.json"
    if approval.exists():
        payload = json.loads(approval.read_text())
        report["approved"] = bool(payload.get("approved"))
        report["failed_checks"] = payload.get("failed")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--situations", nargs="+", required=True)
    parser.add_argument("--admission-gib", type=float, default=3.2)
    parser.add_argument("--live-floor-gib", type=float, default=1.0)
    parser.add_argument("--poll", type=float, default=20.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--first-instance", type=int, default=720)
    args = parser.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else dict(
        schema="review.v60.batch.v1", started_utc=utc(), episodes=[])
    for offset, situation in enumerate(args.situations):
        situation = situation.upper()
        base = f"{situation}_v60"
        existing = [e for e in state["episodes"] if e.get("situation") == situation and e.get("approved")]
        if existing:
            state.setdefault("skipped", []).append(dict(situation=situation, reason="already approved",
                                                        case=existing[0]["case"], utc=utc()))
            continue
        attempt = 0
        while attempt < args.max_attempts:
            attempt += 1
            name = base if attempt == 1 else f"{base}_r{attempt}"
            case = REVIEW / name
            if case.exists():
                # preserved evidence; never reuse the directory
                attempt += 1
                continue
            job_for(situation, name, args.first_instance + offset * 10 + attempt)
            log = LOGS / f"{name}.log"
            while True:
                free = free_gib()
                write(HEARTBEAT, dict(utc=utc(), waiting_for=name, situation=situation,
                                      free_ram_gib=round(free, 3), admission_gib=args.admission_gib,
                                      other_flights=my_flights()))
                if free >= args.admission_gib and not my_flights():
                    break
                time.sleep(args.poll)
            entry = dict(situation=situation, case=name, attempt=attempt, started_utc=utc(),
                         admission_free_gib=round(free, 3))
            state["episodes"].append(entry)
            write(STATE, state)
            print(json.dumps({k: entry[k] for k in ("situation", "case", "attempt", "admission_free_gib")}),
                  flush=True)
            with log.open("w") as handle:
                process = subprocess.Popen([sys.executable, "-u", str(RUNNER), "--job", str(JOBS / f"{name}.json")],
                                           cwd=str(ROOT), stdout=handle, stderr=subprocess.STDOUT)
                started = time.time()
                while process.poll() is None:
                    write(HEARTBEAT, dict(utc=utc(), flying=name, situation=situation, pid=process.pid,
                                          elapsed_s=round(time.time() - started, 1),
                                          free_ram_gib=round(free_gib(), 3)))
                    time.sleep(args.poll)
            code = process.returncode
            entry.update(exit_code=code, wall_s=round(time.time() - started, 1), finished_utc=utc())
            error_path = case / "error.json"
            memory_abort = False
            if error_path.exists():
                error = json.loads(error_path.read_text())
                entry["error"] = error.get("error")
                memory_abort = "MemoryError" in str(error.get("error"))
            if code == 0 and (case / "preview_result.json").exists():
                entry["analysis"] = analyse(case, situation)
                entry["approved"] = bool(entry["analysis"].get("approved"))
            entry["memory_abort"] = memory_abort
            write(STATE, state)
            print(json.dumps({k: entry.get(k) for k in ("situation", "case", "exit_code", "approved",
                                                        "memory_abort")}), flush=True)
            if code == 0:
                break
            if not memory_abort:
                # a real behavioural/technical failure is kept, not retried blindly
                break
            time.sleep(args.poll)
    write(HEARTBEAT, dict(utc=utc(), idle=True, free_ram_gib=round(free_gib(), 3)))
    approved = [e["case"] for e in state["episodes"] if e.get("approved")]
    write(STATE, state)
    print(json.dumps(dict(done=True, episodes=len(state["episodes"]), approved=approved), indent=2))


if __name__ == "__main__":
    main()

"""Sequential v60 review queue with explicit RAM admission and a heartbeat.

One flight at a time.  Never reruns an existing case directory, never retries a
failed flight, never kills other applications.  Writes a heartbeat file every
poll so an unattended run can be supervised from the outside.

Run:  python queue_review_v60.py --jobs E01_nominal_v60 E02_distractors_v60 ...
"""
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
CASES = ROOT / "review_v60"
LOGS = CASES / "logs"
JOBS = CASES / "jobs"
HEARTBEAT = CASES / "heartbeat.json"
STATE = CASES / "queue_state.json"
RUNNER = ROOT / "run_windows_review_v60.py"
PYTHON = sys.executable


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    os.replace(tmp, path)


def running_flights():
    found = []
    for process in psutil.process_iter(["pid", "cmdline", "create_time"]):
        try:
            cmd = " ".join(process.info["cmdline"] or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "run_windows_review_v60.py" in cmd and str(process.pid) != str(os.getpid()):
            found.append(process.pid)
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", nargs="+", required=True)
    parser.add_argument("--admission-gib", type=float, default=2.0)
    parser.add_argument("--poll", type=float, default=15.0)
    args = parser.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else dict(
        schema="review.v60.queue.v1", started_utc=utc(), completed=[], skipped=[], failed=[], current=None)
    for name in args.jobs:
        job_path = JOBS / f"{name}.json"
        if not job_path.exists():
            state["skipped"].append(dict(name=name, reason="job file missing", utc=utc()))
            continue
        case = CASES / name
        if (case / "closed.json").exists():
            state["skipped"].append(dict(name=name, reason="closed case already exists", utc=utc()))
            continue
        if case.exists():
            state["skipped"].append(dict(name=name, reason="existing incomplete case preserved; not rerun",
                                         utc=utc()))
            continue
        while True:
            free = psutil.virtual_memory().available / 2 ** 30
            others = running_flights()
            write(HEARTBEAT, dict(utc=utc(), waiting_for=name, free_ram_gib=round(free, 3),
                                  other_flights=others, admission_gib=args.admission_gib,
                                  state_path=str(STATE)))
            if free >= args.admission_gib and not others:
                break
            time.sleep(args.poll)
        log_path = LOGS / f"{name}.log"
        state["current"] = dict(name=name, started_utc=utc(), log=str(log_path))
        write(STATE, state)
        print(json.dumps(dict(starting=name, free_ram_gib=round(free, 3), utc=utc())), flush=True)
        with log_path.open("w") as log:
            process = subprocess.Popen([PYTHON, "-u", str(RUNNER), "--job", str(job_path)],
                                       cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT)
            started = time.time()
            while process.poll() is None:
                write(HEARTBEAT, dict(utc=utc(), flying=name, pid=process.pid,
                                      elapsed_s=round(time.time() - started, 1),
                                      free_ram_gib=round(psutil.virtual_memory().available / 2 ** 30, 3),
                                      state_path=str(STATE)))
                time.sleep(args.poll)
        code = process.returncode
        entry = dict(name=name, exit_code=code, utc=utc(), wall_s=round(time.time() - started, 1))
        result_path = case / "preview_result.json"
        if result_path.exists():
            entry["result"] = json.loads(result_path.read_text())
        if (case / "closed.json").exists():
            entry["closed"] = json.loads((case / "closed.json").read_text())
        (state["completed"] if code == 0 else state["failed"]).append(entry)
        state["current"] = None
        write(STATE, state)
        write(HEARTBEAT, dict(utc=utc(), idle=True, free_ram_gib=round(psutil.virtual_memory().available / 2 ** 30, 3),
                              state_path=str(STATE)))
        print(json.dumps(entry, default=str), flush=True)
    write(STATE, state)
    print(json.dumps(dict(done=True, completed=[c["name"] for c in state["completed"]],
                          failed=[c["name"] for c in state["failed"]],
                          skipped=state["skipped"]), indent=2))


if __name__ == "__main__":
    main()

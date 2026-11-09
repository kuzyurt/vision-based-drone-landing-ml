"""Fly the remaining radio-on scenarios back to back, then rebuild the v64 chart.

Each flight is a real Windows MuJoCo + pinned-PX4 run and takes 10-40 minutes.
A failed flight is logged and skipped; it never blocks the next one.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKPOINT = "../approved_curriculum_20261020/trained_policy_recovery/perception_training_v47/best.pt"
JOBS = ["E02_radio_v64", "E07_radio_v64", "E08_radio_v64"]


def main():
    for name in JOBS:
        out = HERE / "review_v61" / name
        if (out / "preview_result.json").exists():
            print(f"{name}: already complete", flush=True)
            continue
        if out.exists():
            shutil.rmtree(out)
        log = HERE / "logs" / f"{name}.log"
        print(f"{name}: starting {time.strftime('%H:%M:%S')}", flush=True)
        started = time.monotonic()
        with log.open("w") as handle:
            code = subprocess.call([sys.executable, "run_windows_review_v61.py",
                                    "--job", f"jobs_radio/{name}.json",
                                    "--gate", "runtime_probe_windows_v60_radio.json",
                                    "--checkpoint", CHECKPOINT, "--radio"],
                                   cwd=HERE, stdout=handle, stderr=subprocess.STDOUT)
        done = (out / "preview_result.json").exists()
        print(f"{name}: exit {code}, complete={done}, {time.monotonic()-started:.0f}s", flush=True)

    subprocess.call([sys.executable, "artifacts/teacher_repair_20261020/benchmark_v63/score_radio_v64.py"],
                    cwd=HERE.parents[1])
    subprocess.call([sys.executable, "artifacts/teacher_repair_20261020/benchmark_v63/make_chart_v64.py"],
                    cwd=HERE.parents[1])
    print("batch finished", flush=True)


if __name__ == "__main__":
    main()

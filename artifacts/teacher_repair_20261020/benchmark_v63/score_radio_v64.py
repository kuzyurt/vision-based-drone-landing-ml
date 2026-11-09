#!/usr/bin/env python3
"""Score radio-on v60 review flights (benchmark v64) from their own recordings.

Only what the recordings contain is reported: physical landing from
preview_result.json, geometric registration from learner_diagnostics, and the
radio link's own counters.  A flight without record/record.json is reported as
"not analysed", never as qualified.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "artifacts/local_curriculum_20261020/review_v61"
OUT = Path(__file__).resolve().parent / "radio_results_v64.json"

FLIGHTS = {
    "E01_radio_v64": dict(scenario="E01 nominal 8 m", distance_m=8.0),
    "E02_radio_v64": dict(scenario="E02 decoy 20 m", distance_m=20.0),
    "E07_radio_v64": dict(scenario="E07 search 28 m", distance_m=28.0),
    "E08_radio_v64": dict(scenario="E08 far 52 m", distance_m=52.0),
}


def load(name):
    d = REVIEW / name
    steps = d / "steps.jsonl"
    if not steps.exists():
        return None
    rows = [json.loads(line) for line in steps.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return None
    result = json.loads((d / "preview_result.json").read_text()) if (d / "preview_result.json").exists() else {}
    receipt = json.loads((d / "source_receipt.json").read_text()) if (d / "source_receipt.json").exists() else {}
    radio = result.get("radio") or receipt.get("radio") or {}
    metric = [r for r in rows if r["output"]["learner_diagnostics"].get("metric_acceptance") == "tracked"]
    first_metric = metric[0]["task_time_s"] if metric else None
    record_path = d / "record/record.json"
    record = json.loads(record_path.read_text()) if record_path.exists() else None
    landed = bool(result.get("strict_physical_target_landing"))
    # A flight counts only if it reached a terminal scoring step and wrote its
    # result.  An abort (RAM guard, crash) is not an attempt in the denominator.
    completed = bool(result) and str(result.get("outcome", "")).startswith(("landed", "water_strike", "collision_failure", "development_diagnostic_stop"))
    row = dict(
        completed=completed,
        id=name, scenario=FLIGHTS[name]["scenario"], distance_m=FLIGHTS[name]["distance_m"],
        basis="v60", radio=True, radio_mode=radio.get("mode"),
        radio_valid_frames=int(result.get("valid_beacon_frames", 0)),
        radio_packets=int(radio.get("packets_sent", 0) or 0),
        outcome=result.get("outcome"), stop_reason=result.get("stop_reason"),
        physical_landing=landed, frames=len(rows),
        duration_s=float(rows[-1]["task_time_s"]),
        metric_tracked=bool(metric), metric_frames=len(metric),
        first_metric_s=first_metric,
        has_record=record is not None,
        record_tier=(record or {}).get("tier"),
        qualified_landing=bool(landed and record and record.get("tier") != "REJECT"),
        lock_t=(record or {}).get("lock_t"),
        target_fraction=(record or {}).get("target_fraction"),
    )
    return row


def main():
    rows = [r for r in (load(name) for name in FLIGHTS) if r is not None]
    payload = dict(schema="benchmark.v64.radio", utc=None, flights=rows,
                   note="radio-on v60 flights; no record means 'not analysed', never qualified")
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    for r in rows:
        print(r["id"], "landed" if r["physical_landing"] else r["outcome"],
              f"{r['radio_valid_frames']}/{r['frames']} valid beacon frames",
              f"metric {r['metric_frames']}")
    print(f"wrote {OUT.name} ({len(rows)} flights)")


if __name__ == "__main__":
    sys.exit(main())

"""Audit the benchmark's claims against the files that produced them.

This is not a new benchmark.  It answers one question: *is what the existing
reports say actually what the recordings and receipts contain?*  Every check
below reads a source file and recomputes the quantity, or asserts a structural
fact that makes a quoted number mean what it is said to mean.

Status vocabulary (deliberately not pass/fail):

  verified    the claim is true and the number is reproduced from the source
  refuted     the claim is false
  mislabeled  the data is real but the label says something it does not measure
  vacuous     the check is true because the situation never occurs
  stale       the document no longer matches the file it describes

Usage
    python audit_v63.py [--json audit_v63.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[1]                      # artifacts/
REPO = ART.parent
LOCAL = ART / "local_curriculum_20261020"
V62 = ART / "teacher_repair_20261020" / "benchmark_v62"

CHECKS = []


def check(cid, claim, status, detail):
    CHECKS.append(dict(id=cid, claim=claim, status=status, detail=detail))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flight_dirs():
    out = []
    for sub in ("review_v60", "review_v61"):
        for d in sorted((LOCAL / sub).iterdir()):
            if d.is_dir() and (d / "steps.jsonl").exists():
                out.append(d)
    return out


def receipt_dirs():
    out = []
    for sub in ("review_v60", "review_v61"):
        for d in sorted((LOCAL / sub).iterdir()):
            if d.is_dir() and (d / "source_receipt.json").exists():
                out.append(d)
    return out


def steps(d):
    return [json.loads(line) for line in (d / "steps.jsonl").open(encoding="utf-8")]


def receipt(d):
    return read_json(d / "source_receipt.json")


# --------------------------------------------------------------- benchmark v62
def audit_v62_report():
    results = read_json(V62 / "results.json")
    md = (V62 / "RESULTS_V62.md").read_text(encoding="utf-8")
    rows = results["summary"]["rows"]
    decided = results["summary"]["decided_rows"]
    quoted = re.search(r"rows: (\d+), decided: (\d+)", md)
    check("v62.report_matches_results",
          "RESULTS_V62.md quotes the same row and decided counts as results.json",
          "verified" if quoted and (int(quoted.group(1)), int(quoted.group(2))) == (rows, decided)
          else "stale",
          dict(results_rows=rows, results_decided=decided,
               markdown=None if not quoted else [int(quoted.group(1)), int(quoted.group(2))]))
    check("v62.verdicts_recomputed",
          "the verdict tally in results.json equals the tally over its own rows",
          "verified" if _tally(results["rows"]) == results["summary"]["verdicts"] else "refuted",
          dict(recomputed=_tally(results["rows"]), quoted=results["summary"]["verdicts"]))


def _tally(rows):
    out = {}
    for row in rows:
        out[row["verdict"]] = out.get(row["verdict"], 0) + 1
    return out


def audit_v62_decision():
    results = read_json(V62 / "results.json")
    decision = {r["id"]: r for r in results["rows"] if r["tier"] == "decision"}

    d05 = decision["d05_scale_ambiguity_20m"]
    conf = {arm: d05["arms"][arm]["measured"]["confirmed_set"] for arm in ("baseline", "repaired")}
    check("v62.d05_fails_on_the_decoy",
          "the E02 scale case confirms the decoy (track 9), not the target (track 7)",
          "verified" if all(v == [9] for v in conf.values()) else "refuted", conf)

    # The criterion named "never_confirms_the_decoy" is implemented as
    # `confirmed_set == [7]`, i.e. "the only confirmed track is the true target".
    # That is not the same proposition as its name.
    source = (V62 / "cases_v62.py").read_text(encoding="utf-8")
    name_ok = "never_confirms_the_decoy=m[\"confirmed_set\"] == [7]" in source
    check("v62.d05_criterion_names",
          "d05's criteria test what their names say",
          "mislabeled" if name_ok else "verified",
          dict(note="never_confirms_the_decoy is implemented as 'confirmed_set == [7]'; "
                    "no_confirmation_before_target_visible is implemented as "
                    "'confirmation_track == 7' and never checks the confirmation time"))

    vacuous = [cid for cid, row in decision.items()
               for arm in ("baseline", "repaired")
               if row["arms"][arm]["measured"].get("descent_frames_off_target") == 0]
    descents = sum(1 for cid, row in decision.items()
                   for arm in ("baseline", "repaired")
                   if row["arms"][arm]["measured"].get("descent_frames_off_target", 0) > 0)
    check("v62.descent_invariant",
          "the 'no descent without a confirmed selection' invariant is exercised by the case set",
          "vacuous" if descents == 0 else "verified",
          dict(descent_frames_off_target_rows=descents, zero_rows=len(vacuous)))

    # cases_v62.state() passes yaw_rate into own_vertical_speed_m_s.  All cases
    # currently use the default 0, so the measured decisions are unaffected - but
    # the harness field is still wrong.
    bug = "own_vertical_speed_m_s=yaw_rate" in source
    check("v62.decision_harness_vertical_speed",
          "the decision harness feeds vertical speed, not yaw rate, into PublicState",
          "mislabeled" if bug else "verified",
          dict(note="state() sets own_vertical_speed_m_s=yaw_rate; yaw_rate defaults to 0 in "
                    "every current case, so the published rows are unchanged"))


def audit_v62_basis():
    results = read_json(V62 / "results.json")
    basis = results.get("basis") or {}
    sources = LOCAL / "sources/target_learning"
    current = dict(protocol_sha256=sha(sources / "protocol_priority_v60.py"),
                   adapter_sha256=sha(sources / "expert_adapter_v60.py"),
                   public_state_sha256=sha(sources / "protocol.py"),
                   disarm_policy_sha256=sha(LOCAL / "disarm_policy.py"),
                   arms_module_sha256=sha(V62 / "arms_v62.py"))
    wrong = {k: [basis.get(k), v] for k, v in current.items() if basis.get(k) != v}
    check("v62.basis_hashes_match_disk",
          "the hashes in results.json are the files the benchmark claims to have run",
          "verified" if not wrong and basis.get("same_process") is True else "stale",
          dict(mismatched=wrong, same_process=basis.get("same_process")))


def audit_weight_ladder():
    ladder = read_json(V62 / "weight_ladder.json")
    total = sum(e["crops"] for e in ladder["episodes"].values())
    check("v62.ladder_crop_count",
          "the ladder uses 1294 crops from three recordings",
          "verified" if total == 1294 and len(ladder["episodes"]) == 3 else "refuted",
          dict(total=total, episodes={k: e["crops"] for k, e in ladder["episodes"].items()}))
    check("v62.ladder_three_checkpoints",
          "three checkpoints exist and each ran on the identical crop set",
          "verified" if len(ladder["checkpoints"]) == 3 and
          all({e["per_class"]["_aggregate"]["crops"] for e in cp["episodes"].values()}
              == {e["crops"] for e in ladder["episodes"].values()}
              for cp in ladder["checkpoints"].values()) else "refuted",
          sorted(ladder["checkpoints"]))
    e08 = ladder["episodes"]["e08_approach_25_40s"]
    check("v62.ladder_e08_blind",
          "the E08 25-40 s window cannot judge the verifier (all classes below 0.05 at 0.85)",
          "verified" if ladder["episodes_informative"]["e08_approach_25_40s"] is False else "refuted",
          dict(classes=e08["class_counts"], informative=ladder["episodes_informative"]))
    # The protocol classifies TARGET at support >= 0.5 and confirms on a 0.8 s
    # peak with three votes; the ladder gates every crop at support >= 0.80.
    proto = (LOCAL / "sources/target_learning/protocol_priority_v60.py").read_text(encoding="utf-8")
    ladder_src = (V62 / "run_weight_ladder_v62.py").read_text(encoding="utf-8")
    blind_zero = [r["weights"] for r in ladder["rows"]
                  if not r["debris_informative"] and r["debris_confirm"] == 0.0]
    check("v62.ladder_blind_debris_value",
          "a blind E08 criterion is stored as a measured 0.0 false-confirmation rate",
          "mislabeled" if blind_zero else "verified",
          dict(weights=blind_zero,
               note="the markdown says 'blind', but the JSON row carries debris_confirm=0.0; "
                    "a reader of the JSON can mistake it for a measured refusal"))

    check("v62.ladder_gate_equivalence",
          "the ladder's per-crop gate is the protocol's decision gate",
          "mislabeled" if "SUPPORT = 0.80" in ladder_src and "identity_support >= 0.5" in proto
          else "verified",
          dict(ladder_support=0.80, protocol_target_support=0.5,
               note="the protocol's evidence_peak is a maximum over a 0.8 s window and "
                    "confirmation needs 3 votes; a per-crop fraction is a lower bound on "
                    "the probability that the track reaches the gate"))


def audit_flights():
    dirs = receipt_dirs()
    receipts = [receipt(d) for d in dirs]
    distinct = {k: len({r.get(k) for r in receipts})
                for k in ("adapter_sha256", "protocol_sha256", "harness_sha256",
                          "mission_safety_sha256", "recognizer_sha256")}
    check("v62.flight_version_diversity",
          "22 recordings span 3 adapters, 5 protocols and 10 harnesses",
          "verified" if len(dirs) == 22 and distinct["adapter_sha256"] == 3
          and distinct["protocol_sha256"] == 5 and distinct["harness_sha256"] == 10
          else "refuted", dict(recordings=len(dirs), distinct=distinct))

    current = dict(
        protocol=sha(LOCAL / "sources/target_learning/protocol_priority_v60.py"),
        adapter=sha(LOCAL / "sources/target_learning/expert_adapter_v60.py"),
        public_state=sha(LOCAL / "sources/target_learning/protocol.py"),
        disarm=sha(LOCAL / "disarm_policy.py"),
    )
    matches = [d.name for d in dirs if receipt(d).get("protocol_sha256") == current["protocol"]
               and receipt(d).get("adapter_sha256") == current["adapter"]]
    check("v62.current_tree_flies_once",
          "exactly one recording matches the protocol and adapter on disk",
          "verified" if matches == ["E08_v61c"] else "refuted",
          dict(matching=matches, current={k: v[:12] for k, v in current.items()}))

    e08c = read_json(LOCAL / "review_v61/E08_v61c/record/record.json")
    check("v62.e08c_qualified",
          "the repaired E08 flight is a qualified success",
          "refuted" if e08c["tier"] == "REJECT" else "verified",
          dict(tier=e08c["tier"], landed=e08c["strict_physical_target_landing"],
               failed_hard=e08c["failed_hard"],
               continuity=[c["detail"] for c in e08c["checks"]
                           if c["check"] == "authority.selection_continuity"]))

    v61_flights = [d.name for d in dirs if receipt(d).get("recognizer_sha256", "").startswith("5d7df9eb")]
    check("v62.v61_weights_were_flown",
          "the v61 checkpoint was never flown",
          "refuted" if v61_flights else "verified",
          dict(flights=v61_flights,
               note="E08_v61 and E08_v61b used v61 weights; E08_v61c, the landing, used v47"))

    pairs = {r["id"]: r for r in read_json(V62 / "results.json")["rows"] if r["tier"] == "flight"}
    check("v62.flight_pairs_blocked",
          "both recorded flight pairs are blocked because their bases differ",
          "verified" if all(r["verdict"] == "blocked_uncontrolled_basis" for r in pairs.values())
          else "refuted",
          {k: dict(outside=v["changed_outside_the_repair_scope"],
                   missing=v["missing_on_one_side"]) for k, v in pairs.items()})


def audit_radio():
    dirs = flight_dirs()
    valid = {d.name: sum(1 for r in steps(d) if r["observation"].get("beacon", {}).get("valid"))
             for d in dirs}
    check("v60.radio_present_in_review_flights",
          "the v60 review flights exercise a radio channel",
          "refuted" if all(v == 0 for v in valid.values()) else "verified",
          dict(recordings=len(valid), beacon_valid_frames=valid))

    adapter = (LOCAL / "sources/target_learning/expert_adapter_v60.py").read_text(encoding="utf-8")
    forced = 'o["beacon"] = dict(valid=False' in adapter
    public_state = (LOCAL / "sources/target_learning/protocol.py").read_text(encoding="utf-8")
    no_field = "beacon" not in public_state and "radio" not in public_state
    check("v60.radio_reaches_the_protocol",
          "a valid beacon can reach SearchProtocolV60",
          "refuted" if forced and no_field else "verified",
          dict(adapter_forces_invalid=forced, protocol_has_no_radio_field=no_field,
               line="expert_adapter_v60.py:419"))

    audited = read_json(ART / "tidewater_testing_20261018/verified/audited_results.json")
    radio_rows = [r for r in audited["results"] if r["radio"]]
    visual_rows = [r for r in audited["results"] if not r["radio"]]
    check("r15.radio_exercised",
          "the radio-on R15 rows actually received radio samples",
          "verified" if all(r["radio_valid_frames"] > 0 for r in radio_rows)
          and all(r["radio_valid_frames"] == 0 for r in visual_rows) else "refuted",
          dict(radio_rows=len(radio_rows), visual_rows=len(visual_rows)))

    check("r15.visibility_is_not_finding",
          "visual visibility separates R15 successes from failures",
          "refuted" if all(r["maximum_image_visibility_probability"] >= 0.99
                           for r in audited["results"]) else "verified",
          dict(min_visibility=min(r["maximum_image_visibility_probability"]
                                  for r in audited["results"]),
               landed_metric=[r["metric_frames"] for r in audited["results"] if r["landed"]],
               failed_metric=sorted({r["metric_frames"] for r in audited["results"]
                                     if not r["landed"]})))

    landed = [r for r in audited["results"] if r["landed"]]
    check("r15.landing_count",
          "the October corpus contains 26 flights and 5 physical boat landings",
          "verified" if len(audited["results"]) == 26 and len(landed) == 5 else "refuted",
          dict(flights=len(audited["results"]), landed=len(landed),
               radio_landed=sum(1 for r in landed if r["radio"]),
               visual_landed=sum(1 for r in landed if not r["radio"])))

    # The deployed runtime deliberately does not let radio bypass the controller.
    runtime = (ART / "approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/"
               "package/base_r15/code/landing_training/radio_robust_20261015/runtime.py").read_text(
        encoding="utf-8")
    check("r15.radio_is_not_a_search_bypass",
          "R15 radio drives the search/controller directly",
          "refuted" if "reliable = False" in runtime and "direct_radio_controller_bypass_disabled" in runtime
          else "verified",
          dict(note="radio enters learned pose fusion; the controller is handed an invalid beacon"))


def audit_e03_attribution():
    reasons = {}
    for name in ("E03_v60_forced", "E03_v60_repair", "E03_v60_rest"):
        result = read_json(LOCAL / f"review_v60/{name}/preview_result.json")
        reasons[name] = result.get("disarm_reason")
    check("v60.e03_branch_attribution",
          "the E03 repair landings are attributed to the new rest-on-deck branch",
          "verified" if reasons["E03_v60_forced"] == "rest_on_deck"
          and reasons["E03_v60_repair"] == "px4_landed"
          and reasons["E03_v60_rest"] == "px4_landed" else "refuted",
          dict(disarm_reasons=reasons,
               note="only E03_v60_forced exercised rest_on_deck; the other two landed via "
                    "PX4's own detector"))


def audit_freeze_magnitude():
    rows = steps(LOCAL / "review_v61/E08_v61b")
    window = [r for r in rows if 64.0 <= float(r["task_time_s"]) <= 96.0]
    reorient = [r for r in window if r.get("phase") == "reorient_candidate"]
    yaws = [abs(float(r["output"]["executed_action"][3])) for r in reorient]
    check("v61.e08b_freeze_magnitude",
          "the E08_v61b freeze is a near-zero yaw command (the report rounds it to 0.00 rad/s)",
          "verified" if reorient and max(yaws) < 0.01 else "refuted",
          dict(window_s=[64, 96], frames=len(window), reorient_frames=len(reorient),
               max_abs_yaw_rad_s=round(max(yaws), 6) if yaws else None,
               note="the command is 0.005-0.008 rad/s, not exactly zero; the freeze is real"))


def audit_metric_time_origin():
    audited = read_json(ART / "tidewater_testing_20261018/verified/audited_results.json")
    offenders = [(r["id"], r.get("first_metric_simulation_s"), r.get("flight_seconds"))
                 for r in audited["results"]
                 if r.get("first_metric_simulation_s") is not None
                 and r["flight_seconds"] is not None
                 and r["first_metric_simulation_s"] > r["flight_seconds"]]
    check("r15.metric_time_origin",
          "first_metric_simulation_s is a flight-relative acquisition latency",
          "mislabeled" if offenders else "verified",
          dict(examples=offenders[:4],
               note="it is simulation-absolute and exceeds flight_seconds in several rows; "
                    "no handoff timestamp is present, so no R15 latency is reported"))


def audit_tidewater_prerequisite():
    run = (V62 / "run_benchmark_v62.py").read_text(encoding="utf-8")
    checked = "artifacts / \"tidewater_runtime\"" in run or 'artifacts / "tidewater_runtime"' in run
    actual = ART / "landing_hardening_20261018/r15_final_game_verified/tidewater_runtime"
    check("v62.tidewater_staging_path",
          "the v62 prerequisite check looks for the staged runtime where it actually is",
          "mislabeled" if checked and actual.exists() else "verified",
          dict(actual_path=str(actual), actual_exists=actual.exists(),
               note="the v62 check tests landing_hardening_20261018/tidewater_runtime; the "
                    "runtime is under r15_final_game_verified/tidewater_runtime"))


def audit_flight_time_origins():
    d = LOCAL / "review_v60/E01_nominal_v60c"
    rows = steps(d)
    start = rows[0]["time_s"] - rows[0]["task_time_s"]
    record = read_json(d / "record/record.json")
    touchdown = next(t for k, t in record["physical_events"] if k == "touchdown")
    check("v60.event_time_origin",
          "physical event times are on the same clock as duration_s",
          "mislabeled" if touchdown > record["duration_s"] else "verified",
          dict(duration_s=record["duration_s"], touchdown_absolute_s=touchdown,
               task_start_absolute_s=round(start, 2),
               touchdown_task_s=round(touchdown - start, 2),
               note="record.duration_s is task-relative; physical_events are simulation-absolute"))


def audit_record_evidence():
    checked, missing, bad = 0, [], []
    for d in flight_dirs():
        path = d / "record" / "record.json"
        if not path.exists():
            continue
        record = read_json(path)
        for name, expected in (record.get("evidence") or {}).items():
            candidates = [d / name, d / "analysis_v1" / name]
            found = next((p for p in candidates if p.exists()), None)
            if found is None:
                missing.append((d.name, name))
                continue
            checked += 1
            if sha(found) != expected:
                bad.append((d.name, name))
    check("v60.record_evidence_hashes",
          "every flight record's evidence hash matches the file it names",
          "verified" if not bad and not missing else "refuted",
          dict(checked=checked, mismatched=bad, missing=missing,
               note="lock_t and target_fraction are computed from frames.csv; the hash ties "
                    "the record to that trace"))


def audit_flight_inclusion():
    dirs = flight_dirs()
    terminal, records, handoff, crashed = [], [], [], []
    for d in dirs:
        preview = d / "preview_result.json"
        duration = float(steps(d)[-1]["task_time_s"])
        if duration >= 5.0:
            handoff.append(d.name)
            if not preview.exists():
                crashed.append(d.name)
        if preview.exists():
            terminal.append(d.name)
        if (d / "record" / "record.json").exists():
            records.append(d.name)
    check("v60.flight_denominators",
          "the 22 recordings are 22 completed, analysable flights",
          "refuted" if (len(terminal), len(records)) != (22, 22) else "verified",
          dict(recordings=22, with_steps=len(dirs), reached_handoff=len(handoff),
               terminal=len(terminal), crashed_before_terminal=len(crashed),
               with_record=len(records),
               no_record=sorted(set(d.name for d in dirs) - set(records))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(HERE / "audit_v63.json"))
    args = parser.parse_args()
    audit_v62_report()
    audit_v62_decision()
    audit_v62_basis()
    audit_weight_ladder()
    audit_flights()
    audit_radio()
    audit_record_evidence()
    audit_e03_attribution()
    audit_freeze_magnitude()
    audit_metric_time_origin()
    audit_tidewater_prerequisite()
    audit_flight_time_origins()
    audit_flight_inclusion()
    counts = {}
    for item in CHECKS:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    report = dict(schema="audit.v63", checks=CHECKS, status_counts=counts)
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    width = max(len(c["id"]) for c in CHECKS)
    for c in CHECKS:
        print(f'{c["status"]:<11} {c["id"]:<{width}}  {json.dumps(c["detail"])[:150]}')
    print()
    print(json.dumps(counts, sort_keys=True))
    print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

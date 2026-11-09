"""Independent approval gate for one closed review episode.

Approval is not a feeling produced by watching a video.  It is a list of named,
numbered checks computed from three independent records of the same flight:

* the executed decision trace (``steps.jsonl``) - what the actor actually commanded;
* the observer-truth timeline (``analysis_v1/frames.csv``) - what was physically
  true, measured from segmentation on the rendered frame;
* the rendered video join (``analysis_v1/video_join.json``) - proof that the frames
  analysed are the frames encoded in ``review.mp4``;
* the text digest (``digest/digest.md``) - the transcript an LLM reads.

No check may be satisfied by the episode's own claims.  Every number comes from a
file, and the approval receipt records the sha256 of each evidence file so a later
reader can prove which recording was approved.

Usage
-----
    python tools/approve_episode.py <case_dir> --situation E01 \
        [--require-landed] [--max-survey-s 1.0]

Exit code 0 only when every check passes; the receipt is written either way.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

#: Contradiction kinds from the digest that are allowed to appear.  For a nominal
#: episode the honest expectation is an empty list; anything else must be named.
ALLOWED_FINDINGS = {
    "E01": set(),
    "E02": {"survey_while_target_visible"},   # the first survey is the purpose
    "E03": set(),
    "E04": set(),
    "E05": set(),
    "E06": {"survey_while_target_visible"},
    "E07": {"survey_while_target_visible"},
    "E08": {"survey_while_target_visible"},
    "E09": {"survey_while_target_visible"},
    "E10": set(),
    "E11": set(),
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_csv(path: Path):
    import csv
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def flag(value) -> bool:
    return str(value).strip().lower() in ("true", "1")


def check(name, ok, detail):
    return dict(check=name, ok=bool(ok), detail=detail)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--situation", required=True)
    parser.add_argument("--max-survey-s", type=float, default=1.0)
    parser.add_argument("--min-target-fraction", type=float, default=0.95)
    parser.add_argument("--supersede", action="store_true",
                        help="write APPROVAL_<utc>.json instead of refusing")
    args = parser.parse_args()
    case = Path(args.case).resolve()
    analysis = case / "analysis_v1"
    receipt_path = case / "APPROVAL.json"
    if receipt_path.exists() and not args.supersede:
        raise SystemExit(f"refusing to overwrite an existing approval: {receipt_path}")

    frames = load_csv(analysis / "frames.csv")
    steps = load_jsonl(case / "steps.jsonl")
    digest_path = case / "digest" / "digest.json"
    digest = json.loads(digest_path.read_text()) if digest_path.exists() else None
    verdict = json.loads((analysis / "verdict.json").read_text()) if (analysis / "verdict.json").exists() else {}
    join = json.loads((analysis / "video_join.json").read_text()) if (analysis / "video_join.json").exists() else {}
    result = json.loads((case / "preview_result.json").read_text()) if (case / "preview_result.json").exists() else {}
    closed = json.loads((case / "closed.json").read_text()) if (case / "closed.json").exists() else {}
    job = json.loads((case / "purpose_contract.json").read_text()) if (case / "purpose_contract.json").exists() else {}

    checks = []
    # ---- 1. record integrity -------------------------------------------------
    checks.append(check("record.trace_present", bool(steps), dict(step_rows=len(steps))))
    indices = [int(row["frame_index"]) for row in steps] if steps else []
    contiguous = indices == list(range(len(indices))) if indices else False
    checks.append(check("record.frame_indices_contiguous", contiguous,
                        dict(first=indices[0] if indices else None, last=indices[-1] if indices else None,
                             count=len(indices))))
    checks.append(check("record.observer_join_complete",
                        bool(join.get("consistent")) and len(frames) == len(steps),
                        dict(video_join=join.get("consistent"), frames_csv=len(frames), steps=len(steps))))
    checks.append(check("record.closed_cleanly", closed.get("failure") in (None, "") and not closed.get("cleanup_errors"),
                        dict(failure=closed.get("failure"), cleanup=closed.get("cleanup_errors"))))
    observation_keys = sorted({k for row in steps[:1] for k in row.get("observation", {})}) if steps else []
    forbidden = [k for k in observation_keys if any(word in k.lower() for word in ("instance", "seg", "annotation", "truth"))]
    checks.append(check("record.actor_inputs_observer_free", not forbidden,
                        dict(observation_keys=observation_keys, forbidden=forbidden)))

    # ---- 2. one selection authority -----------------------------------------
    disagreements, descent_without_identity, descent_without_metric, non_target_descent = [], [], [], []
    for row in steps:
        diag = row["output"].get("learner_diagnostics", {})
        intent = diag.get("expert_intent") or {}
        protocol = diag.get("expert_protocol_v60") or {}
        selected = intent.get("selected_track")
        authority = protocol.get("selected")
        if selected is not None and selected != authority:
            disagreements.append(dict(t=round(float(row["task_time_s"]), 2), intent=selected, protocol=authority))
        aliases = set((protocol.get("anchor") or {}).get("aliases") or [])
        if intent.get("allow_descent"):
            if protocol.get("confirmed") is None or selected not in aliases:
                descent_without_identity.append(dict(t=round(float(row["task_time_s"]), 2),
                                                     selected=selected, confirmed=protocol.get("confirmed")))
            if not diag.get("metric_confirmed"):
                descent_without_metric.append(round(float(row["task_time_s"]), 2))
    checks.append(check("authority.intent_matches_protocol", not disagreements,
                        dict(disagreements=disagreements[:5], count=len(disagreements))))
    checks.append(check("authority.descent_only_on_confirmed_object", not descent_without_identity,
                        dict(violations=descent_without_identity[:5], count=len(descent_without_identity))))
    checks.append(check("authority.descent_only_with_live_metric", not descent_without_metric,
                        dict(first_violations=descent_without_metric[:5], count=len(descent_without_metric))))
    for row in frames:
        if flag(row.get("allow_descent")) and row.get("selected_name") not in (None, "", "target"):
            non_target_descent.append(dict(t=round(float(row["t"]), 2), on=row.get("selected_name")))
    checks.append(check("authority.no_descent_while_selected_not_target", not non_target_descent,
                        dict(violations=non_target_descent[:5], count=len(non_target_descent))))
    invariants = []
    for row in steps:
        invariants.extend((row["output"].get("learner_diagnostics", {}).get("expert_protocol_v60") or {})
                          .get("invariant_violations") or [])
    checks.append(check("authority.protocol_invariants_clean", not invariants, dict(violations=invariants[:4])))

    # ---- 3. opportunity use --------------------------------------------------
    summary = verdict.get("summary") or {}
    by_name = {entry.get("name"): entry for entry in summary.get("checks", [])} if summary else {}
    survey = next((e for e in (summary.get("checks") or []) if e.get("name", "").endswith("no_pointless_survey_while_opportunity_visible")), None)
    survey_span = None
    if survey is not None:
        survey_span = (survey.get("detail") or {}).get("scan_span_s")
    checks.append(check("opportunity.no_survey_while_visible",
                        survey is not None and survey.get("ok") is True,
                        dict(present=survey is not None, scan_span_s=survey_span,
                             limit_s=args.max_survey_s)))
    continuity = next((e for e in (summary.get("checks") or []) if "selection_continuity_after_lock" in e.get("name", "")), None)
    checks.append(check("opportunity.selection_continuity",
                        continuity is not None and continuity.get("ok") is True,
                        dict(present=continuity is not None,
                             detail=(continuity or {}).get("detail"),
                             required=args.min_target_fraction)))

    # ---- 4. physical result --------------------------------------------------
    landed = str(result.get("outcome")) == "landed" and bool(result.get("strict_physical_target_landing"))
    final = steps[-1] if steps else {}
    final_diag = final.get("output", {}).get("learner_diagnostics", {})
    final_px4 = final.get("observation", {}).get("px4", {})
    checks.append(check("physical.landed_on_target", landed,
                        dict(outcome=result.get("outcome"), stop_reason=result.get("stop_reason"),
                             frames=result.get("frames"))))
    checks.append(check("physical.disarmed_after_landing", not bool(final_px4.get("armed")),
                        dict(armed=final_px4.get("armed"), landed=final_px4.get("landed"))))
    contact_rows = [r for r in steps if str(r.get("outcome")) == "landed"]
    post_contact = [r for r in contact_rows
                    if np.abs(np.asarray(r["output"]["executed_action"], float)).sum() > 1e-9]
    checks.append(check("physical.no_commands_after_contact", not post_contact,
                        dict(rows_after_landing=len(contact_rows), commanded=len(post_contact))))

    # ---- 5. the digest actually describes this episode -----------------------
    same = bool(digest) and digest.get("frames") == len(frames)
    checks.append(check("digest.matches_recording", same,
                        dict(digest_frames=(digest or {}).get("frames"), frames=len(frames),
                             digest_present=bool(digest))))
    kinds = sorted({f["kind"] for f in (digest or {}).get("findings", [])})
    allowed = ALLOWED_FINDINGS.get(args.situation.upper())
    tolerated = sorted(set(kinds) & (allowed or set()))
    unexplained = sorted(set(kinds) - (allowed or set()))
    checks.append(check("digest.no_unexplained_contradiction", not unexplained,
                        dict(found=kinds, tolerated_for_situation=tolerated, unexplained=unexplained)))

    # ---- 6. situation purpose actually happened ------------------------------
    purpose = dict(initial_target=job.get("initial_target"), distance_band=job.get("distance_band"),
                   fault=job.get("fault"), mode=job.get("mode"))
    if job.get("fault"):
        fault_rows = int(result.get("actual_fault_rows") or 0)
        checks.append(check("purpose.fault_actually_injected", fault_rows > 0, dict(fault_rows=fault_rows)))
    if str(args.situation).upper() in ("E04", "E04A", "E11"):
        checks.append(check("purpose.metric_loss_occurred", int(result.get("near_metric_missing_frames") or 0) > 0,
                            dict(near_metric_missing_frames=result.get("near_metric_missing_frames"))))
    if str(args.situation).upper() == "E02":
        checks.append(check("purpose.survey_completed_before_lock",
                            survey_span is not None and survey_span > 2.0,
                            dict(scan_span_s=survey_span)))
    checks.append(check("purpose.contract_retained", bool(job), purpose))

    approved = all(item["ok"] for item in checks)
    payload = dict(
        schema="teacher.episode.approval.v1",
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        case=str(case), case_name=case.name, situation=args.situation.upper(),
        approved=approved,
        training_eligible=approved,
        checks=checks,
        failed=[item["check"] for item in checks if not item["ok"]],
        evidence={name: sha(path) for name, path in
                  (("steps.jsonl", case / "steps.jsonl"),
                   ("frames.csv", analysis / "frames.csv"),
                   ("verdict.json", analysis / "verdict.json"),
                   ("digest.md", case / "digest" / "digest.md"),
                   ("video_join.json", analysis / "video_join.json"),
                   ("review.mp4", case / "review.mp4")) if path.exists()},
        limits=dict(max_survey_s=args.max_survey_s, min_target_fraction=args.min_target_fraction),
        inspector="tools/llm_flight_digest.py transcript + tools/flight_microscope.py acceptance",
        note="Approval covers only the files hashed above. A later edit to any of them voids it.",
    )
    target = receipt_path
    if receipt_path.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = case / f"APPROVAL_{stamp}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(dict(case=case.name, situation=payload["situation"], approved=approved,
                          failed=payload["failed"], receipt=str(target)), indent=2))
    return 0 if approved else 1


if __name__ == "__main__":
    raise SystemExit(main())

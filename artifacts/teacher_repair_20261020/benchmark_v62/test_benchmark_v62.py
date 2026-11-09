"""Self-test: does benchmark v62 actually discriminate, and can it fail?

A benchmark is only worth its rows if four things hold, and this file asserts
each of them on the code that produces the report:

1. The two arms are the same code except for the toggled rule (same basis
   hashes), so a difference cannot come from anywhere else.
2. The baseline arm reproduces the historical failures - the freeze, the crash,
   the missed deck dwell.  If it did not, the "repair" would be measuring
   nothing.
3. The repaired arm fixes exactly those, and leaves the older situations alone.
4. The benchmark can fail: E02's scale ambiguity must still fail in *both* arms.

Run:  python test_benchmark_v62.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import arms_v62  # noqa: E402
import cases_v62  # noqa: E402
import run_benchmark_v62 as bench  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}")
        FAILS.append((name, detail))


def by_id(rows):
    return {row["id"]: row for row in rows}


def main() -> int:
    basis = arms_v62.basis()
    check("basis records real hashes", all(len(v) == 64 for k, v in basis.items()
                                           if k.endswith("sha256")), basis)
    check("basis says both arms run in one process", basis["same_process"] is True)
    check("only the repaired rules are toggled", "reorient" in basis["only_rule_toggled"])

    decision = by_id(bench.decision_tier())

    # 2. The baseline reproduces the historical failures.
    d06 = decision["d06_reorient_freeze"]["arms"]["baseline"]["measured"]
    check("baseline freezes on a stale remembered candidate", d06["frozen_seconds"] >= 30.0,
          f"frozen {d06['frozen_seconds']} s")
    check("baseline never records a timeout", not d06["events"].get("reorient_timeout"))
    d07 = decision["d07_retired_candidate_timestamp"]["arms"]["baseline"]
    check("baseline crashes on a bare rejection timestamp",
          d07["measured"]["exception"] is not None
          and "TypeError" in d07["measured"]["exception"], d07["measured"]["exception"])
    d08 = decision["d08_rest_on_deck_disarm"]["arms"]["baseline"]["measured"]
    check("baseline misses the deck dwell", d08["pressed"][0] is False)

    # 3. The repaired arm fixes them.
    d06r = decision["d06_reorient_freeze"]["arms"]["repaired"]
    check("repaired bounds the wait", d06r["measured"]["frozen_seconds"] <= 3.5,
          f"frozen {d06r['measured']['frozen_seconds']} s")
    check("repaired records the timeout", d06r["measured"]["events"].get("reorient_timeout", 0) >= 1)
    check("repaired resumes the survey", d06r["measured"]["scan_frames_after_3_5s_with_yaw"] > 0)
    check("repaired keeps the object", 5 not in d06r["measured"]["rejected"])
    d07r = decision["d07_retired_candidate_timestamp"]["arms"]["repaired"]
    check("repaired survives the bare timestamp", d07r["measured"]["exception"] is None,
          d07r["measured"]["exception"])
    d08r = decision["d08_rest_on_deck_disarm"]["arms"]["repaired"]["measured"]
    check("repaired disarms on the deck dwell", d08r["pressed"] == [True, "rest_on_deck"], d08r["pressed"])
    check("repaired still refuses a hovering body", d08r["hovering"][0] is False)

    # 3b. Older situations are untouched.
    for case_id in ("d01_visible_opportunity", "d02_competing_buoy",
                    "d03_target_appears_mid_survey", "d04_evidence_growth_at_range"):
        row = decision[case_id]
        check(f"{case_id}: no regression", row["verdict"] == "pass_both",
              {arm: row["arms"][arm]["criteria"] for arm in arms_v62.ARMS})

    # 4. The benchmark can fail.
    d05 = decision["d05_scale_ambiguity_20m"]
    check("E02 scale ambiguity still fails in both arms", d05["verdict"] == "fail_both",
          {arm: d05["arms"][arm]["criteria"] for arm in arms_v62.ARMS})

    # The arms differ where the repairs say they should, and nowhere else.
    differing = [row["id"] for row in decision.values()
                 if row["verdict"] in ("repaired_only", "regression")]
    check("at least three rows separate the arms", len(differing) >= 3, differing)
    check("no row is a regression", not any(row["verdict"] == "regression"
                                            for row in decision.values()))

    # Every row has criteria, every criterion is a bool, and no descent bypasses
    # the confirmed selection.
    nothing = [case_id for case_id, row in decision.items()
               if not row["arms"]["repaired"]["criteria"]]
    check("every decision row declares criteria", not nothing, nothing)
    non_bool = [case_id for case_id, row in decision.items()
                for arm in arms_v62.ARMS
                for name, value in row["arms"][arm]["criteria"].items()
                if not isinstance(value, bool)]
    check("every criterion is a boolean", not non_bool, non_bool)
    bypass = [case_id for case_id, row in decision.items()
              for arm in arms_v62.ARMS
              if row["arms"][arm].get("invariant") is False]
    check("no descent without a confirmed selection", not bypass, bypass)

    # Mission tier: the repair must not have removed a safety stop.
    mission = by_id(bench.mission_tier())
    check("E08 replay no longer ends on the reserve",
          mission["m01_e08_long_approach"]["verdict"] == "pass",
          mission["m01_e08_long_approach"].get("criteria"))
    check("E02 hover still ends the mission",
          mission["m02_e02_hovering_decoy"]["verdict"] == "pass",
          mission["m02_e02_hovering_decoy"].get("criteria"))

    # Weight ladder: the claim that blocks promotion must be the measured one.
    weights = {row["weights"]: row["measured"] for row in bench.perception_tier()
               if row.get("weights")}
    check("three weight sets form the ladder", len(weights) == 3, sorted(weights))
    check("v61 confirms more decoys than v47",
          weights["v61"]["decoy_confirm"] > weights["v47"]["decoy_confirm"],
          {k: v["decoy_confirm"] for k, v in weights.items()})
    check("no weight set earns a promotion verdict",
          all(row["verdict"] == "promotion_refused" for row in bench.perception_tier()),
          [row["verdict"] for row in bench.perception_tier()])

    # Tidewater: declared, and never reported as a pass it did not earn.
    tidewater = bench.tidewater_tier()
    check("three Tidewater situations are declared", len(tidewater) == 3)
    check("Tidewater rows are blocked, not passed",
          all(row["verdict"].startswith("blocked") for row in tidewater),
          [row["verdict"] for row in tidewater])
    check("the blocker names the missing bridge",
          all("bridge" in row["blocked_reason"] for row in tidewater))

    print()
    if FAILS:
        print(f"{len(FAILS)} of the benchmark's own properties failed.")
        return 1
    print("benchmark v62 self-test: all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

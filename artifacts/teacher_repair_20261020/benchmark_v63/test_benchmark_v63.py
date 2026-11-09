"""Self-test for benchmark v63.

A benchmark is only worth its rows if it can fail in the right places.  This
file asserts the properties that would make the four-cell report meaningless if
they broke:

  1. the four cells exist and each basis is reported on its own rows;
  2. the radio-on v60 cells are blocked, and the blocker is the adapter line
     that actually removes the input - not a missing file;
  3. physical and qualified landings are different numbers (E08_v61c lands but
     is REJECT on selection continuity);
  4. "found" is not visual visibility (every R15 flight sees the boat);
  5. a transient lock is not a find (E02 locks the truth target, then loses it);
  6. the R15 aggregate is not read as a radio effect: the low-start stratum is
     0/9 in both conditions, so the visible-start 3/4 vs 2/4 is the whole story;
  7. touchdown times are on the task clock, not the simulation clock.

Run:  python test_benchmark_v63.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_benchmark_v63 as bench  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}")
        FAILS.append((name, detail))


def main() -> int:
    cells, v60, attempts, r15, r15_meta, blocked = bench.build()
    by_id = {c["id"]: c for c in cells}

    check("four cells are declared", set(by_id) == {"L-R", "L-0", "F-R", "F-0"}, sorted(by_id))
    check("every cell has both bases", all(set(c["bases"]) == {"v60", "r15"} for c in cells))

    # 1. No pooling: every measured row belongs to the basis it is filed under.
    mixed = [(c["id"], name) for c in cells for name, e in c["bases"].items()
             if e["status"] == "measured"
             and any(r["basis"] != name for r in e["rows"])]
    check("no cell pools bases", not mixed, mixed)

    # 2. The radio-on v60 cells are blocked by the adapter, not by absence of data.
    for cell_id in ("L-R", "F-R"):
        entry = by_id[cell_id]["bases"]["v60"]
        check(f"{cell_id}: v60 radio-on is blocked", entry["status"] == "blocked")
        check(f"{cell_id}: blocker names the adapter line",
              "expert_adapter_v60.py:419" in entry["reason"], entry["reason"][:80])
    check("Tidewater v60 bridge is declared blocked",
          any("Tidewater" in b["cell"] and "bridge" in b["reason"] for b in blocked))

    # 3/4. Landing counts, recomputed from the rows.
    lr = by_id["L-R"]["bases"]["r15"]
    l0 = by_id["L-0"]["bases"]["r15"]
    check("R15 radio-on landings are 3/13",
          sum(1 for r in lr["rows"] if r["physical_landing"]) == 3 and len(lr["rows"]) == 13)
    check("R15 radio-off landings are 2/13",
          sum(1 for r in l0["rows"] if r["physical_landing"]) == 2 and len(l0["rows"]) == 13)

    v60_landing = by_id["L-0"]["bases"]["v60"]
    check("v60 radio-off physical landings are 9/16 incl. two harness crashes",
          sum(1 for r in v60_landing["rows"] if r["physical_landing"]) == 9
          and len(v60_landing["rows"]) == 16
          and sum(1 for r in v60_landing["rows"] if r["crashed"]) == 2)
    check("v60 policy-attributable landings are 9/14",
          v60_landing["summary"]["policy_physical"]["k"] == 9
          and v60_landing["summary"]["policy_physical"]["n"] == 14)
    v60_strata = v60_landing["summary"]["strata"]
    check("v60 9/16 is 7/10 near, 0/1 mid, 2/5 far",
          (v60_strata["near_<=10m"]["landed"]["k"], v60_strata["near_<=10m"]["n"]) == (7, 10)
          and (v60_strata["mid_11_24m"]["landed"]["k"], v60_strata["mid_11_24m"]["n"]) == (0, 1)
          and (v60_strata["far_>=25m"]["landed"]["k"], v60_strata["far_>=25m"]["n"]) == (2, 5),
          {k: (v["landed"]["k"], v["n"]) for k, v in v60_strata.items()})
    analysed = [r for r in v60_landing["rows"] if r["qualified_landing"] is not None]
    check("v60 radio-off qualified landings are 7/12",
          sum(1 for r in analysed if r["qualified_landing"]) == 7 and len(analysed) == 12)

    e08c = next(r for r in v60_landing["rows"] if r["id"] == "E08_v61c")
    check("E08_v61c lands physically", e08c["physical_landing"] is True)
    check("E08_v61c is not qualified", e08c["qualified_landing"] is False)
    check("E08_v61c names the continuity failure",
          any("selection_continuity" in f for f in e08c["failed_hard"]), e08c["failed_hard"])

    # 4. Visibility does not separate outcomes in R15.
    check("every R15 flight sees the boat",
          all(r["max_visibility"] >= 0.99 for r in r15), 
          sorted({r["max_visibility"] for r in r15})[:4])
    failed_but_visible = [r for r in r15 if not r["found_metric"] and r["max_visibility"] >= 0.99]
    check("failed R15 flights are still fully visible",
          len(failed_but_visible) >= 10, len(failed_but_visible))

    # 5. A transient truth lock is not a find.
    e02 = next(r for r in v60 if r["id"] == "E02_v60")
    check("E02 locked the truth target transiently",
          e02["lock_t"] is not None and e02["target_fraction"] < 0.05,
          [e02["lock_t"], e02["target_fraction"]])
    check("E02 is not counted as found", e02["found_decision"] is False)

    # 5b. Radio availability is not radio reliance.
    radio_rows = [r for r in r15 if r["radio"]]
    active = {r["id"] for r in radio_rows if r["radio_position_fusion_weight"] > 0.01}
    landed_radio = {r["id"] for r in radio_rows if r["physical_landing"]}
    check("only 3 radio flights used position fusion, and they are the 3 landings",
          active == landed_radio and len(active) == 3, [sorted(active), sorted(landed_radio)])

    # 6. The R15 result is stratified, and the hard-start stratum shows no radio benefit.
    strata_r = by_id["L-R"]["bases"]["r15"]["summary"]["strata"]
    strata_0 = by_id["L-0"]["bases"]["r15"]["summary"]["strata"]
    check("R15 radio-on visible starts land 3/4",
          strata_r["visible_start"]["landed"]["k"] == 3
          and strata_r["visible_start"]["landed"]["n"] == 4)
    check("R15 radio-off visible starts land 2/4",
          strata_0["visible_start"]["landed"]["k"] == 2
          and strata_0["visible_start"]["landed"]["n"] == 4)
    check("R15 hard starts land 0/9 in both radio conditions",
          strata_r["hard_start"]["landed"]["k"] == 0
          and strata_0["hard_start"]["landed"]["k"] == 0
          and strata_r["hard_start"]["landed"]["n"] == 9
          and strata_0["hard_start"]["landed"]["n"] == 9)

    # 7. Event times are task-relative and precede the end of the flight.
    wrong_clock = [(r["id"], r["touchdown_s"], r["duration_s"])
                   for r in v60 if r["physical_landing"] and r["touchdown_s"] is not None
                   and r["touchdown_s"] > r["duration_s"] + 0.01]
    check("v60 touchdown is on the task clock", not wrong_clock, wrong_clock)

    # Rates are complete and their intervals bracket the estimate.
    bad = []
    for c in cells:
        for name, e in c["bases"].items():
            if e["status"] != "measured":
                continue
            stats = ([e["summary"]["physical"], e["summary"]["qualified"]]
                     if c["outcome"] == "landing"
                     else ([e["summary"]["found"], e["summary"]["sustained"]]
                           if name == "r15"
                           else [e["summary"]["found"], e["summary"]["qualified"],
                                 e["summary"]["metric_tracked"]]))
            for s in stats:
                if not s["wilson"] or not (s["wilson"][0] <= s["p"] <= s["wilson"][1]):
                    bad.append((c["id"], name, s))
    check("every rate has a Wilson interval containing it", not bad, bad)

    check("crashes are rows, not startup aborts",
          all(r in v60_landing["rows"] and r["status"] == "crashed_before_terminal_result"
              for r in v60 if r["id"] in ("E03_v60_ondeck", "E08_v61"))
          and all(a["reason"] == "startup_abort" for a in attempts))

    print()
    if FAILS:
        print(f"{len(FAILS)} of the new benchmark's properties failed.")
        return 1
    print("benchmark v63 self-test: all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

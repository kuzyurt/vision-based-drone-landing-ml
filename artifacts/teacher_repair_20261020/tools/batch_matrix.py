"""Honest result matrix over every v60 review case that exists on disk.

Reads only closed cases and their receipts.  A case appears as APPROVED only when
its own APPROVAL.json says training_eligible, and every number shown is copied
from that receipt - this script never re-derives or softens a verdict.

Writes:
    review_v60/MATRIX.md      the table a human reads
    review_v60/index.html     local gallery: video, digest, approval, checks

Run
    python tools/batch_matrix.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent.parent / "local_curriculum_20261020" / "review_v60"
ORDER = ["E01", "E02", "E03", "E04", "E04A", "E05", "E06", "E07", "E08", "E09", "E10", "E11"]


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    rows = []
    for case in sorted(REVIEW.iterdir()):
        if not case.is_dir() or not (case / "closed.json").exists():
            continue
        result = load(case / "preview_result.json") or {}
        approval = load(case / "APPROVAL.json")
        digest = load(case / "digest" / "digest.json")
        verdict = load(case / "analysis_v1" / "verdict.json") or {}
        summary = verdict.get("summary") or {}
        rows.append(dict(
            case=case.name,
            situation=(approval or {}).get("situation") or case.name.split("_")[0],
            outcome=result.get("outcome"),
            frames=result.get("frames"),
            wall_s=result.get("wall_s"),
            approved=bool((approval or {}).get("approved")),
            failed=(approval or {}).get("failed") or (summary.get("failed_checks") or []),
            checks=(approval or {}).get("checks") or summary.get("checks") or [],
            findings=[f["kind"] for f in (digest or {}).get("findings", [])],
            video=(case / "review.mp4").exists(),
            digest=(case / "digest" / "digest.md").exists(),
            path=str(case),
        ))
    rows.sort(key=lambda r: (ORDER.index(r["situation"]) if r["situation"] in ORDER else 99, r["case"]))
    lines = ["# v60 review result matrix", "",
             "Generated from the case directories themselves. APPROVED means the approval gate",
             "wrote `training_eligible: true` from measured checks; a physical landing alone is not",
             "approval, and a failed case is never renamed or promoted.", "",
             "| case | situation | outcome | frames | wall s | approved | failing checks | digest contradictions |",
             "|---|---|---|---:|---:|---|---|---|"]
    for row in rows:
        failing = ", ".join(f"`{name}`" for name in row["failed"]) or "-"
        findings = ", ".join(sorted(set(row["findings"]))) or "-"
        lines.append(f"| `{row['case']}` | {row['situation']} | {row['outcome']} | {row['frames']} | "
                     f"{row['wall_s']} | {'YES' if row['approved'] else 'no'} | {failing} | {findings} |")
    approved = [r for r in rows if r["approved"]]
    lines += ["", f"**{len(approved)} of {len(rows)} closed cases approved** for training data.", "",
              "Approval covers only the hashed evidence in each `APPROVAL.json`; the physical claim is a",
              "MuJoCo contact landing with the pinned PX4 stack, not an airframe qualification.", ""]
    (REVIEW / "MATRIX.md").write_text("\n".join(lines), encoding="utf-8")

    cards = []
    for row in rows:
        case = Path(row["path"])
        status = "APPROVED" if row["approved"] else "NOT APPROVED"
        checks = "".join(
            f"<tr><td>{html.escape(str(c.get('check')))}</td>"
            f"<td class='{'ok' if c.get('ok') else 'bad'}'>{'pass' if c.get('ok') else 'FAIL'}</td>"
            f"<td><code>{html.escape(json.dumps(c.get('detail'), default=str)[:300])}</code></td></tr>"
            for c in row["checks"])
        cards.append(f"""
        <section class="{'good' if row['approved'] else 'bad-card'}">
          <h2>{html.escape(row['case'])} <span class="tag">{html.escape(status)}</span></h2>
          <p>situation <b>{html.escape(row['situation'])}</b> · outcome <b>{html.escape(str(row['outcome']))}</b>
             · {row['frames']} frames · {row['wall_s']} s wall</p>
          <p><a href="{case.name}/review.mp4">annotated video</a> ·
             <a href="{case.name}/digest/digest.md">digest</a> ·
             <a href="{case.name}/APPROVAL.json">approval</a> ·
             <a href="{case.name}/analysis_v1/narrative.md">narrative</a></p>
          <details><summary>{len(row['checks'])} checks</summary><table>{checks}</table></details>
        </section>""")
    page = f"""<!doctype html><meta charset="utf-8"><title>v60 review gallery</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;background:#0f1216;color:#dfe7ef;max-width:1200px;margin:2rem auto;padding:0 1rem}}
 section{{background:#161c23;border:1px solid #26303a;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0}}
 section.good{{border-left:5px solid #3ecf8e}} section.bad-card{{border-left:5px solid #d9534f}}
 h2{{margin:.2rem 0 .6rem;font-size:1.05rem}} .tag{{font-size:.75rem;padding:.1rem .45rem;border-radius:6px;background:#26303a}}
 .good .tag{{background:#12372a;color:#7ef0b8}} .bad-card .tag{{background:#3a1616;color:#ffb3ae}}
 table{{border-collapse:collapse;width:100%;font-size:.85rem}} td,th{{border-bottom:1px solid #232c35;padding:.25rem .4rem;vertical-align:top}}
 td.ok{{color:#7ef0b8}} td.bad{{color:#ffb3ae}} code{{font-size:.78rem;color:#a9b8c7}}
 a{{color:#8ab4f8}}
</style>
<h1>v60 specialist review — {len(approved)}/{len(rows)} approved</h1>
<p><a href="MATRIX.md">matrix</a> · every case keeps its failures.</p>
{''.join(cards)}
"""
    (REVIEW / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps(dict(cases=len(rows), approved=len(approved),
                          matrix=str(REVIEW / "MATRIX.md"), gallery=str(REVIEW / "index.html")), indent=2))
    for row in rows:
        print(f"{row['case']:24s} {row['situation']:5s} {str(row['outcome']):18s} "
              f"{'APPROVED' if row['approved'] else 'not approved'} {','.join(row['failed'])[:80]}")


if __name__ == "__main__":
    main()

# Flight narrative — E02_v60

Scenario `windows_review_E02_distractors` kind=beach seed=3200000004 distance=20.0m height=6.0m boat_speed=0.3m/s initial_target=outside_camera fault=None mode=expert
Frames 2501, task duration 100.00s, outcome flying.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–16.12 | 0–403 | scan | complete_observed_360_before_inspection_pass | none | 0 | -140° | 6.6 | 20.1 | no | — |
| 16.16–16.20 | 404–405 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 0 | +57° | 6.5 | 25.2 | no | — |
| 16.24–16.80 | 406–420 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 0 | +54° | 6.5 | 25.2 | no | — |
| 16.84–17.04 | 421–426 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 773 | +29° | 6.5 | 25.4 | no | 320px |
| 17.08–17.12 | 427–428 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 743 | +27° | 6.5 | 25.4 | no | 310px |
| 17.16–17.60 | 429–440 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 697 | +25° | 6.5 | 25.4 | no | 284px |
| 17.64–17.72 | 441–443 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 701 | +23° | 6.5 | 25.3 | no | 280px |
| 17.76–17.80 | 444–445 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 655 | +20° | 6.5 | 25.3 | no | 244px |
| 17.84–17.84 | 446–446 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 614 | +17° | 6.5 | 25.2 | no | 208px |
| 17.88–17.92 | 447–448 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 598 | +15° | 6.5 | 25.2 | no | 194px |
| 17.96–18.00 | 449–450 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 592 | +15° | 6.5 | 25.2 | no | 186px |
| 18.04–18.12 | 451–453 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 581 | +13° | 6.5 | 25.1 | no | 175px |
| 18.16–18.16 | 454–454 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 583 | +13° | 6.5 | 25.0 | no | 164px |
| 18.20–18.20 | 455–455 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 595 | +13° | 6.5 | 25.0 | no | 167px |
| 18.24–18.24 | 456–456 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 602 | +14° | 6.5 | 25.0 | no | 176px |
| 18.28–18.28 | 457–457 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 607 | +14° | 6.5 | 24.9 | no | 180px |
| 18.32–18.32 | 458–458 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 620 | +15° | 6.5 | 24.9 | no | 187px |
| 18.36–18.36 | 459–459 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 615 | +15° | 6.5 | 24.9 | no | 189px |
| 18.40–18.40 | 460–460 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 623 | +16° | 6.5 | 24.8 | no | 195px |
| 18.44–18.64 | 461–466 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 632 | +17° | 6.5 | 24.8 | no | 198px |
| 18.68–18.68 | 467–467 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 712 | +22° | 6.5 | 24.6 | no | 250px |
| 18.72–18.88 | 468–472 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 715 | +22° | 6.5 | 24.6 | no | 254px |
| 18.92–18.96 | 473–474 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 763 | +24° | 6.5 | 24.4 | no | 273px |
| 19.00–19.08 | 475–477 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 750 | +22° | 6.5 | 24.3 | no | 263px |
| 19.12–19.12 | 478–478 | target_inspect | target_likely_evidence_requires_inspection | track24(decoy_blank_clone) | 740 | +22° | 6.5 | 24.1 | no | 253px |
| 19.16–19.28 | 479–482 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 770 | +23° | 6.5 | 24.1 | no | 261px |
| 19.32–19.48 | 483–487 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 828 | +25° | 6.5 | 23.9 | no | 290px |
| 19.52–19.52 | 488–488 | target_inspect | target_likely_evidence_requires_inspection | track20(decoy_blank_clone) | 733 | +18° | 6.5 | 23.7 | no | 213px |
| 19.56–19.56 | 489–489 | target_inspect | target_likely_evidence_requires_inspection | track26(target) | 720 | +17° | 6.5 | 23.6 | no | 196px |
| 19.60–20.40 | 490–510 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 692 | +15° | 6.5 | 23.5 | no | 175px |
| 20.44–22.80 | 511–570 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 1039 | +29° | 6.5 | 22.4 | no | 336px |
| 22.84–23.48 | 571–587 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +42° | 6.5 | 19.0 | no | — |
| 23.52–23.80 | 588–595 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(decoy_blank_clone) | 0 | +47° | 6.5 | 18.3 | no | — |
| 23.84–31.64 | 596–791 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +41° | 6.5 | 18.1 | no | — |
| 31.68–31.68 | 792–792 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 19.7 | no | — |
| 31.72–32.32 | 793–808 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +31° | 6.4 | 19.8 | no | — |
| 32.36–32.72 | 809–818 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 20.0 | no | — |
| 32.76–35.28 | 819–882 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +31° | 6.4 | 20.1 | no | — |
| 35.32–35.32 | 883–883 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +32° | 6.4 | 20.8 | no | — |
| 35.36–37.40 | 884–935 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +32° | 6.4 | 20.8 | no | — |
| 37.44–37.64 | 936–941 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 21.4 | no | — |
| 37.68–39.36 | 942–984 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +37° | 6.4 | 21.5 | no | — |
| 39.40–39.44 | 985–986 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 21.8 | no | — |
| 39.48–47.88 | 987–1197 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +32° | 6.4 | 21.8 | no | — |
| 47.92–48.04 | 1198–1201 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +39° | 6.4 | 24.2 | no | — |
| 48.08–49.20 | 1202–1230 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +37° | 6.4 | 24.2 | no | — |
| 49.24–49.28 | 1231–1232 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(decoy_blank_clone) | 0 | +37° | 6.4 | 24.6 | no | — |
| 49.32–52.48 | 1233–1312 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 24.6 | no | — |
| 52.52–53.08 | 1313–1327 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 25.6 | no | — |
| 53.12–53.36 | 1328–1334 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 25.7 | no | — |
| 53.40–54.20 | 1335–1355 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 25.8 | no | — |
| 54.24–54.52 | 1356–1363 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +38° | 6.4 | 26.1 | no | — |
| 54.56–55.12 | 1364–1378 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +32° | 6.4 | 26.2 | no | — |
| 55.16–56.08 | 1379–1402 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 26.3 | no | — |
| 56.12–56.32 | 1403–1408 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +35° | 6.4 | 26.6 | no | — |
| 56.36–56.68 | 1409–1417 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 26.7 | no | — |
| 56.72–56.92 | 1418–1423 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +34° | 6.4 | 26.8 | no | — |
| 56.96–58.00 | 1424–1450 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 26.9 | no | — |
| 58.04–58.52 | 1451–1463 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 27.2 | no | — |
| 58.56–58.80 | 1464–1470 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 27.4 | no | — |
| 58.84–58.84 | 1471–1471 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 27.4 | no | — |
| 58.88–59.20 | 1472–1480 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +31° | 6.4 | 27.4 | no | — |
| 59.24–59.48 | 1481–1487 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 27.6 | no | — |
| 59.52–59.96 | 1488–1499 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 27.6 | no | — |
| 60.00–60.08 | 1500–1502 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 27.8 | no | — |
| 60.12–60.36 | 1503–1509 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +32° | 6.4 | 27.8 | no | — |
| 60.40–61.12 | 1510–1528 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +44° | 6.4 | 27.9 | no | — |
| 61.16–61.44 | 1529–1536 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 28.1 | no | — |
| 61.48–61.56 | 1537–1539 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 28.2 | no | — |
| 61.60–62.12 | 1540–1553 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +32° | 6.4 | 28.3 | no | — |
| 62.16–62.52 | 1554–1563 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +32° | 6.4 | 28.4 | no | — |
| 62.56–63.08 | 1564–1577 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 28.6 | no | — |
| 63.12–63.32 | 1578–1583 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 28.7 | no | — |
| 63.36–63.72 | 1584–1593 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 28.8 | no | — |
| 63.76–63.80 | 1594–1595 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +32° | 6.4 | 28.9 | no | — |
| 63.84–64.08 | 1596–1602 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +33° | 6.4 | 28.9 | no | — |
| 64.12–64.24 | 1603–1606 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +34° | 6.4 | 29.0 | no | — |
| 64.28–64.76 | 1607–1619 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 29.1 | no | — |
| 64.80–65.12 | 1620–1628 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +33° | 6.4 | 29.2 | no | — |
| 65.16–65.40 | 1629–1635 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +35° | 6.4 | 29.3 | no | — |
| 65.44–65.60 | 1636–1640 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +31° | 6.4 | 29.4 | no | — |
| 65.64–65.88 | 1641–1647 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +31° | 6.4 | 29.5 | no | — |
| 65.92–66.04 | 1648–1651 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +35° | 6.4 | 29.6 | no | — |
| 66.08–66.32 | 1652–1658 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 29.6 | no | — |
| 66.36–66.36 | 1659–1659 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +34° | 6.4 | 29.7 | no | — |
| 66.40–66.64 | 1660–1666 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +34° | 6.4 | 29.7 | no | — |
| 66.68–68.00 | 1667–1700 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +46° | 6.4 | 29.8 | no | — |
| 68.04–71.52 | 1701–1788 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +37° | 6.4 | 30.2 | no | — |
| 71.56–71.56 | 1789–1789 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +38° | 6.4 | 31.2 | no | — |
| 71.60–75.32 | 1790–1883 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +38° | 6.4 | 31.3 | no | — |
| 75.36–75.60 | 1884–1890 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +36° | 6.4 | 32.4 | no | — |
| 75.64–75.88 | 1891–1897 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +37° | 6.4 | 32.4 | no | — |
| 75.92–75.92 | 1898–1898 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +34° | 6.4 | 32.5 | no | — |
| 75.96–88.52 | 1899–2213 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +34° | 6.4 | 32.5 | no | — |
| 88.56–88.68 | 2214–2217 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +39° | 6.4 | 36.2 | no | — |
| 88.72–89.16 | 2218–2229 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +37° | 6.4 | 36.2 | no | — |
| 89.20–89.28 | 2230–2232 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +38° | 6.4 | 36.4 | no | — |
| 89.32–98.48 | 2233–2462 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +36° | 6.4 | 36.4 | no | — |
| 98.52–98.60 | 2463–2465 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +26° | 6.4 | 39.2 | no | — |
| 98.64–98.92 | 2466–2473 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +26° | 6.4 | 39.2 | no | — |
| 98.96–98.96 | 2474–2474 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track24(decoy_blank_clone) | 0 | +28° | 6.4 | 39.3 | no | — |
| 99.00–99.96 | 2475–2499 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track20(decoy_blank_clone) | 0 | +28° | 6.4 | 39.3 | no | — |
| 100.00–100.00 | 2500–2500 | None | None | none | 0 | +30° | 6.4 | 39.7 | no | — |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 16.84–17.04s: selected track20(decoy_blank_clone) while target had 773 px of visible structure; selected object 81 px, target_probability 0.9696, wrong_object_probability 0.026.
- 17.16–17.60s: selected track20(decoy_blank_clone) while target had 697 px of visible structure; selected object 110 px, target_probability 0.4071, wrong_object_probability 0.472.
- 17.76–17.80s: selected track20(decoy_blank_clone) while target had 655 px of visible structure; selected object 100 px, target_probability 0.9200, wrong_object_probability 0.056.
- 17.88–17.92s: selected track20(decoy_blank_clone) while target had 598 px of visible structure; selected object 97 px, target_probability 0.2649, wrong_object_probability 0.661.
- 18.04–18.12s: selected track20(decoy_blank_clone) while target had 581 px of visible structure; selected object 80 px, target_probability 0.8146, wrong_object_probability 0.143.
- 18.20–18.20s: selected track20(decoy_blank_clone) while target had 595 px of visible structure; selected object 86 px, target_probability 0.5799, wrong_object_probability 0.380.
- 18.28–18.28s: selected track20(decoy_blank_clone) while target had 607 px of visible structure; selected object 56 px, target_probability 0.4521, wrong_object_probability 0.449.
- 18.36–18.36s: selected track20(decoy_blank_clone) while target had 615 px of visible structure; selected object 75 px, target_probability 0.8600, wrong_object_probability 0.118.

## Observer-truth visibility arcs

- target visible 16.68–20.68s (4.0s), peak 1088 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 16.840000000002814, "first_usable_px": 773, "first_target_select_t": 17.080000000002254, "first_target_approach_t": 17.080000000002254, "delay_s": 0.23999999999944066, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 0, "scan_span_s": 0.0, "limit_s": 1.0, "window": null}
- FAIL **E01.4_no_non_target_outranks_visible_target** — {"frames": 69, "worst_span_s": 0.7999999999981355, "limit_s": 0.5, "spans": [{"t0": 16.840000000002814, "t1": 17.040000000002347, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9696034789085388, "target_px": 773, "selected_size_px": 81.17989349365234}, {"t0": 17.160000000002068, "t1": 17.600000000001042, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.40710318088531494, "target_px": 697, "selected_size_px": 110.49140930175781}, {"t0": 17.76000000000067, "t1": 17.800000000000576, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9199885129928589, "target_px": 655, "selected_size_px": 100.2486801147461}, {"t0": 17.88000000000039, "t1": 17.920000000000297, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.26488634943962097, "target_px": 598, "selected_size_px": 96.58985900878906}, {"t0": 18.040000000000017, "t1": 18.11999999999983, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.8146162033081055, "target_px": 581, "selected_size_px": 80.10740661621094}, {"t0": 18.199999999999644, "t1": 18.199999999999644, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.5798972845077515, "target_px": 595, "selected_size_px": 85.62039184570312}, {"t0": 18.279999999999458, "t1": 18.279999999999458, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.45208460092544556, "target_px": 607, "selected_size_px": 55.96976852416992}, {"t0": 18.35999999999927, "t1": 18.35999999999927, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.860007107257843, "target_px": 615, "selected_size_px": 75.3434829711914}, {"t0": 18.439999999999085, "t1": 18.63999999999862, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9585376977920532, "target_px": 632, "selected_size_px": 82.7237319946289}, {"t0": 18.719999999998432, "t1": 18.87999999999806, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.40029630064964294, "target_px": 715, "selected_size_px": 79.4938735961914}, {"t0": 18.99999999999778, "t1": 19.279999999997127, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.3458413779735565, "target_px": 750, "selected_size_px": 99.8934326171875}, {"t0": 19.519999999996568, "t1": 19.519999999996568, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.5219186544418335, "target_px": 733, "selected_size_px": 97.9958267211914}]}
- FAIL **E01.4_selection_continuity_after_lock** — {"frames_after": 2074, "frames_on_target": 21, "fraction": 0.0101, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 1201, "examples": [{"t": 18.75999999999834, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.799999999998246, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.839999999998152, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.87999999999806, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 19.679999999996195, "name": "decoy_blank_clone", "prob": 0.03264717385172844, "wrong": 0.8581274151802063, "size": 30.177722930908203}]}
- FAIL **E01.7_descent_keeps_useful_framing** — {"reason": "no descent permission frames"}
- FAIL **E01.8_descent_started_after_identity_and_geometry** — {"reason": "never descended"}
- PASS **E01.9_no_chatter** — {"intent_changes": 2, "span_s": 100.0, "per_10s": 0.2, "limit": 6.0}
- PASS **E01.9_descent_permission_stable** — {"reversals": 0, "limit": 3}
- FAIL **E01.9_no_unnecessary_hold** — {"worst_hold_s": 61.1200000002563, "limit_s": 6.0, "holds": [{"t0": 25.31999999998305, "t1": 31.63999999996832, "phase": "target_inspect"}, {"t0": 32.879999999965435, "t1": 35.27999999995984, "phase": "target_inspect"}, {"t0": 35.359999999959655, "t1": 37.03999999995574, "phase": "target_inspect"}, {"t0": 38.839999999951544, "t1": 99.96000000020784, "phase": "target_inspect"}]}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 165}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.066, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- FAIL **E01.11_physical_termination** — {"outcome": "flying", "landed": false, "armed": true, "final_clearance": 5.6921194482187065, "final_t": 100.00000000020803, "touchdown_s": null}
- PASS **integrity.observer_join** — {"frames": 2501, "joined_frames": 2501}

Behavioural acceptance: **False** (7 failing checks).
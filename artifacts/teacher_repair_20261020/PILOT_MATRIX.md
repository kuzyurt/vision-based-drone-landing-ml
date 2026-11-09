# Episode matrix (evidence-joined gate v2)

| case | situation | tier | outcome | lock t | on target | frames | hard failures | soft failures |
|---|---|---|---|---|---|---|---|---|
| E01_nominal_v60c | E01 | **SILVER** | landed | 0.12 | 100.00% | 1162 | — | physical.no_press_after_contact |
| E02_v60 | E02 | **REJECT** | development_diagnostic_stop | 17.08 | 1.01% | 2501 | physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact, authority.confirmed_object_is_truth_target, authority.selection_continuity | digest.matches_recording |
| E03_v60 | E03 | **REJECT** | collision_failure | 0.12 | 100.00% | 1138 | physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact, physical.no_collision, authority.descent_only_on_confirmed_target | physical.no_press_after_contact, authority.guards_engaged_with_enforcement, digest.matches_recording |
| E03_v60_repair | E03 | **SILVER** | landed | 0.2 | 100.00% | 1215 | — | physical.no_press_after_contact |
| E03_v60_forced | E03 | **SILVER** | landed | 0.24 | 100.00% | 1117 | — | physical.no_press_after_contact |
| E04_v60 | E04 | **SILVER** | landed | 0.08 | 100.00% | 1647 | — | physical.no_press_after_contact |
| E05_v60 | E05 | **SILVER** | landed | 0.12 | 100.00% | 1151 | — | physical.no_press_after_contact |
| E06_v60 | E06 | **SILVER** | landed | 17.48 | 100.00% | 2203 | — | physical.no_press_after_contact |
| E07_v60 | E07 | **SILVER** | landed | 18.08 | 100.00% | 1931 | — | physical.no_press_after_contact |
| E08_v60 | E08 | **REJECT** | development_diagnostic_stop | 20.76 | 99.88% | 1338 | physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact | digest.matches_recording |

Perception-training eligible: **E01_nominal_v60c, E03_v60_repair, E03_v60_forced, E04_v60, E05_v60, E06_v60, E07_v60**

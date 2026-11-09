| range | boat px | extent px | pad px (oct/cur) | Oct 25 teacher | why | 3k stills | why |
|---:|---:|---:|---:|---|---|---|---|
| 2 m | 49203 | 332 | 40.4 / 85.2 | **target_boat** | ok | **target_boat** | ok |
| 3 m | 36850 | 296 | 30.3 / 74.0 | **target_boat** | ok | **target_boat** | ok |
| 4 m | 26369 | 243 | 22.5 / 63.8 | **target_boat** | ok | **target_boat** | ok |
| 5 m | 18918 | 198 | 16.8 / 55.3 | **target_boat** | ok | **target_boat** | ok |
| 6 m | 13828 | 171 | 12.8 / 48.4 | **target_boat** | ok | **target_boat** | ok |
| 7 m | 10298 | 151 | 10.0 / 42.9 | **target_boat** | ok | **target_boat** | ok |
| 8 m | 7868 | 135 | 8.0 / 38.3 | **target_boat** | ok | **target_boat** | ok |
| 10 m | 4907 | 110 | 5.3 / 31.5 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 12 m | 3299 | 93 | 3.8 / 26.7 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 14 m | 2347 | 80 | 2.8 / 23.1 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 15 m | 2021 | 75 | 2.4 / 21.6 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 18 m | 1345 | 64 | 1.7 / 18.1 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 20 m | 1057 | 57 | 1.4 / 16.4 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 25 m | 646 | 46 | 0.9 / 13.2 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 30 m | 431 | 38 | 0.6 / 11.0 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 33 m | 346 | 34 | 0.5 / 10.0 | **target_or_similar** | pad missing or < 6 px | **target_boat** | ok |
| 35 m | 313 | 33 | 0.4 / 9.4 | **target_or_similar** | pad missing or < 6 px | **target_or_similar** | pad < 10 px |
| 36 m | 291 | 32 | 0.4 / 9.2 | **unknown_boat** | range > 35 m | **target_or_similar** | pad < 10 px |
| 40 m | 234 | 29 | 0.3 / 8.3 | **unknown_boat** | range > 35 m | **target_or_similar** | pad < 10 px |
| 45 m | 182 | 25 | 0.2 / 7.4 | **unknown_boat** | range > 35 m | **target_or_similar** | pad < 10 px |
| 48 m | 157 | 24 | 0.2 / 6.9 | **unknown_boat** | range > 35 m | **target_or_similar** | pad < 10 px |

## Why the October head answers `target_or_similar`

* Its teacher refused every identity claim beyond **35 m** (`unknown_boat`).
* Between ~20 m and 35 m the pad drops under **6 px**, so the teacher emitted
  `target_or_similar` while the boat itself was still easy to see and owned a heat cell.
* `identity_supervision_valid` is true only for `target_boat` / `different_boat`,
  so those mid-range frames contributed no identity gradient at all.
* At inference `decode()` additionally demotes `target_boat` to `target_or_similar`
  unless `identity_threshold` 0.98 is met, which is a very high bar.

The 3k rule has no range cutoff and a lower pad bar (10 px), so it keeps teaching
`target_boat` closer in, where the October rule had already given up.

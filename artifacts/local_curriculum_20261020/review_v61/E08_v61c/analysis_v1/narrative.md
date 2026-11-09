# Flight narrative — E08_v61c

Scenario `windows_review_E08_search_far` kind=beach seed=3200000003 distance=52.0m height=8.0m boat_speed=0.3m/s initial_target=outside_camera fault=None mode=expert
Frames 4323, task duration 172.88s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–20.60 | 0–515 | scan | complete_observed_360_before_inspection_pass | none | 0 | -140° | 8.5 | 52.2 | no | — |
| 20.64–20.72 | 516–518 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track13(none) | 0 | -31° | 8.5 | 58.6 | no | — |
| 20.76–27.56 | 519–689 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(target) | 112 | -30° | 8.5 | 58.6 | no | 323px |
| 27.60–27.60 | 690–690 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 88 | +0° | 8.5 | 54.5 | no | 1px |
| 27.64–27.68 | 691–692 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 91 | +1° | 8.5 | 54.4 | no | 6px |
| 27.72–27.72 | 693–693 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 93 | +2° | 8.5 | 54.2 | no | 23px |
| 27.76–27.84 | 694–696 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 93 | +3° | 8.5 | 54.2 | no | 31px |
| 27.88–27.88 | 697–697 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 94 | +5° | 8.5 | 53.9 | no | 50px |
| 27.92–28.08 | 698–702 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 95 | +6° | 8.5 | 53.9 | no | 56px |
| 28.12–28.24 | 703–706 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 98 | +8° | 8.5 | 53.5 | no | 75px |
| 28.28–28.28 | 707–707 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 102 | +8° | 8.5 | 53.2 | no | 83px |
| 28.32–28.60 | 708–715 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 99 | +9° | 8.5 | 53.1 | no | 84px |
| 28.64–28.64 | 716–716 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track13(none) | 100 | +9° | 8.5 | 52.6 | no | 93px |
| 28.68–28.68 | 717–717 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 98 | +9° | 8.5 | 52.5 | no | 95px |
| 28.72–28.72 | 718–718 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 104 | +10° | 8.5 | 52.4 | no | 95px |
| 28.76–28.88 | 719–722 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 102 | +10° | 8.5 | 52.3 | no | 95px |
| 28.92–29.04 | 723–726 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 105 | +10° | 8.5 | 52.1 | no | 98px |
| 29.08–29.16 | 727–729 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track13(none) | 107 | +10° | 8.5 | 51.8 | no | 100px |
| 29.20–29.24 | 730–731 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track13(decoy_debris) | 108 | +10° | 8.5 | 51.6 | no | 101px |
| 29.28–29.28 | 732–732 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 106 | +10° | 8.5 | 51.4 | no | 101px |
| 29.32–29.36 | 733–734 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 103 | +10° | 8.5 | 51.3 | no | 101px |
| 29.40–29.40 | 735–735 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 106 | +10° | 8.5 | 51.2 | no | 100px |
| 29.44–29.44 | 736–736 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(none) | 99 | +10° | 8.5 | 51.1 | no | 99px |
| 29.48–30.68 | 737–767 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 105 | +10° | 8.5 | 51.1 | no | 99px |
| 30.72–30.72 | 768–768 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track13(decoy_debris) | 122 | +11° | 8.5 | 48.9 | no | 106px |
| 30.76–37.16 | 769–929 | inspect_candidate | plausible_boat_inspect_unknown_design | track13(decoy_debris) | 125 | +11° | 8.5 | 48.8 | no | 106px |
| 37.20–39.76 | 930–994 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 254 | +14° | 8.4 | 38.0 | no | 156px |
| 39.80–42.36 | 995–1059 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 302 | +0° | 8.4 | 33.6 | no | 2px |
| 42.40–56.28 | 1060–1407 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 415 | -0° | 8.4 | 29.1 | no | 1px |
| 56.32–60.56 | 1408–1514 | target_align | identity_and_fresh_geometry_associated | track18(target) | 8365 | -0° | 8.4 | 5.3 | yes | 24px |
| 60.60–61.00 | 1515–1525 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12800 | +3° | 8.4 | 0.3 | no | 11px |
| 61.04–61.44 | 1526–1536 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12808 | -1° | 8.4 | 0.3 | yes | 13px |
| 61.48–62.00 | 1537–1550 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12814 | +22° | 8.4 | 0.3 | no | 15px |
| 62.04–62.16 | 1551–1554 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12925 | +3° | 8.4 | 0.3 | no | 7px |
| 62.20–62.96 | 1555–1574 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12877 | +1° | 8.4 | 0.3 | yes | 13px |
| 63.00–63.52 | 1575–1588 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12686 | -5° | 8.4 | 0.4 | no | 14px |
| 63.56–63.80 | 1589–1595 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12767 | +5° | 8.4 | 0.4 | no | 22px |
| 63.84–64.40 | 1596–1610 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12761 | +5° | 8.4 | 0.4 | yes | 33px |
| 64.44–64.56 | 1611–1614 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12758 | -33° | 8.4 | 0.4 | no | 17px |
| 64.60–64.88 | 1615–1622 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track23(target) | 12796 | -0° | 8.4 | 0.5 | no | 14px |
| 64.92–64.96 | 1623–1624 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12719 | +13° | 8.4 | 0.5 | no | 10px |
| 65.00–65.04 | 1625–1626 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12766 | +16° | 8.4 | 0.6 | no | 13px |
| 65.08–65.20 | 1627–1630 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12755 | +14° | 8.4 | 0.6 | yes | 11px |
| 65.24–65.24 | 1631–1631 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track23(target) | 12756 | +16° | 8.4 | 0.6 | no | 14px |
| 65.28–65.76 | 1632–1644 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12697 | +19° | 8.4 | 0.6 | no | 14px |
| 65.80–66.00 | 1645–1650 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12627 | +7° | 8.4 | 0.7 | no | 9px |
| 66.04–67.04 | 1651–1676 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12631 | +4° | 8.4 | 0.7 | yes | 17px |
| 67.08–67.36 | 1677–1684 | target_align | identity_and_fresh_geometry_associated | track23(target) | 12787 | +11° | 8.4 | 0.9 | yes | 29px |
| 67.40–67.40 | 1685–1685 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12888 | +1° | 8.3 | 0.9 | yes | 18px |
| 67.44–67.44 | 1686–1686 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12921 | -2° | 8.3 | 0.9 | no | 15px |
| 67.48–67.68 | 1687–1692 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12851 | -3° | 8.3 | 0.9 | yes | 9px |
| 67.72–68.08 | 1693–1702 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13068 | +2° | 8.3 | 0.8 | no | 34px |
| 68.12–68.12 | 1703–1703 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13139 | +4° | 8.3 | 0.6 | yes | 53px |
| 68.16–68.24 | 1704–1706 | target_align | identity_and_fresh_geometry_associated | track23(target) | 13138 | +5° | 8.3 | 0.6 | yes | 52px |
| 68.28–68.64 | 1707–1716 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13089 | +3° | 8.3 | 0.5 | yes | 48px |
| 68.68–68.96 | 1717–1724 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12910 | +25° | 8.4 | 0.5 | no | 16px |
| 69.00–69.04 | 1725–1726 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track23(target) | 12824 | +4° | 8.4 | 0.5 | no | 9px |
| 69.08–69.20 | 1727–1730 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12866 | +1° | 8.4 | 0.5 | no | 4px |
| 69.24–69.40 | 1731–1735 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12851 | -4° | 8.4 | 0.5 | no | 2px |
| 69.44–69.44 | 1736–1736 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track23(target) | 12837 | +3° | 8.4 | 0.5 | no | 24px |
| 69.48–69.88 | 1737–1747 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12852 | +3° | 8.4 | 0.5 | no | 29px |
| 69.92–69.96 | 1748–1749 | target_align | identity_and_fresh_geometry_associated | track23(target) | 12895 | +3° | 8.4 | 0.5 | yes | 39px |
| 70.00–70.24 | 1750–1756 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12863 | +2° | 8.4 | 0.5 | yes | 39px |
| 70.28–70.28 | 1757–1757 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12822 | +2° | 8.4 | 0.6 | no | 12px |
| 70.32–70.52 | 1758–1763 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12780 | +2° | 8.4 | 0.6 | yes | 11px |
| 70.56–70.56 | 1764–1764 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12818 | +16° | 8.4 | 0.6 | no | 12px |
| 70.60–70.68 | 1765–1767 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 12837 | +19° | 8.4 | 0.6 | no | 15px |
| 70.72–70.96 | 1768–1774 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12804 | +6° | 8.4 | 0.6 | no | 6px |
| 71.00–71.08 | 1775–1777 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 12807 | +3° | 8.4 | 0.6 | no | 9px |
| 71.12–71.32 | 1778–1783 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track25(target) | 12855 | +2° | 8.4 | 0.6 | no | 10px |
| 71.36–71.60 | 1784–1790 | target_align | identity_and_fresh_geometry_associated | track25(target) | 12875 | +0° | 8.4 | 0.7 | yes | 18px |
| 71.64–71.80 | 1791–1795 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12831 | -3° | 8.4 | 0.7 | yes | 4px |
| 71.84–72.28 | 1796–1807 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12780 | -7° | 8.4 | 0.7 | no | 10px |
| 72.32–72.60 | 1808–1815 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12713 | +8° | 8.4 | 0.8 | yes | 9px |
| 72.64–73.16 | 1816–1829 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12781 | +20° | 8.4 | 0.8 | no | 23px |
| 73.20–73.20 | 1830–1830 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12845 | +1° | 8.4 | 0.8 | no | 24px |
| 73.24–73.36 | 1831–1834 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12841 | +1° | 8.4 | 0.8 | yes | 22px |
| 73.40–73.52 | 1835–1838 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 12879 | -3° | 8.4 | 0.7 | no | 19px |
| 73.56–73.80 | 1839–1845 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12901 | -1° | 8.3 | 0.7 | no | 17px |
| 73.84–73.92 | 1846–1848 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 12895 | +3° | 8.3 | 0.7 | no | 4px |
| 73.96–74.00 | 1849–1850 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track25(target) | 12873 | +4° | 8.3 | 0.7 | no | 5px |
| 74.04–74.36 | 1851–1859 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12908 | +3° | 8.3 | 0.7 | no | 5px |
| 74.40–74.68 | 1860–1867 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12951 | +3° | 8.3 | 0.7 | yes | 29px |
| 74.72–74.76 | 1868–1869 | target_align | identity_and_fresh_geometry_associated | track25(target) | 12892 | -7° | 8.3 | 0.7 | yes | 9px |
| 74.80–75.16 | 1870–1879 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12941 | -7° | 8.3 | 0.8 | yes | 14px |
| 75.20–75.32 | 1880–1883 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 12963 | +27° | 8.3 | 0.8 | no | 29px |
| 75.36–75.68 | 1884–1892 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 12981 | +11° | 8.3 | 0.8 | no | 14px |
| 75.72–75.84 | 1893–1896 | target_align | identity_and_fresh_geometry_associated | track25(target) | 13053 | +3° | 8.3 | 0.8 | yes | 21px |
| 75.88–76.12 | 1897–1903 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 13039 | +4° | 8.3 | 0.8 | no | 9px |
| 76.16–76.40 | 1904–1910 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13010 | +1° | 8.3 | 0.8 | no | 11px |
| 76.44–76.52 | 1911–1913 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 12961 | +3° | 8.3 | 0.8 | no | 9px |
| 76.56–76.68 | 1914–1917 | target_align | identity_and_fresh_geometry_associated | track18(target) | 12991 | +4° | 8.3 | 0.8 | yes | 14px |
| 76.72–77.12 | 1918–1928 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13020 | +4° | 8.3 | 0.8 | no | 14px |
| 77.16–77.24 | 1929–1931 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13084 | +6° | 8.3 | 0.8 | no | 10px |
| 77.28–77.32 | 1932–1933 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13060 | +6° | 8.3 | 0.8 | yes | 8px |
| 77.36–77.64 | 1934–1941 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13082 | +5° | 8.3 | 0.8 | yes | 9px |
| 77.68–77.76 | 1942–1944 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13149 | +14° | 8.3 | 0.8 | no | 13px |
| 77.80–77.84 | 1945–1946 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13131 | +3° | 8.3 | 0.8 | no | 10px |
| 77.88–78.08 | 1947–1952 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13101 | +1° | 8.3 | 0.7 | no | 5px |
| 78.12–78.40 | 1953–1960 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13064 | +2° | 8.3 | 0.7 | yes | 15px |
| 78.44–78.48 | 1961–1962 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13114 | +15° | 8.3 | 0.7 | no | 16px |
| 78.52–78.52 | 1963–1963 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13054 | +15° | 8.3 | 0.7 | yes | 18px |
| 78.56–78.60 | 1964–1965 | target_align | identity_and_fresh_geometry_associated | track25(target) | 13076 | +12° | 8.3 | 0.7 | yes | 14px |
| 78.64–78.64 | 1966–1966 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13010 | +6° | 8.3 | 0.7 | yes | 6px |
| 78.68–78.76 | 1967–1969 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13071 | +5° | 8.3 | 0.7 | no | 5px |
| 78.80–79.36 | 1970–1984 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13056 | +4° | 8.3 | 0.6 | yes | 5px |
| 79.40–79.48 | 1985–1987 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13214 | +5° | 8.3 | 0.4 | no | 25px |
| 79.52–79.64 | 1988–1991 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13275 | +2° | 8.3 | 0.4 | yes | 36px |
| 79.68–79.68 | 1992–1992 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13318 | +3° | 8.3 | 0.3 | no | 36px |
| 79.72–80.40 | 1993–2010 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13337 | +4° | 8.3 | 0.3 | yes | 32px |
| 80.44–80.56 | 2011–2014 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13618 | -33° | 8.2 | 0.2 | no | 9px |
| 80.60–80.96 | 2015–2024 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13716 | -0° | 8.1 | 0.2 | yes | 3px |
| 81.00–81.00 | 2025–2025 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13792 | +14° | 8.1 | 0.2 | no | 8px |
| 81.04–81.16 | 2026–2029 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13789 | +13° | 8.1 | 0.2 | yes | 10px |
| 81.20–81.24 | 2030–2031 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13808 | +11° | 8.1 | 0.2 | yes | 8px |
| 81.28–81.72 | 2032–2043 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13770 | +11° | 8.1 | 0.2 | no | 7px |
| 81.76–81.80 | 2044–2045 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13759 | +3° | 8.1 | 0.2 | no | 3px |
| 81.84–82.04 | 2046–2051 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 13771 | +4° | 8.1 | 0.1 | no | 2px |
| 82.08–82.12 | 2052–2053 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13847 | +15° | 8.1 | 0.1 | yes | 36px |
| 82.16–82.56 | 2054–2064 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13902 | +16° | 8.1 | 0.2 | yes | 45px |
| 82.60–82.60 | 2065–2065 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13766 | +179° | 8.1 | 0.2 | no | 13px |
| 82.64–82.80 | 2066–2070 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13740 | -45° | 8.1 | 0.2 | yes | 11px |
| 82.84–83.36 | 2071–2084 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 13725 | -4° | 8.1 | 0.2 | no | 11px |
| 83.40–83.84 | 2085–2096 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 13734 | +2° | 8.1 | 0.2 | no | 7px |
| 83.88–83.92 | 2097–2098 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track25(target) | 13979 | +9° | 8.1 | 0.2 | no | 51px |
| 83.96–84.24 | 2099–2106 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 13950 | +10° | 8.1 | 0.2 | no | 49px |
| 84.28–84.32 | 2107–2108 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track25(target) | 13981 | +8° | 8.1 | 0.3 | no | 53px |
| 84.36–84.40 | 2109–2110 | target_align | identity_and_fresh_geometry_associated | track25(target) | 13970 | +9° | 8.1 | 0.3 | yes | 54px |
| 84.44–85.32 | 2111–2133 | target_align | identity_and_fresh_geometry_associated | track18(target) | 13916 | +8° | 8.1 | 0.3 | yes | 49px |
| 85.36–85.88 | 2134–2147 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14082 | +57° | 8.0 | 0.5 | no | 28px |
| 85.92–86.36 | 2148–2159 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14419 | +6° | 8.0 | 0.4 | no | 34px |
| 86.40–86.60 | 2160–2165 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14701 | +8° | 8.0 | 0.4 | yes | 70px |
| 86.64–86.68 | 2166–2167 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14495 | -12° | 8.0 | 0.4 | no | 33px |
| 86.72–86.84 | 2168–2171 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14443 | -9° | 8.0 | 0.4 | yes | 25px |
| 86.88–87.40 | 2172–2185 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14420 | +15° | 8.0 | 0.4 | no | 13px |
| 87.44–87.52 | 2186–2188 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14279 | +13° | 8.0 | 0.5 | no | 7px |
| 87.56–88.08 | 2189–2202 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14249 | +9° | 8.0 | 0.5 | yes | 6px |
| 88.12–88.12 | 2203–2203 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14309 | +12° | 7.9 | 0.5 | no | 10px |
| 88.16–88.32 | 2204–2208 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14344 | +16° | 7.9 | 0.5 | yes | 11px |
| 88.36–88.84 | 2209–2221 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14447 | +34° | 7.9 | 0.5 | no | 20px |
| 88.88–89.00 | 2222–2225 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14432 | +8° | 7.9 | 0.5 | yes | 8px |
| 89.04–89.56 | 2226–2239 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14393 | +7° | 7.9 | 0.5 | no | 6px |
| 89.60–89.68 | 2240–2242 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14484 | +10° | 7.9 | 0.5 | no | 11px |
| 89.72–90.48 | 2243–2262 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14471 | +7° | 7.9 | 0.5 | yes | 14px |
| 90.52–90.56 | 2263–2264 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14131 | +55° | 8.0 | 0.5 | no | 28px |
| 90.60–90.68 | 2265–2267 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14124 | +58° | 8.0 | 0.5 | yes | 28px |
| 90.72–90.72 | 2268–2268 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14088 | +20° | 8.0 | 0.5 | yes | 13px |
| 90.76–91.24 | 2269–2281 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14076 | +22° | 8.0 | 0.5 | no | 13px |
| 91.28–91.28 | 2282–2282 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14172 | +4° | 8.0 | 0.4 | no | 15px |
| 91.32–91.40 | 2283–2285 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14169 | +4° | 8.0 | 0.4 | no | 15px |
| 91.44–91.52 | 2286–2288 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14146 | +6° | 8.0 | 0.4 | yes | 19px |
| 91.56–92.04 | 2289–2301 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14158 | +8° | 8.0 | 0.4 | yes | 23px |
| 92.08–92.76 | 2302–2319 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14329 | +11° | 8.0 | 0.4 | yes | 5px |
| 92.80–93.08 | 2320–2327 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14618 | +6° | 7.9 | 0.3 | no | 10px |
| 93.12–93.24 | 2328–2331 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14686 | +3° | 7.9 | 0.2 | yes | 32px |
| 93.28–93.28 | 2332–2332 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14694 | +7° | 7.9 | 0.2 | no | 26px |
| 93.32–93.64 | 2333–2341 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14661 | +8° | 7.9 | 0.2 | yes | 22px |
| 93.68–93.68 | 2342–2342 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14572 | +13° | 7.9 | 0.1 | no | 2px |
| 93.72–94.12 | 2343–2353 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14517 | +9° | 7.9 | 0.1 | yes | 1px |
| 94.16–94.24 | 2354–2356 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14401 | -12° | 7.9 | 0.1 | no | 2px |
| 94.28–94.28 | 2357–2357 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14350 | -15° | 7.9 | 0.1 | no | 2px |
| 94.32–94.44 | 2358–2361 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14366 | -2° | 7.9 | 0.1 | yes | 2px |
| 94.48–94.92 | 2362–2373 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14381 | +12° | 7.9 | 0.1 | no | 21px |
| 94.96–95.00 | 2374–2375 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14309 | +9° | 7.9 | 0.1 | no | 6px |
| 95.04–95.12 | 2376–2378 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14318 | -41° | 7.9 | 0.1 | no | 0px |
| 95.16–95.88 | 2379–2397 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14359 | -52° | 7.9 | 0.1 | yes | 0px |
| 95.92–95.96 | 2398–2399 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14408 | +18° | 8.0 | 0.1 | no | 3px |
| 96.00–96.36 | 2400–2409 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14444 | +14° | 8.0 | 0.1 | yes | 2px |
| 96.40–96.72 | 2410–2418 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14528 | -34° | 7.9 | 0.1 | no | 8px |
| 96.76–96.92 | 2419–2423 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14386 | +17° | 7.9 | 0.0 | no | 4px |
| 96.96–97.16 | 2424–2429 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 14401 | +22° | 7.9 | 0.0 | no | 4px |
| 97.20–97.32 | 2430–2433 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14517 | +18° | 7.9 | 0.0 | yes | 40px |
| 97.36–97.44 | 2434–2436 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14534 | +24° | 7.9 | 0.1 | no | 42px |
| 97.48–97.68 | 2437–2442 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14426 | +28° | 7.9 | 0.1 | yes | 15px |
| 97.72–97.84 | 2443–2446 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14415 | +145° | 7.9 | 0.1 | no | 6px |
| 97.88–97.92 | 2447–2448 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14326 | +4° | 8.0 | 0.1 | yes | 8px |
| 97.96–98.08 | 2449–2452 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14320 | +1° | 8.0 | 0.1 | no | 13px |
| 98.12–98.16 | 2453–2454 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14265 | +3° | 8.0 | 0.1 | no | 12px |
| 98.20–98.32 | 2455–2458 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14255 | +7° | 8.0 | 0.1 | yes | 20px |
| 98.36–98.60 | 2459–2465 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14197 | +7° | 8.0 | 0.1 | no | 1px |
| 98.64–98.76 | 2466–2469 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14209 | -3° | 8.0 | 0.1 | yes | 5px |
| 98.80–98.88 | 2470–2472 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14227 | +31° | 8.0 | 0.1 | no | 2px |
| 98.92–99.04 | 2473–2476 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14275 | +20° | 8.0 | 0.1 | yes | 2px |
| 99.08–99.20 | 2477–2480 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14308 | -5° | 8.0 | 0.1 | no | 0px |
| 99.24–99.72 | 2481–2493 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14291 | -6° | 8.0 | 0.1 | yes | 1px |
| 99.76–100.28 | 2494–2507 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14387 | -3° | 8.0 | 0.1 | no | 5px |
| 100.32–100.44 | 2508–2511 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14222 | -10° | 8.0 | 0.1 | yes | 3px |
| 100.48–100.48 | 2512–2512 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14246 | +173° | 8.0 | 0.1 | no | 3px |
| 100.52–100.72 | 2513–2518 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14303 | +168° | 8.0 | 0.0 | yes | 5px |
| 100.76–100.84 | 2519–2521 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14263 | -8° | 8.0 | 0.0 | yes | 9px |
| 100.88–101.00 | 2522–2525 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 14124 | +2° | 8.0 | 0.0 | no | 4px |
| 101.04–101.40 | 2526–2535 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13989 | -3° | 8.0 | 0.0 | no | 4px |
| 101.44–101.60 | 2536–2540 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 13903 | +6° | 8.0 | 0.0 | no | 6px |
| 101.64–101.76 | 2541–2544 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14092 | +22° | 8.0 | 0.0 | yes | 34px |
| 101.80–102.32 | 2545–2558 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14160 | +27° | 8.0 | 0.0 | no | 42px |
| 102.36–102.40 | 2559–2560 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 14016 | +10° | 8.1 | 0.1 | no | 4px |
| 102.44–102.68 | 2561–2567 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14034 | +8° | 8.1 | 0.1 | yes | 8px |
| 102.72–102.88 | 2568–2572 | target_align | identity_and_fresh_geometry_associated | track27(target) | 14004 | -174° | 8.1 | 0.1 | yes | 9px |
| 102.92–102.96 | 2573–2574 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13978 | -97° | 8.1 | 0.1 | yes | 3px |
| 103.00–103.00 | 2575–2575 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 13992 | -4° | 8.1 | 0.1 | no | 3px |
| 103.04–103.16 | 2576–2579 | target_align | identity_and_fresh_geometry_associated | track26(target) | 13934 | -1° | 8.1 | 0.1 | yes | 4px |
| 103.20–103.72 | 2580–2593 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14016 | +11° | 8.0 | 0.1 | no | 9px |
| 103.76–104.04 | 2594–2601 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 14033 | +12° | 8.0 | 0.1 | no | 10px |
| 104.08–104.24 | 2602–2606 | target_align | identity_and_fresh_geometry_associated | track18(target) | 14181 | +16° | 8.0 | 0.1 | yes | 50px |
| 104.28–104.36 | 2607–2609 | target_align | identity_and_fresh_geometry_associated | track18(none) | 14083 | +27° | 8.0 | 0.1 | yes | 24px |
| 104.40–104.44 | 2610–2611 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14039 | +69° | 8.0 | 0.1 | yes | 7px |
| 104.48–104.52 | 2612–2613 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14053 | +158° | 8.0 | 0.1 | no | 10px |
| 104.56–105.00 | 2614–2625 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14052 | -179° | 8.0 | 0.1 | yes | 10px |
| 105.04–105.04 | 2626–2626 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14139 | -4° | 8.0 | 0.1 | no | 9px |
| 105.08–105.36 | 2627–2634 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14107 | -3° | 8.0 | 0.1 | yes | 8px |
| 105.40–105.68 | 2635–2642 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14184 | +1° | 8.0 | 0.1 | no | 14px |
| 105.72–106.00 | 2643–2650 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14235 | -7° | 8.0 | 0.1 | yes | 7px |
| 106.04–106.04 | 2651–2651 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14222 | +14° | 8.0 | 0.1 | no | 4px |
| 106.08–106.28 | 2652–2657 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14141 | +19° | 8.0 | 0.1 | yes | 5px |
| 106.32–106.36 | 2658–2659 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14162 | +38° | 8.0 | 0.1 | no | 3px |
| 106.40–106.52 | 2660–2663 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14209 | +48° | 8.0 | 0.1 | yes | 4px |
| 106.56–106.72 | 2664–2668 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14213 | +150° | 8.0 | 0.1 | no | 4px |
| 106.76–107.12 | 2669–2678 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14244 | -3° | 8.0 | 0.1 | yes | 6px |
| 107.16–107.68 | 2679–2692 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14277 | -5° | 8.0 | 0.1 | no | 8px |
| 107.72–107.92 | 2693–2698 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 14374 | -14° | 7.9 | 0.0 | no | 5px |
| 107.96–109.20 | 2699–2730 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14448 | -1° | 7.9 | 0.0 | yes | 28px |
| 109.24–109.72 | 2731–2743 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14840 | +5° | 7.9 | 0.1 | no | 2px |
| 109.76–109.96 | 2744–2749 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14879 | -2° | 7.8 | 0.1 | yes | 4px |
| 110.00–110.52 | 2750–2763 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14843 | +57° | 7.8 | 0.1 | no | 7px |
| 110.56–110.68 | 2764–2767 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14885 | -16° | 7.8 | 0.1 | yes | 5px |
| 110.72–110.84 | 2768–2771 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 14897 | -10° | 7.8 | 0.1 | no | 5px |
| 110.88–111.00 | 2772–2775 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14965 | -21° | 7.8 | 0.1 | yes | 4px |
| 111.04–111.56 | 2776–2789 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15009 | +13° | 7.8 | 0.1 | no | 13px |
| 111.60–111.76 | 2790–2794 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 15072 | +10° | 7.8 | 0.1 | no | 3px |
| 111.80–111.92 | 2795–2798 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15103 | -5° | 7.8 | 0.1 | yes | 11px |
| 111.96–112.48 | 2799–2812 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15021 | +2° | 7.8 | 0.1 | no | 15px |
| 112.52–112.68 | 2813–2817 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 14964 | +5° | 7.8 | 0.1 | no | 1px |
| 112.72–113.32 | 2818–2833 | target_align | identity_and_fresh_geometry_associated | track26(target) | 14991 | +2° | 7.8 | 0.1 | yes | 15px |
| 113.36–113.88 | 2834–2847 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15245 | -10° | 7.7 | 0.1 | no | 4px |
| 113.92–113.92 | 2848–2848 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 15539 | +12° | 7.7 | 0.1 | no | 12px |
| 113.96–113.96 | 2849–2849 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 15516 | +13° | 7.7 | 0.1 | no | 11px |
| 114.00–114.28 | 2850–2857 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15538 | +13° | 7.7 | 0.1 | yes | 12px |
| 114.32–114.36 | 2858–2859 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15508 | +125° | 7.7 | 0.1 | no | 11px |
| 114.40–114.44 | 2860–2861 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track29(target) | 15540 | +69° | 7.7 | 0.1 | no | 6px |
| 114.48–114.84 | 2862–2871 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15526 | +11° | 7.7 | 0.1 | no | 6px |
| 114.88–115.24 | 2872–2881 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15510 | -2° | 7.7 | 0.1 | yes | 4px |
| 115.28–115.28 | 2882–2882 | target_align | identity_and_fresh_geometry_associated | track29(target) | 15540 | +12° | 7.7 | 0.1 | yes | 5px |
| 115.32–115.48 | 2883–2887 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15665 | +10° | 7.7 | 0.1 | yes | 6px |
| 115.52–115.52 | 2888–2888 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15620 | +22° | 7.7 | 0.1 | no | 2px |
| 115.56–116.20 | 2889–2905 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15563 | +14° | 7.7 | 0.1 | yes | 3px |
| 116.24–116.32 | 2906–2908 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15394 | -13° | 7.7 | 0.1 | no | 8px |
| 116.36–116.60 | 2909–2915 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15229 | -51° | 7.7 | 0.1 | no | 5px |
| 116.64–116.76 | 2916–2919 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15280 | -60° | 7.7 | 0.1 | no | 3px |
| 116.80–116.92 | 2920–2923 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 15166 | -34° | 7.7 | 0.1 | no | 3px |
| 116.96–117.32 | 2924–2933 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15266 | -11° | 7.7 | 0.0 | yes | 18px |
| 117.36–117.88 | 2934–2947 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15335 | +10° | 7.7 | 0.1 | no | 4px |
| 117.92–118.00 | 2948–2950 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 15440 | -20° | 7.7 | 0.1 | no | 3px |
| 118.04–118.20 | 2951–2955 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15583 | -28° | 7.7 | 0.1 | yes | 6px |
| 118.24–118.44 | 2956–2961 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15372 | -49° | 7.7 | 0.1 | yes | 5px |
| 118.48–118.56 | 2962–2964 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15415 | -108° | 7.7 | 0.1 | no | 4px |
| 118.60–118.92 | 2965–2973 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15390 | -174° | 7.7 | 0.1 | no | 7px |
| 118.96–118.96 | 2974–2974 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track29(target) | 15331 | -3° | 7.7 | 0.1 | no | 14px |
| 119.00–119.00 | 2975–2975 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15270 | -2° | 7.7 | 0.1 | no | 16px |
| 119.04–119.04 | 2976–2976 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15192 | -1° | 7.7 | 0.1 | yes | 16px |
| 119.08–119.32 | 2977–2983 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15214 | -1° | 7.7 | 0.0 | yes | 15px |
| 119.36–119.44 | 2984–2986 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15238 | +25° | 7.7 | 0.0 | no | 6px |
| 119.48–119.88 | 2987–2997 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15173 | +155° | 7.7 | 0.0 | no | 6px |
| 119.92–119.92 | 2998–2998 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 15239 | -7° | 7.7 | 0.0 | no | 16px |
| 119.96–120.00 | 2999–3000 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15250 | -7° | 7.7 | 0.0 | yes | 16px |
| 120.04–120.08 | 3001–3002 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15276 | -8° | 7.7 | 0.0 | yes | 15px |
| 120.12–120.56 | 3003–3014 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15287 | -2° | 7.7 | 0.0 | no | 11px |
| 120.60–120.64 | 3015–3016 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15294 | -61° | 7.7 | 0.0 | no | 7px |
| 120.68–120.80 | 3017–3020 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 15335 | -71° | 7.7 | 0.0 | no | 6px |
| 120.84–120.84 | 3021–3021 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15397 | -77° | 7.7 | 0.0 | yes | 24px |
| 120.88–120.88 | 3022–3022 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15439 | -77° | 7.7 | 0.0 | yes | 32px |
| 120.92–121.00 | 3023–3025 | target_align | identity_and_fresh_geometry_associated | track27(none) | 15477 | -75° | 7.7 | 0.0 | yes | 39px |
| 121.04–121.24 | 3026–3031 | target_align | identity_and_fresh_geometry_associated | track29(target) | 15416 | -57° | 7.7 | 0.0 | yes | 29px |
| 121.28–121.60 | 3032–3040 | target_align | identity_and_fresh_geometry_associated | track27(target) | 15365 | -45° | 7.7 | 0.0 | yes | 10px |
| 121.64–121.64 | 3041–3041 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15624 | -19° | 7.7 | 0.0 | yes | 5px |
| 121.68–121.88 | 3042–3047 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 15626 | -5° | 7.7 | 0.0 | no | 4px |
| 121.92–122.12 | 3048–3053 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 15933 | +25° | 7.6 | 0.0 | no | 2px |
| 122.16–122.20 | 3054–3055 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track29(target) | 15883 | +16° | 7.6 | 0.0 | no | 3px |
| 122.24–122.24 | 3056–3056 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track29(target) | 15936 | +6° | 7.6 | 0.0 | no | 4px |
| 122.28–122.28 | 3057–3057 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 15889 | +1° | 7.6 | 0.0 | no | 4px |
| 122.32–123.56 | 3058–3089 | target_align | identity_and_fresh_geometry_associated | track26(target) | 15888 | -10° | 7.6 | 0.0 | yes | 5px |
| 123.60–123.68 | 3090–3092 | target_align | identity_and_fresh_geometry_associated | track27(target) | 16717 | +17° | 7.4 | 0.0 | yes | 7px |
| 123.72–123.72 | 3093–3093 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 16880 | +13° | 7.4 | 0.0 | no | 5px |
| 123.76–124.00 | 3094–3100 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 16952 | +11° | 7.4 | 0.0 | no | 4px |
| 124.04–124.12 | 3101–3103 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 17057 | -20° | 7.3 | 0.0 | no | 4px |
| 124.16–124.24 | 3104–3106 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track29(target) | 17102 | -22° | 7.3 | 0.0 | no | 4px |
| 124.28–124.28 | 3107–3107 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track29(target) | 17212 | -26° | 7.3 | 0.0 | no | 5px |
| 124.32–124.32 | 3108–3108 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 17129 | -25° | 7.3 | 0.0 | no | 5px |
| 124.36–124.40 | 3109–3110 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track26(target) | 17145 | -25° | 7.3 | 0.0 | no | 7px |
| 124.44–124.60 | 3111–3115 | target_align | identity_and_fresh_geometry_associated | track26(target) | 17161 | -23° | 7.3 | 0.0 | yes | 20px |
| 124.64–124.72 | 3116–3118 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17177 | -16° | 7.3 | 0.0 | yes | 23px |
| 124.76–125.00 | 3119–3125 | target_align | identity_and_fresh_geometry_associated | track26(target) | 17194 | +39° | 7.3 | 0.0 | yes | 2px |
| 125.04–125.08 | 3126–3127 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17388 | -28° | 7.3 | 0.0 | yes | 13px |
| 125.12–125.16 | 3128–3129 | target_align | identity_and_fresh_geometry_associated | track29(target) | 17424 | -27° | 7.3 | 0.0 | yes | 14px |
| 125.20–125.44 | 3130–3136 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17452 | -19° | 7.3 | 0.0 | yes | 11px |
| 125.48–125.88 | 3137–3147 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 17452 | +2° | 7.3 | 0.0 | no | 9px |
| 125.92–125.96 | 3148–3149 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track29(target) | 17242 | -103° | 7.3 | 0.1 | no | 2px |
| 126.00–126.00 | 3150–3150 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 17205 | -36° | 7.3 | 0.1 | no | 1px |
| 126.04–126.20 | 3151–3155 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 17189 | -18° | 7.3 | 0.1 | no | 1px |
| 126.24–126.32 | 3156–3158 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17283 | +9° | 7.3 | 0.1 | yes | 29px |
| 126.36–126.36 | 3159–3159 | target_align | identity_and_fresh_geometry_associated | track29(target) | 17389 | +13° | 7.3 | 0.1 | yes | 43px |
| 126.40–127.24 | 3160–3181 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17368 | +15° | 7.3 | 0.1 | yes | 38px |
| 127.28–127.84 | 3182–3196 | target_align | identity_and_fresh_geometry_associated | track26(target) | 17748 | -17° | 7.2 | 0.1 | yes | 10px |
| 127.88–127.88 | 3197–3197 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track26(target) | 17838 | +6° | 7.2 | 0.1 | no | 5px |
| 127.92–128.40 | 3198–3210 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 17861 | +7° | 7.2 | 0.1 | no | 6px |
| 128.44–128.44 | 3211–3211 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track27(target) | 17916 | +8° | 7.2 | 0.0 | no | 5px |
| 128.48–128.68 | 3212–3217 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17899 | +8° | 7.2 | 0.0 | yes | 6px |
| 128.72–128.80 | 3218–3220 | target_align | identity_and_fresh_geometry_associated | track29(target) | 17881 | +22° | 7.2 | 0.0 | yes | 8px |
| 128.84–129.36 | 3221–3234 | target_align | identity_and_fresh_geometry_associated | track27(target) | 17923 | +14° | 7.2 | 0.0 | yes | 5px |
| 129.40–129.92 | 3235–3248 | target_align | identity_and_fresh_geometry_associated | track29(target) | 18025 | -80° | 7.2 | 0.0 | yes | 3px |
| 129.96–130.20 | 3249–3255 | target_align | identity_and_fresh_geometry_associated | track26(target) | 18420 | -25° | 7.1 | 0.0 | yes | 10px |
| 130.24–131.08 | 3256–3277 | target_align | identity_and_fresh_geometry_associated | track27(target) | 18862 | +9° | 7.0 | 0.0 | yes | 2px |
| 131.12–131.12 | 3278–3278 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 19952 | +99° | 6.9 | 0.0 | no | 1px |
| 131.16–131.80 | 3279–3295 | target_align | identity_and_fresh_geometry_associated | track27(target) | 20000 | +144° | 6.8 | 0.0 | yes | 2px |
| 131.84–131.88 | 3296–3297 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 20705 | -23° | 6.7 | 0.0 | no | 5px |
| 131.92–132.16 | 3298–3304 | target_align | identity_and_fresh_geometry_associated | track26(target) | 20793 | -41° | 6.7 | 0.0 | yes | 6px |
| 132.20–132.24 | 3305–3306 | target_align | identity_and_fresh_geometry_associated | track27(target) | 20998 | -57° | 6.7 | 0.0 | yes | 5px |
| 132.28–132.52 | 3307–3313 | target_align | identity_and_fresh_geometry_associated | track26(target) | 21151 | -94° | 6.7 | 0.0 | yes | 5px |
| 132.56–132.56 | 3314–3314 | target_align | identity_and_fresh_geometry_associated | track27(target) | 21027 | -48° | 6.7 | 0.1 | yes | 3px |
| 132.60–132.64 | 3315–3316 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 21104 | -40° | 6.7 | 0.1 | no | 2px |
| 132.68–132.88 | 3317–3322 | target_align | identity_and_fresh_geometry_associated | track27(target) | 20999 | +113° | 6.7 | 0.1 | yes | 3px |
| 132.92–132.92 | 3323–3323 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track27(target) | 21181 | +61° | 6.7 | 0.1 | no | 2px |
| 132.96–133.72 | 3324–3343 | target_align | identity_and_fresh_geometry_associated | track27(target) | 21067 | +72° | 6.7 | 0.1 | yes | 2px |
| 133.76–134.32 | 3344–3358 | target_align | identity_and_fresh_geometry_associated | track26(target) | 22081 | -109° | 6.6 | 0.0 | yes | 6px |
| 134.36–134.72 | 3359–3368 | target_align | identity_and_fresh_geometry_associated | track27(target) | 23411 | -5° | 6.4 | 0.0 | yes | 5px |
| 134.76–136.20 | 3369–3405 | target_align | identity_and_fresh_geometry_associated | track26(target) | 24305 | -26° | 6.3 | 0.0 | yes | 4px |
| 136.24–136.28 | 3406–3407 | target_align | identity_and_fresh_geometry_associated | track29(target) | 27560 | -53° | 5.9 | 0.0 | yes | 5px |
| 136.32–136.72 | 3408–3418 | target_align | identity_and_fresh_geometry_associated | track26(target) | 27746 | -121° | 5.9 | 0.0 | yes | 4px |
| 136.76–136.84 | 3419–3421 | target_align | identity_and_fresh_geometry_associated | track27(target) | 28762 | -108° | 5.8 | 0.0 | yes | 8px |
| 136.88–137.20 | 3422–3430 | target_align | identity_and_fresh_geometry_associated | track26(target) | 29104 | -125° | 5.8 | 0.0 | yes | 4px |
| 137.24–137.44 | 3431–3436 | target_align | identity_and_fresh_geometry_associated | track29(target) | 29916 | +36° | 5.7 | 0.0 | yes | 3px |
| 137.48–137.52 | 3437–3438 | target_align | identity_and_fresh_geometry_associated | track27(target) | 30438 | +78° | 5.7 | 0.0 | yes | 3px |
| 137.56–141.08 | 3439–3527 | target_align | identity_and_fresh_geometry_associated | track26(target) | 30613 | +84° | 5.7 | 0.0 | yes | 4px |
| 141.12–141.12 | 3528–3528 | target_align | identity_and_fresh_geometry_associated | track27(target) | 41838 | -154° | 4.9 | 0.0 | yes | 7px |
| 141.16–141.32 | 3529–3533 | target_align | identity_and_fresh_geometry_associated | track29(target) | 41858 | -167° | 4.9 | 0.0 | yes | 7px |
| 141.36–141.60 | 3534–3540 | target_align | identity_and_fresh_geometry_associated | track26(target) | 42521 | -168° | 4.9 | 0.0 | yes | 9px |
| 141.64–141.84 | 3541–3546 | target_align | identity_and_fresh_geometry_associated | track29(target) | 43568 | +175° | 4.8 | 0.0 | yes | 6px |
| 141.88–145.40 | 3547–3635 | target_align | identity_and_fresh_geometry_associated | track26(target) | 45067 | -12° | 4.8 | 0.0 | yes | 2px |
| 145.44–146.08 | 3636–3652 | target_align | identity_and_fresh_geometry_associated | track29(target) | 65111 | -127° | 3.9 | 0.0 | yes | 2px |
| 146.12–150.32 | 3653–3758 | target_align | identity_and_fresh_geometry_associated | track26(target) | 69034 | +120° | 3.8 | 0.0 | yes | 4px |
| 150.36–150.52 | 3759–3763 | target_align | identity_and_fresh_geometry_associated | track29(target) | 97949 | +88° | 2.9 | 0.0 | yes | 2px |
| 150.56–151.80 | 3764–3795 | target_align | identity_and_fresh_geometry_associated | track26(target) | 99338 | +33° | 2.9 | 0.0 | yes | 1px |
| 151.84–152.36 | 3796–3809 | target_align | identity_and_fresh_geometry_associated | track29(target) | 114511 | +13° | 2.6 | 0.0 | yes | 2px |
| 152.40–153.40 | 3810–3835 | target_align | identity_and_fresh_geometry_associated | track26(target) | 122351 | -46° | 2.4 | 0.0 | yes | 4px |
| 153.44–153.52 | 3836–3838 | target_align | identity_and_fresh_geometry_associated | track37(target) | 138508 | +27° | 2.2 | 0.0 | yes | 0px |
| 153.56–153.88 | 3839–3847 | target_align | identity_and_fresh_geometry_associated | track26(target) | 140879 | +15° | 2.2 | 0.0 | yes | 0px |
| 153.92–154.72 | 3848–3868 | target_align | identity_and_fresh_geometry_associated | track37(target) | 147597 | +0° | 2.1 | 0.0 | yes | 2px |
| 154.76–155.28 | 3869–3882 | target_align | identity_and_fresh_geometry_associated | track33(target) | 168070 | +32° | 1.9 | 0.0 | yes | 0px |
| 155.32–155.48 | 3883–3887 | target_align | identity_and_fresh_geometry_associated | track37(target) | 186649 | -13° | 1.8 | 0.0 | yes | 2px |
| 155.52–156.24 | 3888–3906 | target_align | identity_and_fresh_geometry_associated | track33(target) | 194741 | +14° | 1.8 | 0.0 | yes | 2px |
| 156.28–157.76 | 3907–3944 | target_align | identity_and_fresh_geometry_associated | track40(target) | 226704 | +44° | 1.6 | 0.0 | yes | 0px |
| 157.80–161.80 | 3945–4045 | target_align | identity_and_fresh_geometry_associated | track43(target) | 222744 | -170° | 1.3 | 0.0 | yes | 0px |
| 161.84–163.96 | 4046–4099 | target_align | identity_and_fresh_geometry_associated | track47(target) | 213506 | -165° | 1.0 | 0.0 | yes | 0px |
| 164.00–170.80 | 4100–4270 | target_align | identity_and_fresh_geometry_associated | track48(target) | 215042 | -98° | 1.0 | 0.0 | yes | 0px |
| 170.84–172.84 | 4271–4321 | ground_hold | own_estimator_not_airborne | track48(target) | 149992 | -73° | 0.7 | 0.0 | no | 0px |
| 172.88–172.88 | 4322–4322 | ground_hold | own_estimator_not_airborne | track48(target) | 150003 | -78° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 104.28–104.36s: selected track18(none) while target had 14083 px of visible structure; selected object 74 px, target_probability 0.0045, wrong_object_probability 0.923.
- 120.92–121.00s: selected track27(none) while target had 15477 px of visible structure; selected object 119 px, target_probability 0.0127, wrong_object_probability 0.943.

## Observer-truth visibility arcs

- target visible 17.52–20.60s (3.1s), peak 121 px, identity support 0.00
- target visible 20.72–172.88s (152.2s), peak 226848 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 39.799999999943196, "first_usable_px": 302, "first_target_select_t": 20.759999999987567, "first_target_approach_t": 20.759999999987567, "delay_s": -19.03999999995563, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 0, "scan_span_s": 0.0, "limit_s": 1.0, "window": null}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 6, "worst_span_s": 0.08000000000038199, "limit_s": 0.5, "spans": [{"t0": 104.28000000023458, "t1": 104.36000000023496, "selected": "none", "selected_boat": true, "target_prob": 0.004481701646000147, "target_px": 14083, "selected_size_px": 73.66468811035156}, {"t0": 120.92000000031403, "t1": 121.00000000031442, "selected": "none", "selected_boat": true, "target_prob": 0.012734813615679741, "target_px": 15477, "selected_size_px": 118.5488510131836}]}
- FAIL **E01.4_selection_continuity_after_lock** — {"frames_after": 3804, "frames_on_target": 3558, "fraction": 0.9353, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 249, "examples": [{"t": 20.639999999987847, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 20.679999999987754, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 20.71999999998766, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 27.599999999971626, "name": "decoy_debris", "prob": 1.5354113429566496e-06, "wrong": 0.5199069976806641, "size": 11.795333862304688}, {"t": 27.639999999971533, "name": "none", "prob": 1.5354113429566496e-06, "wrong": 0.5199069976806641, "size": 11.795333862304688}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 1991, "lost_frames": 63, "good_frames": 1739, "lost_fraction": 0.0316, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 56.32000000000558, "metric_confirmed_at_start": true, "descent_span_s": 114.48000000054664}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.84, "limit_s": 1.0, "windows": [{"t0": 56.560000000006724, "t1": 56.80000000000787, "pad_err": 47.00265949922408}, {"t0": 57.72000000001226, "t1": 58.04000000001379, "pad_err": 45.17742799230607}, {"t0": 58.4400000000157, "t1": 59.28000000001971, "pad_err": 48.66466890876789}, {"t0": 68.12000000006192, "t1": 68.44000000006345, "pad_err": 53.115440316352455}, {"t0": 84.36000000013946, "t1": 84.44000000013985, "pad_err": 54.037024344425184}, {"t0": 86.4000000001492, "t1": 86.56000000014997, "pad_err": 70.0446286306095}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 74, "span_s": 172.88, "per_10s": 4.28, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 164, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 2.719999999993661, "limit_s": 6.0, "holds": [{"t0": 20.639999999987847, "t1": 23.359999999981508, "phase": "inspect_candidate"}]}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 1215}
- FAIL **E01.10b_parent_recovery_share_below_limit** — {"share": 0.2811, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.0015642371653810105, "final_t": 172.88000000056215, "touchdown_s": 189.08000000053877}
- PASS **integrity.observer_join** — {"frames": 4323, "joined_frames": 4323}

Behavioural acceptance: **False** (4 failing checks).
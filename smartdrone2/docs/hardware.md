# Component inventory and reference budget

The FreeCAD model combines a Holybro X500 V2, Khadas Edge2 Basic, XIAO/SX1262 assembly, Lumenier battery and ALLXF camera. The selected reference purchase configuration uses **Pixhawk 6C**; 6X is an alternative kit, not a second controller.

Prices checked **5 October 2026**. USD maker prices are converted with the [ECB reference rate](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), **1 EUR = 1.1204 USD**. They are EUR equivalents, not checkout quotes. The Edge2 retailer price already includes VAT; the other maker import offers do not establish import taxes or shipping. The €9 radio price is the user's approximation.

| Purchase unit | Qty | Reference EUR | Source / scope |
|---|---:|---:|---|
| X500 V2 PX4 kit with Pixhawk 6C / M10 | 1 | €543.56 | [Holybro](https://holybro.com/products/px4-development-kit-x500-v2); includes propulsion and avionics below |
| ALLXF D-80Pro 40x-4K spherical gimbal camera | 1 | €767.58 | [ALLXF](https://allxf.com/product/d-80pro-40x-4k-spherical-gimbal-camera/); GCU inclusion not verified |
| Khadas Edge2 Basic Maker Kit KEG2-B-001 | 1 | €239.95 | [SoundImports](https://www.soundimports.eu/en/khadas-keg2-b-001.html); VAT included, bare-board representation |
| XIAO ESP32S3 + SX1262 | 1 | ~€9 | User-supplied approximation; combined mass unpublished |
| Lumenier NAV 12000mAh 4S Amprius XT60 | 1 | €195.46 | [Lumenier](https://www.lumenier.com/products/lumenier-nav-12000mah-4s-21700-amprius-lithium-ion-battery-xt60); out of stock when checked |

**Reference parts subtotal: approximately €1,756.** Machine calculation is €1,755.55, and the €9 input is approximate. This is not a complete delivered-build quotation. Custom mounts, wiring, charger, unspecified accessories, GCU supply, shipping, import charges and currency fees are excluded. The original CAD's PM06 differs from the current kit's included PM02; no invented extra price is added to reconcile that difference. [parts.json](parts.json) / [parts.csv](parts.csv) preserve quote basis and exact arithmetic.

A direct German seller alternative for the same 6C kit is [MYBOTSHOP €899.95 including 19% VAT](https://www.mybotshop.de/Holybro-X500-V2-ARF-Kit_4), delivery date unknown. That is an alternative to the €543.56 maker conversion, not an extra item. The maker 6X kit equivalent is approximately €686.36; it is not used in this budget.

## Included X500 components

| Included component | Supplied / installed | Published mass used in the scenario |
|---|---|---:|
| X500 V2 frame, plates, carbon tubes, landing gear and fasteners | 1 assembly | CAD volumes with explicitly inferred material densities; published 610 g scope ambiguous |
| AIR2216II KV920 motors | 4 / 4 | 64 ±2 g each, cables included |
| BLHeli S 20A ESCs | 4 / 4 | 21 g each, cables included |
| T1045II 10×4.5 propellers and retainers | 6 / 4 | 12.5 g each flying prop; spare props are not airborne mass |
| Pixhawk 6C plastic | 1 / 1 | 34.6 g |
| PM02 V3 power module, PDB | Included kit | CAD instead represents PM06 V2 at 24 g |
| M10 GPS | 1 / 1 | 32 g V1 manufacturer scenario; exact CAD variant unresolved |
| SiK V3 telemetry | Kit | 23.5 g for the onboard radio; ground unit not airborne mass |

These rows have **no additional purchase cost** beyond the kit. The original CAD labels motor assets KV880, while the sourced propulsion model uses the current kit's KV920 manufacturer table. This is a documented representation difference.

## Payload representation

- **Edge2 Basic:** 8 GB RAM, 32 GB eMMC, 25 g bare board ([Khadas specification](https://dl.khadas.com/products/edge2/specs/edge2_specs.pdf)). Enclosure/cooling/regulated supply are not automatically added to the CAD.
- **ALLXF D-80Pro:** manufacturer pod mass 405 g plus a separately specified 18.6 g GCU; three-axis mechanism, 10× optical plus 4× digital hybrid zoom, 36.1° wide-end vertical FOV ([specification](https://allxf.com/wp-content/uploads/2026/04/D-80Pro-40x-4K-Spherical-Pod-Specifications-1.pdf)). The project locks its third axis and retains the user-defined continuous pan, −61°..+140° tilt and 400 g whole-camera budget. That budget is split 80/180/140 g as a provisional allocation, not a published internal mass distribution. GCU geometry/mass are not included in that user camera budget. Rendering uses the published wide-end FOV; it does not simulate the camera's commercial stabilization electronics, optical zoom or laser module.
- **XIAO/SX1262:** combined unit confirmed by the user; the CAD instance is named `xiao_esp32s3_v3_with_pins`. Its existing 6 g allocation is an explicit installed-board estimate (3–12 g), not a verified combined mass. Product documentation: [Seeed XIAO + Wio-SX1262](https://wiki.seeedstudio.com/wio_sx1262_with_xiao_esp32s3_kit_class/).
- **Lumenier:** manufacturer 465 g, 12 Ah, 14.8 V nominal / 16.8 V full, 177.6 Wh, 36 A continuous. The installed-path simulation limit is 30 A total using the sourced connector/wiring scenario.

Current whole-model mass is approximately **2.066 kg**. Every allocation is recorded in [component_masses.csv](component_masses.csv) and `models/metadata/mass_model.json`. Sourced totals, user values, CAD geometric calculations and provisional settings are identified separately. Full research: [airframe](research/upgrade/findings_airframe.md), [payload](research/upgrade/findings_payload.md), [original mass evidence](flight_model.md).

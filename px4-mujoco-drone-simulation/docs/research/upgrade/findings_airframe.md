# Airframe, propulsion and battery sourcing

Checked 2026-10-05. Five search queries, followed by direct primary store/document reads. Prices are listed offers, not purchased costs.

## EUR cost basis

Use one kit configuration, not a frame plus separately priced included components. The live [Holybro development kit page](https://holybro.com/products/px4-development-kit-x500-v2) lists Pixhawk 6C / M10 / either telemetry frequency at USD 609, available. The 6X alternative is USD 769. An older cached search result still says USD 579; the freshly opened variant JSON and visible price both say 609.

The directly opened [ECB reference page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) is dated **5 October 2026**, with **1 EUR = 1.1204 USD**. Conversion is USD / 1.1204; these EUR equivalents are informational and exclude shipping, import charges, checkout taxes and exchange fees.

| Purchase unit | Quantity | Manufacturer listed USD | EUR equivalent | Availability |
|---|---:|---:|---:|---|
| X500 V2 PX4 development kit, Pixhawk 6C / M10 | 1 | 609.00 | 543.56 | Available; shipping notice says orders processed after Oct 7 |
| Lumenier NAV 12000mAh 4S 21700 Amprius XT60, SKU 23315 | 1 | 218.99 | 195.46 | Out of stock |
| **Airframe + battery subtotal** | | **827.99** | **739.01** | Not a delivered total |

Battery price is from the live [Lumenier manufacturer store](https://www.lumenier.com/products/lumenier-nav-12000mah-4s-21700-amprius-lithium-ion-battery-xt60), not an invented estimate. No verified EUR store offer for this exact battery was found within the scoped search.

Alternative direct EUR seller: [MYBOTSHOP exact Pixhawk 6C kit](https://www.mybotshop.de/Holybro-X500-V2-ARF-Kit_4), **EUR 899.95 including 19% VAT**, shipping additional; goods ordered, manufacturer delivery date unknown. Do not mix this VAT-inclusive offer with the untaxed manufacturer equivalents without stating the different basis. Optional 6X manufacturer equivalent: EUR 686.36; not an extra component to add to the 6C kit.

## What the kit price includes

The selected Holybro development kit includes the X500 V2 frame, Pixhawk 6C plastic controller, PM02 V3, M10 GPS, SiK V3 telemetry, four Holybro 2216 KV920 motors, four BLHeli S 20A ESCs, PDB, and six 1045 propellers with retainers. Four props fly; two are spares. Battery and optional depth-camera mount are separate. Count included components in the BOM for clarity, but assign no additional acquisition cost to them.

## Published physical specifications

The manufacturer-linked [propulsion sheet](https://cdn.shopify.com/s/files/1/0604/5905/7341/files/X500MotorSpec.png?v=1678791632), also inspected from the existing local image, gives:

| Installed item | Count | Published mass each | Scope |
|---|---:|---:|---|
| AIR2216II KV920 motor | 4 | 64 ± 2 g | Cable included |
| BLHeli S 20A ESC | 4 | 21 g | Cable included |
| T1045II propeller | 4 | 12.5 g | 10 × 4.5 inch; sheet dimension 260 × 30 mm |

Installed propulsion subtotal is 390 g, excluding PDB/retainers beyond the listed scopes. The sheet has a measured 16 V thrust/torque/current/RPM table already preserved in the simulator research. It does not provide wind-response or spin-up measurements.

The Lumenier page publishes 465 g, 86 × 42 × 72 mm, 14.8 V nominal, 16.8 V fully charged, 12 Ah / 177.6 Wh, 36 A continuous and 60 A burst, XT60, eight Amprius SA17 cells. Its configuration prose contradicts itself (4S1P alongside two cells in parallel and eight total), so avoid quoting the 4S1P text as verified topology.

## CAD versus current catalog

The existing CAD labels motors KV880; current X500 V2 kit data says KV920. Keep this explicit as CAD appearance versus selected manufacturer's propulsion scenario. Existing power-module CAD is PM06 V2, whereas the selected commercial kit supplies PM02 V3. Do not silently call them identical or change physical masses based on the kit price alone.

Holybro's published 610 g figure has unclear frame/ARF scope; retain that uncertainty. Shipping/package weights must not replace component masses. Exact aggregate mass and the current model's material-derived frame mass remain distinct facts.

Excluded from this subtotal: camera, Edge2 Basic, XIAO/SX1262, custom mounts and wiring, charger, ground controller, tax/import/shipping. Payload sourcing is a separate report.

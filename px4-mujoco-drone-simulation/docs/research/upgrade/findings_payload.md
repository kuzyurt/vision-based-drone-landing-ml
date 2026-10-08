# Payload sourcing — 5 October 2026

## ALLXF D-80Pro 40x-4K

The user confirmed this exact commercial camera and that one of its three axes is locked in the FreeCAD assembly. The existing two-axis CAD mechanism remains the selected project configuration.

| Published item | Manufacturer value |
|---|---|
| Stabilization | Three axes, nonorthogonal mechanism |
| Pod dimensions | 85.8 × 86 × 129.3 mm |
| Pod / separate GCU mass | 405 g / 18.6 g |
| Supply | 14–53 V DC |
| Pod power | 6.7 W average, illumination off; 55 W stall, illumination on |
| GCU power | 1.8 W |
| Pitch / yaw range | −157° to +70° / continuous rotation |
| Maximum commanded pitch/yaw speed | ±200°/s |
| Image / video | 3840 × 2160 / 4K at 30 fps |
| Optical / digital zoom | 10× / 4×, marketed as 40× hybrid |
| Horizontal / vertical FOV | 60.2°–6.6° / 36.1°–3.7° |

Source: [ALLXF specification PDF](https://allxf.com/wp-content/uploads/2026/04/D-80Pro-40x-4K-Spherical-Pod-Specifications-1.pdf), pages 1–3, including visual inspection of the specification table on page 2. [Manufacturer product page](https://allxf.com/product/d-80pro-40x-4k-spherical-gimbal-camera/) lists **USD 860.00**; shipping, taxes and discounts are calculated at checkout. Whether the GCU is included in that purchase is not explicitly established by the retrieved listing.

The user-specified **400 g** simulation budget and **−61° to +140°** CAD tilt range are project choices, distinct from these manufacturer figures. Do not claim a measured internal mass split or a derived equivalence between the two pitch coordinate systems. The third-axis locking arrangement is user-confirmed; no manufacturer locked-axis operating specification was found. Model optics can use the published 36.1° wide-end vertical FOV, while resolution and rendering rate remain simulation settings.

## Khadas Edge2 Basic

The [manufacturer specification PDF](https://dl.khadas.com/products/edge2/specs/edge2_specs.pdf), opened directly, specifies **8 GB LPDDR4X, 32 GB eMMC, 25 g bare board, 82.0 × 57.5 × 5.7 mm**, Rockchip RK3588S2 and a 6 TOPS NPU. The currently retrieved PDF uses RK3588S2; older indexed versions say RK3588S, so record the specification revision rather than asserting which silicon the original CAD represents.

[Khadas product information](https://www.khadas.com/edge2) distinguishes the Maker Kit bare board from the ARM PC with cooling and enclosure. The [manufacturer shop page](https://www.khadas.com/product-page/edge2) shows a generic “From USD 339.00” without a selected Basic variant; that amount cannot safely be assigned to the requested Basic board.

An exact matching **Edge2 Maker Kit Basic, KEG2-B-001**, is listed at **€239.95 including VAT / €198.31 excluding VAT** by [SoundImports](https://www.soundimports.eu/en/khadas-keg2-b-001.html). This is the retailer’s own price offer; technical specifications above come from Khadas. Two units are shown in stock in the retrieved listing, though stock is not a project guarantee. Price does not establish inclusion of additional drone power conversion, cooling, cables or mounting hardware. The CAD board and 25 g mass correspond to the bare-board representation, not the enclosed ARM PC.

## XIAO ESP32S3 + SX1262

Use **approximately €9**, explicitly attributed to the user, for the combined radio/processor entry. The user confirms the SX1262 module is part of this board assembly. No independently verified purchasing SKU or combined mass was provided; do not turn a previous estimated electronics mass into a manufacturer claim.

## EUR conversion

The directly opened [ECB reference-rate page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) is dated **5 October 2026** and quotes **1 EUR = 1.1204 USD**. This supersedes the older search-index result dated 30 September. Conversion is USD ÷ 1.1204; **USD 860.00 = approximately €767.58**. ECB rates are informational, so this is a sourced currency conversion, not a checkout quotation. Import VAT, duties, shipping, payment conversion charges and unknown kit accessories are excluded. All final presentation prices should remain in EUR; the source currency/rate can stay in the detailed ledger for reproducibility.

The payload subtotal for camera, bare Edge2 Basic Maker Kit and user-priced XIAO/SX1262 is **approximately €1,016.53**, with mixed tax treatment: camera import taxes unknown, Edge2 retailer VAT included, XIAO user estimate. It must not be labeled a landed purchase total.

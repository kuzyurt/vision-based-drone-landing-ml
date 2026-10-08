# Payload and avionics mass evidence

Research date: 2026-10-05. Manufacturer specifications are nominal product masses, not measurements of the user's installed hardware. Five search queries were used, followed by opening the maker specifications linked in the results.

| Component / variant | Nominal mass | Evidence status and usage |
| --- | ---: | --- |
| Lumenier NAV 12000mAh 4S 21700 Amprius Li-ion, XT60 | 465 g | Published product specification; matches the CAD label 0.465 kg. Use 0.465 kg as the whole pack mass, without adding cell/wrapper mass again. Confirm exact pack variant physically. |
| Khadas Edge2 PCB, Basic or Pro | 25 g | Khadas specification PDF states Board Weight 25 g. CAD root EDGE2_PCBA_3D_V11_220607_ASM identifies PCB assembly. Use 0.025 kg for all its board/component geometry together. |
| Seeed XIAO ESP32S3, with soldered headers | Unknown | No physical mass in the reviewed Seeed product page or wiki. Headers are not included by default. An installed board plus headers, antenna and wiring needs weighing; no nominal shipping mass should be substituted. |
| Pixhawk 6C plastic case | 34.6 g | Holybro published mechanical specification. Current X500 V2 PX4 kit identifies this variant. |
| Pixhawk 6C aluminum case | 59.3 g | Holybro published alternative; use only if that case is installed. |
| Holybro PM02 V3 | 20 g | Holybro comparison chart; current X500 V2 kit pairs this analog module with the Pixhawk 6C. |
| Holybro PM06 V2 | 24 g | Holybro product mechanical specification and comparison chart. Compatible analog alternative for Pixhawk 6C, but not the power module listed in the current stock X500 V2 kit. |
| Holybro M10 / M9N GPS V1 | 32 g | Maker product mechanical table, diameter 50 mm and height 14.4 mm. Check variant; supplied cable/mount inclusion in this nominal mass is not unambiguously specified. |
| Holybro M9N GPS V2 | 36.8 g | Maker comparison table, diameter 51 mm and height 18.5 mm. M9N page also gives M10 V2 the same value; M10 store page still shows only V1. Match installed variant. |
| Camera + three-part gimbal assembly | 400 g | User-provided assembly total. The mass split between static base, pan xaxis and tilt yaxis is not measured. Preserve exactly 0.400 kg combined. Make the pan xaxis allocation heavier as requested, but record any chosen split as a provisional allocation. |

## Sources

- [Lumenier NAV 12000mAh 4S Amprius pack product specification](https://www.getfpv.com/lumenier-nav-12000mah-4s-21700-amprius-lithium-ion-battery-xt60.html): 465 g; 86 x 42 x 72 mm; 4S2P; 14.8 V nominal; 12.0 Ah; 177.6 Wh; 36 A continuous; 60 A burst. GetFPV is the Lumenier brand's product storefront, and the page identifies Lumenier as manufacturer. The 36 A battery limit is a total pack current limit, not per motor. Voltage sag, usable capacity and current-to-thrust relation remain to be characterized.
- [Khadas Edge2 maker specification PDF](https://dl.khadas.com/products/edge2/specs/edge2_specs.pdf): 25 g bare PCB assembly, 82.0 x 57.5 x 5.7 mm. The fan/heat sink, case and external wires are separate accessories. Do not add an unrepresented cooling kit automatically; physical installed configuration needs confirmation.
- [Seeed XIAO ESP32S3 product page](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) and [Seeed getting-started specification](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/): base board is 21 x 17.8 mm; headers ship unsoldered/not included by default. The reviewed maker material does not publish an installed board mass. Sense/Plus variants differ and should not be used to infer this board's mass.
- [Holybro Pixhawk 6C maker product page](https://holybro.com/products/pixhawk-6c): 34.6 g plastic or 59.3 g aluminum; 84.8 x 44 x 12.4 mm. Ignore embedded Shopify variant `weight` fields (e.g. 300 g): these are shop/logistics metadata, not the product mechanical masses. The controller runs PX4 preinstalled, but hardware identity alone does not reproduce its firmware's controller, estimator, sensor timing or motor-output processing.
- [Holybro power-module comparison](https://docs.holybro.com/power-module-and-pdb/power-module-comparison): PM02 V3 20 g, PM06 V2 24 g; both analog modules suitable for Pixhawk 6C. Pixhawk 6X requires compatible digital module instead.
- [Holybro PM06 V2 mechanical specification](https://holybro.com/collections/power-modules-pdbs/products/micro-power-module-pm06-v2): 24 g, 35 x 35 x 5 mm. Board current rating 70 A continuous/120 A burst; the provided XT60 and 12AWG wire rating is lower, 30 A continuous/60 A burst (<60 s). Do not model 70 A as permission for sustained draw through the supplied wiring.
- [Holybro M9N GPS](https://holybro.com/collections/standard-gps-module/products/m9n-gps) and [M10 GPS](https://holybro.com/collections/gps/products/m10-gps): 32 g V1, 36.8 g V2 in M9N comparison. Avoid the storefront's 120 g logistics field.
- [Holybro current X500 V2 PX4 development kit contents](https://holybro.com/products/px4-development-kit-x500-v2): Pixhawk 6C plastic plus PM02 V3, or Pixhawk 6X with digital PM02D; M10 GPS, SiK radio, 2216 KV920 motors, BLHeli S 20 A ESCs, 1045 props, separate PDB. The listed frame mechanical weight is 610 g, but its page does not unequivocally define whether motors/ESCs are included in that figure. Avoid blindly adding 610 g to a second mass estimate for all frame/mechanical components.

## What requires measurement before real-flight calibration

- Ready-to-fly total mass and center of gravity, with battery, camera, computer, headers, wires, fasteners and any unrepresented hardware.
- Actual three camera/gimbal subassembly masses; CAD-volume weighting cannot identify hidden camera electronics, motor winding and material density accurately.
- Installed XIAO with headers/antenna, custom mounting plate, mounts, cables and power regulators.
- Variant identification for Pixhawk, power module and GPS. The CAD may be an older kit than the current product listing.
- Moments of inertia, motor/propeller thrust and torque versus speed and supply voltage, motor lag, propeller inertia, battery sag, aerodynamic drag, actuator friction and limits. Published mass totals alone do not validate these quantities or demonstrate that a policy trained in simulation transfers to the hardware.

Use explicit whole-assembly mass budgets so that several CAD meshes representing one board or pack do not each receive the full board/pack mass. Published totals constrain the complete group; any division among its individual visual meshes is a modeling allocation and must be labelled accordingly.

# Flight model research plan

Question: Build a source-traceable Holybro X500 V2 flight model in MuJoCo, using the existing FreeCAD assembly, owner-specified 400 g gimbal camera, 12,000 mAh Lumenier battery, and onboard electronics, with realistic rotor mechanics and PX4 control integration.

1. Airframe and propulsion: Holybro X500 V2 exact empty/ready-to-fly mass definitions, supplied motors/ESC/props, thrust data, maximum takeoff mass and flight controller variants. Establish a mass budget without double-counting a kit specification.
2. Payload and electronics: official weights for Lumenier NAV 12,000 mAh 4S Amprius battery, Khadas Edge2/VIM variants visible in CAD, Seeed XIAO ESP32S3, flight controller/power module and common 10x4.5 props. Mark exact versus approximate and unresolved identities.
3. Flight control and simulator interface: official PX4 multicopter controller structure and custom simulator/SITL integration (MAVLink HIL sensor/GPS/actuator messages, coordinate frames, time handling). Determine whether PX4 can run locally and what can be independently validated.

Each research agent uses 3–5 searches maximum, prefers manufacturer documentation and source repositories, and writes facts with URLs to a separate findings file. Synthesis will produce a component mass manifest with source/status fields, physical parameters and documented calibration gaps. Geometry grouping and mass/inertia aggregation must retain the verified source transforms. Render a live onboard feed, independent scene view, and keyboard controls.

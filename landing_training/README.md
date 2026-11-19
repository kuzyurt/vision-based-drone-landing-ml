# Landing a drone on a moving boat

A quadrotor has to find a moving boat up to 100 m away and land on a 60 cm pad
on its deck. The boat keeps driving, waves tilt the deck, wind pushes the drone,
and other boats nearby can look like the target. Everything is trained in
simulation, with the real PX4 autopilot flying the drone.
[Watch it land](../website/assets/hero.mp4).

![The drone's path from search to touchdown](../docs/media/landing-flow.png)

## How it works

The drone has one camera that can turn and tilt. Everything it knows comes from
that camera and its own sensors. The boat can also send its GPS position by
radio, but the drone can land without it.

Three neural networks do the seeing, and none of them flies. They report what
they see, and control code decides how to move and sends the commands to the
PX4 autopilot.

**The search head** (about 45,000 parameters) answers one question: is the
target boat in the picture? It looks at the camera image and marks every boat
it finds on a coarse grid, labelling each one as the target, similar to the
target, a different boat, or not yet recognisable.

**The pad finder** (also about 45,000 parameters) looks only at the image and
marks the single point where it thinks the landing pad is, together with how
sure it is that the pad is in view. The control code turns the camera to keep
that point in the middle of the picture, so the pad stays in sight on the way
in. The search head was built from the same design and started from its
weights.

**The main network** (about 1.55 million parameters) tracks the pad during the
landing. Each frame it gets the camera image, the drone's own state including where the
camera is pointing, and a short memory of the previous frames. It answers:
where is the pad relative to the drone, and how is the deck moving? All three
share the same image processing, so the two small ones add very little extra
work.

**Finding the boat.** With radio, the drone flies straight towards the boat's
position and hands over once the search head has marked the target in four
frames in a row, at the place the radio reports. Without radio, it climbs to
about 7 m and turns on the spot. On the first turn it only goes after boats
that look like the target. If that finds nothing, it turns again and also flies
towards boats it can't recognise yet, to get a closer look.

**Precision landing.** Once the target is confirmed, the pad finder and the
main network take over. The control code keeps the camera on the pad finder's
point and the drone above the pad, moving with the boat. In the last few metres
the camera also measures the printed pattern on the pad directly. From then on
that measurement leads, and the drone only keeps descending while it is fresh.

**Why the networks don't fly.** A first version did, copying a teacher's
commands, and landed in none of its 12 test flights. Every small mistake changed
what it saw next, and the errors kept growing.

## How it was trained

The teacher is a pilot that can see everything in the simulator, including
exactly where every boat and the pad are. It flew the demonstration flights,
and its knowledge became the labels. The networks themselves only ever get what
a real drone would have: the camera image and its own sensor readings.

The main network and the pad finder were trained first. The search head came
later, from 60 recorded flights, 45 of them with decoy boats. 48 were used for
training and 12 were held back to check the result. The other two networks
stayed frozen the whole time, so training the search head could not change how
they see the pad.

![Missions landed by each version of the design](../docs/media/training-story.png)

Each bar is one version of the design. The first was tested on its own 12
flights, the others on the 20-mission benchmark below. The version that
depended on the radio landed none of the six missions flown without it. The
camera-first version landed only half of the search missions, and adding the
search head fixed that.

## Results

Every version flies the same 20 missions: boats up to 1.5 m/s, 4 m/s
crosswind, waves, searches from 100 m and decoy boats. A landing only counts if
the drone ends up disarmed and stable on the pad.

| Policy | Score | Landed |
|---|---:|---:|
| Teacher (sees the simulator's ground truth, sets the ceiling) | 99.2 | 20 / 20 |
| With search head, camera only (8 Nov) | 87.8 | 18 / 20 |
| Camera first, no search head | 57.5 | 11 / 20 |
| Radio-dependent (15 Oct) | 54.9 | 7 / 20 |

The same networks also fly in [Tidewater](../tidewater-game/README.md), a
browser game whose graphics they never saw during training. The version there
adds the radio approach described above and ignores sun glare on the water.
Its browser build currently leaves the pad finder out and uses the main
network's own estimate of where the pad is. In one recorded session the drone
started 122 m from a stationary boat with the radio switched off and landed on
the pad.

## What does not work yet

- The two missions that throw everything at once: wind, waves, a 100 m search
  and decoys. In one, the drone never confirmed the right boat and gave up when
  its time ran low. In the other, it got to 30 cm above the pad, lost the pad
  from view and hit the boat.
- The radio approach from Tidewater has not been run through the full
  benchmark yet, so the table is camera only.
- It has only flown in simulation, never on real hardware.

## Go deeper

| Question | Read |
|---|---|
| How are the networks built and what exactly do they output? | [Architecture and training details](docs/ARCHITECTURE.md) |
| How are the 20 missions defined and scored? | [Benchmark](../benchmark/README.md) |
| How was the search head trained? | [Search training run](../training_runs/search_revision_20261025/README.md) |
| Where is the code? | [Source map](docs/SOURCE_MAP.md) |

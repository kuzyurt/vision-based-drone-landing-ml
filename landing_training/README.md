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

Two neural networks do the seeing, and neither of them flies. They report what
they see, and control code decides how to move and sends the commands to the
PX4 autopilot.

**The search head** (about 45,000 parameters) answers one question: is the
target boat in the picture? It marks every boat it finds on a coarse grid of
the image, labelling each one as the target, similar to the target, a
different boat, or not yet recognisable. It reuses the main network's image
processing, so it adds very little extra work.

**The main network** (about 1.55 million parameters) tracks the pad during the
landing. Each frame it gets the camera image, the drone's own state including
where the camera is pointing, and a short memory of the previous frames. It
answers: is the pad in view, where is it in the picture, where is it relative
to the drone, and how is the deck moving?

**Finding the boat.** With radio, the drone flies straight towards the boat's
position and hands over once the search head has marked the target in four
frames in a row, at the place the radio reports. Without radio, it climbs to
about 7 m and turns on the spot. On the first turn it only goes after boats
that look like the target. If that finds nothing, it turns again and also flies
towards boats it can't recognise yet, to get a closer look. If it loses a boat
it was just looking at close by, it tilts the camera further down for one
turn, because from 7 m up the normal search view only starts about 15 m out.

**Precision landing.** Once the target is confirmed, the main network takes
over. The control code turns the camera to keep the pad in the middle of the
picture and holds the drone above it, moving with the boat. In the last few
metres the camera also measures the printed pattern on the pad directly. From
then on that measurement leads, and the drone only keeps descending while it
is fresh.

**Why the networks don't fly.** A first version did, copying a teacher's
commands, and landed in none of its 12 test flights. Every small mistake changed
what it saw next, and the errors kept growing.

## How it was trained

The teacher is a pilot that can see everything in the simulator, including
exactly where every boat and the pad are. It flew the demonstration flights,
and its knowledge became the labels. The networks themselves only ever get what
a real drone would have: the camera image and its own sensor readings.

The main network was trained first, together with a third small network, the
pad finder, which marked one point on the pad so the camera could stay on it.
The search head came later. It was built from the pad finder's design, started
from its weights, and was trained on 60 recorded flights, 45 of them with decoy
boats. 48 were used for training and 12 were held back to check the result. The
other networks stayed frozen the whole time, so training the search head could
not change how they see the pad.

The final version leaves the pad finder out. The main network already reports
where the pad is in the picture, and without the pad finder the drone still
landed 18 of the 20 benchmark missions.

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
| **Final version** (search head and main network) | **79.9** | **18 / 20** |
| With search head and pad finder, camera only (8 Nov) | 72.8 | 18 / 20 |
| Camera first, no search head | 47.5 | 11 / 20 |
| Radio-dependent (15 Oct) | 44.4 | 7 / 20 |

The final version uses the boat's radio in the missions that offer it; the
8 November version was flown with the radio blocked everywhere. Both land 18
of 20. The final version scores higher because it lands one of the two
missions that combine everything, which weigh the most; it loses one wave
mission, which ran out of time.

The final version also flies in a [realistic browser game](../tidewater-game/README.md)
whose ocean, light and boats the networks never saw during training. There it
also ignores sun glare on the water. In recorded sessions with the radio
switched off, it found the boat and landed on the pad from 122 m away, and
from 15 m with the boat behind it.

## What does not work yet

- Two missions with waves, one of them also with wind, a 100 m search and
  decoys. The drone reaches the pad and stays right above it, but for the last
  half metre it waits for a fresh measurement of the pad while the deck is
  nearly steady. In these two missions that moment did not come often enough
  before the time limit.
- The final version has been flown on the benchmark once. One run is not a
  success rate.
- It has only flown in simulation, never on real hardware.

## Go deeper

| Question | Read |
|---|---|
| How are the networks built and what exactly do they output? | [Architecture and training details](docs/ARCHITECTURE.md) |
| How are the 20 missions defined and scored? | [Benchmark](../benchmark/README.md) |
| How was the search head trained? | [Search training run](../training_runs/search_revision_20261025/README.md) |
| Where is the code? | [Source map](docs/SOURCE_MAP.md) |

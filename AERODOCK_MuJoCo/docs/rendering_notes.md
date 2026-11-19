# Rendering

The boat is drawn with MuJoCo's classic renderer. The goal is a believable
picture at low cost; the water's motion comes from the force model in
[physics_notes.md](physics_notes.md), not from the image.

## Water

The water is one flat plane (`water_surface` in
[`models/boat.xml`](../models/boat.xml)) with a seamless animated texture of
256 × 256 pixels. About ten times a second,
[`usv/rendering.py`](../usv/rendering.py) paints a new frame of ripples
(their roughness follows the wave height) and uploads it to the GPU with
`mjr_uploadTexture`. The texture repeats in metres (`texuniform`), so it does
not stretch over a large world. Two thin wake strips behind the propellers
fade in with propeller speed.

Because the surface stays flat, it cannot show wave silhouettes or breaking
water; the boat still heaves, pitches and rolls because the force model moves
it. Planar reflections and shadows are off to keep the cost predictable. The
classic renderer has no custom water shader and no normal maps, so the effect
is done with colour animation only.

## The model as drawn

Every CAD solid is exported as its own named mesh, internal parts included,
and listed in [`models/manifest.json`](../models/manifest.json). The visual
meshes take no part in collisions; MuJoCo would use their convex hulls, so
collisions use separate shapes such as `hull_contact`. Exterior parts get
textures projected at a fixed physical scale per triangle, so patterns do not
stretch; interior parts keep plain colours. Geom groups separate what each
view shows: internals, optical parts (lens covers, camera windows) and helper
geometry can be hidden per view.

## Onboard cameras

Two cameras are attached to the hull and move with it. MuJoCo cameras look
along their local −Z axis. Both use a 67.7° vertical field of view, which on a
16:9 image matches the lens's roughly 100° horizontal view from the CAD
specification.

| Camera | Position (m, boat frame) | Looks at |
|---|---|---|
| `NavigationCamera` | (1.06, 0, 0.666) | the route ahead |
| `DockCamera` | (0.89, 0, 1.15) | down and back onto the landing bay |

When rendering the onboard views, the optical parts are hidden, because a CAD
lens surface right at the camera centre would otherwise block the view. The
near clipping plane is 0.5 mm for the onboard views (`znear` is given as a
fraction of the model extent, here 3 m) and 2 cm for the overview; the far
plane is 200 m with fog from 90 m.

## Scenery

[`usv/world_render.py`](../usv/world_render.py) keeps the world's low-poly
scenery in a cache and only hands a local radius around the boat to the
renderer (380 m by default). Terrain patches are tiled in metres, and distant
objects are drawn as a single silhouette.

## Web streaming

The browser station ([`usv/server.py`](../usv/server.py)) runs the simulation
and every OpenGL call on one dedicated thread, because MuJoCo's Python renderer
must stay on the thread that owns its context. HTTP requests only queue
commands and read the latest cached frames. One 960 × 540 renderer is reused in
turn for the overview (12 fps) and the two onboard cameras (6 fps), and frames
are sent as JPEG.

`mjr_uploadTexture` is reached through the renderer's private
`_mjr_context` and `_gl_context` fields. That works with the pinned MuJoCo
version; a MuJoCo update may need this one function adjusted.

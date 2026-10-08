# Efficient flat water and MuJoCo rendering research

Research completed 2026-10-07. Four targeted searches; primary MuJoCo documentation/source only. This is the rendering subtopic of the parent research plan.

## Recommendation

Use the classic MuJoCo renderer with one visual-only water plane and a seamless animated RGB texture. Keep water geometry perfectly flat and apply waves through the separate force model. A small vectorized 256 or 512 pixel texture updated at 8–15 Hz should give the requested inexpensive moving water appearance. Combine two directional ripple bands, slow broad color variation, and restrained light streaks. These resolution/rate choices are implementation recommendations, not a measured performance claim.

Update model.tex_data and call mjr_uploadTexture(model, context, texture_id), which explicitly overwrites the GPU texture. The water tile update must use the active rendering context; it must not run at the physics tick rate. The official overview supports runtime texture updates for dynamic effects. [Texture assets](https://mujoco.readthedocs.io/en/stable/overview.html#texture), [texture upload API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mjr-uploadtexture).

For predictable cost, disable planar reflections by default and use a painted impression of glints. Rendering true reflection draws boat geometry again. Classic rendering does not provide a user water shader or PBR normal-map shading through MJCF. Normal-map material layers are intended for advanced renderers; they should not be advertised as working in the classic renderer. Use color animation rather than a purported classic normal-map effect. [Materials](https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-material).

## Geometry completeness

MuJoCo visualizes the original triangles, including non-convex meshes, but collision uses their convex hull. Export every CAD solid as a named mesh geom; retain internal parts too. Set visual meshes contype=0 and conaffinity=0, provide explicit body inertias, and add separate collision shapes only where needed. These collision approximations do not replace or omit the full visual model. Maintain a manifest mapping every CAD object to one or more geoms, including compound solids. Avoid discardvisual=true. Export OBJ with normals/UVs where textures are needed; binary STL is adequate for untextured parts. [Mesh behavior](https://mujoco.readthedocs.io/en/stable/overview.html#mesh), [original mesh drawing source](https://github.com/google-deepmind/mujoco/blob/main/src/render/classic/render_context.c).

Use only exterior material textures. For square texel density on exterior triangles, my recommended exporter projects each triangle onto an orthonormal face basis at consistent physical scale and duplicates vertices at texture seams. This prevents stretching at the cost of visible seams on patterned textures; fine, seamless paint/rubber textures minimize those seams. Leave interior geoms as solid colors. A water plane can use texuniform=true with texrepeat to specify repeats per spatial unit; OBJ textured meshes need explicit UV coordinates. [Texture coordinate and tiling reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-material).

## Exact onboard cameras

Keep CAD axis convention +X forward, +Z up, convert millimeters to meters. Attach cameras to the hull body so they follow its motion. MuJoCo cameras look along local -Z, with +X right and +Y up. These positions are verified directly in the delivered CAD macro:

| Camera | Lens center in CAD coordinates, meters | Looking toward | Suggested xyaxes |
| --- | --- | --- | --- |
| Navigation | (2.260, 0, 0.666) | (2.400, 0, 0.666) | 0 -1 0 0 0 1 |
| Dock | (2.090, 0, 1.150) | (1.160, 0, 0.810) | 0 1 0 -0.34337 0 0.93920 |

Use fovy=67.7 with a 16:9 rendered image, matching the CAD lens specification of approximately 100 degrees horizontal. If the hull origin is recentered, subtract the identical offset from camera positions and targets. These numeric transforms are my calculations from the local macro, not manufacturer lens calibration.

Keep lens/window geoms in the export, but place optical surfaces in a dedicated render group and disable that group in onboard camera rendering. At the exact lens center, opaque CAD lens surfaces or tinted windows ahead of the camera otherwise obstruct the simulated view. The overview should retain those optical parts.

## Near clipping

znear must be positive and its metric distance is znear times model.stat.extent. Explicitly set extent=3 meters and znear=0.0001666667 for about 0.5 mm; do not use zero. Keep zfar bounded to the visible water scene rather than miles of distance. A very small near plane reduces depth precision, so outward trim thickness and bounded far clipping still matter. [Clipping settings](https://mujoco.readthedocs.io/en/stable/XMLreference.html#visual-map).

## Web camera streaming

Keep the OpenGL context, texture upload, camera scene update, and render calls on one dedicated worker thread. HTTP handlers should enqueue commands and read cached frames; they should never call the renderer concurrently. The Python docs require subsequent rendering calls on the same thread as the current context. Named model lookup is O(1). [Python rendering/thread rules](https://mujoco.readthedocs.io/en/stable/python.html#rendering).

The native Renderer update_scene accepts camera names, and render returns an RGB NumPy image. Its framebuffer size must be at least the selected output resolution. Reuse one renderer sequentially for overview and both onboard views, encode bounded-resolution JPEGs, cache them, and render only subscribed viewpoints. Start with 640x360 at 10–15 Hz; this is a suggested budget. PNG lossless streaming and rendering all cameras at physics frequency would waste work. [Official renderer source](https://github.com/google-deepmind/mujoco/blob/main/python/mujoco/rendering/classic/renderer.py).

For texture upload with the high-level Renderer, its _mjr_context and _gl_context are private implementation fields. Prefer a small wrapper owning public GLContext/MjrContext APIs if long-term compatibility matters; otherwise pin the tested MuJoCo version and isolate those accesses in one compatibility method. With a passive native viewer, the documented viewer.update_texture(texture_id) offers a public texture refresh path. [Python viewer](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer).

## Limits

The flat image surface cannot show displaced silhouettes or accurate breaking waves. It can show animated ripples, glints, and wakes efficiently. Separately computed wave forces can still move the boat in heave, pitch, roll and yaw. The result should be described as a reduced-order water/boat simulation with inexpensive visual water, rather than computational fluid dynamics.

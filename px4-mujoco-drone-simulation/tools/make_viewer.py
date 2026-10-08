"""Build the interactive three.js viewer for smartdrone2.

Reads ``models/metadata/export.json`` and ``models/metadata/materials.json`` and writes
``web/inspection/index.html`` plus a metadata JSON and bounded binary chunks.

Geometry handling
    One mesh is emitted **per part**, not merged per body.  A body here holds
    80-odd parts that need different materials - carbon weave, bare aluminium,
    black cover, blue battery - and a merged mesh would force one material on the
    whole body.  85 meshes is nothing for three.js, and it makes per-part colour
    and per-part texture trivial.

    Vertices are welded and then quantised to 16 bits inside each part's own
    bounding box, which is where the saving comes from: an unwelded CAD
    tessellation repeats every corner of every triangle face, so welding alone
    cuts the position buffer roughly fivefold.  Normals and UVs are derived in
    the browser from the welded mesh, which keeps a third of the payload off the
    wire.

Textures
    Drawn procedurally on a canvas in the page, so the viewer ships no image
    files: a 2x2 twill carbon weave, a matte grey and a brushed grey.

Joint limits
    Every joint has a slider over its current range **and** two editable limit
    fields.  "Download limits" writes ``joint_limits.json``; "Copy limits" puts
    the same JSON on the clipboard.  ``make_mjcf.py`` reads that file, so the
    angles can be set here and land in the physics model unchanged.
"""

from __future__ import annotations

import base64
import json
import math
import os
import struct
from packed_geometry import write_packed_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER = os.path.join(ROOT, "web", "inspection")
DATA = os.path.join(VIEWER, "data")
VENDOR = os.path.join(VIEWER, "vendor")

#: three.js is vendored rather than loaded from a CDN, so the viewer keeps
#: working with no network.  three 0.186 ships three.module.js plus the
#: three.core.js it imports, and OrbitControls imports the bare specifier
#: "three", which the page's import map resolves.
THREE_LOCAL = os.path.join(VENDOR, "three.module.js")
THREE_CORE = os.path.join(VENDOR, "three.core.js")
ORBIT_LOCAL = os.path.join(VENDOR, "OrbitControls.js")
VENDOR_REQUIRED = (THREE_LOCAL, THREE_CORE, ORBIT_LOCAL)

#: Vertices closer than this (mm) are the same vertex.
WELD_MM = 0.02


def unique_parts(parts):
    """Suppress identical motor instances that overlap in the original CAD."""
    seen = set()
    for part in parts:
        q = part.get('quaternion_xyzw', [0, 0, 0, 1])
        sign = next((1 if v > 0 else -1 for v in reversed(q) if abs(v) > 1e-8), 1)
        key = (part.get('target', part['part']),
               *(round(v, 6) for v in part.get('placement_mm', [0, 0, 0])),
               *(round(v * sign, 8) for v in q))
        if key in seen:
            continue
        seen.add(key)
        yield part


def check_vendor() -> None:
    """Fail with an actionable message if three.js has not been vendored."""
    missing = [p for p in VENDOR_REQUIRED if not os.path.exists(p)]
    if missing:
        names = ", ".join(os.path.basename(p) for p in missing)
        raise SystemExit(
            f"three.js is not vendored ({names} missing).\n"
            f"Run:  cd viewer && npm pack three@0.186.1 && "
            f"tar -xzf three-0.186.1.tgz\n"
            f"      cp package/build/three.module.js package/build/three.core.js "
            f"package/examples/jsm/controls/OrbitControls.js vendor/")


def read_obj(path: str):
    """Return ``(vertices, triangles)`` from an OBJ, vertices as (x, y, z)."""
    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                # Faces may be polygons; fan-triangulate them.
                parts = line.split()[1:]
                idx = []
                for token in parts:
                    first = token.split("/")[0]
                    index = int(first)
                    idx.append(index - 1 if index > 0 else len(vertices) + index)
                for k in range(1, len(idx) - 1):
                    triangles.append((idx[0], idx[k], idx[k + 1]))
    return vertices, triangles


def pack_part(path: str) -> dict:
    """Weld and quantise one part's mesh into a compact block."""
    vertices, triangles = read_obj(path)
    if not vertices or not triangles:
        return {"vertices": 0, "triangles": 0, "blob": b"", "lo": [0, 0, 0],
                "hi": [1, 1, 1]}

    step = WELD_MM
    table: dict[tuple[int, int, int], int] = {}
    out: list[tuple[float, float, float]] = []
    remap = [0] * len(vertices)
    for i, (x, y, z) in enumerate(vertices):
        key = (round(x / step), round(y / step), round(z / step))
        found = table.get(key)
        if found is None:
            found = len(out)
            table[key] = found
            out.append((x, y, z))
        remap[i] = found

    lo = [min(v[i] for v in out) for i in range(3)]
    hi = [max(v[i] for v in out) for i in range(3)]
    span = [max(hi[i] - lo[i], 1e-6) for i in range(3)]
    scale = [65535.0 / span[i] for i in range(3)]

    flat: list[int] = []
    for x, y, z in out:
        flat.append(int(round((x - lo[0]) * scale[0])))
        flat.append(int(round((y - lo[1]) * scale[1])))
        flat.append(int(round((z - lo[2]) * scale[2])))
    positions = struct.pack(f"<{len(flat)}H", *flat)
    indices = struct.pack(
        f"<{len(triangles) * 3}I",
        *(v for t in triangles for v in (remap[t[0]], remap[t[1]], remap[t[2]])))

    # Six bytes per vertex, so the position block is only 4-byte aligned when
    # the vertex count is even.  A browser cannot take a Uint32Array view at an
    # unaligned offset, and every later part's block would inherit the skew, so
    # the padding is applied here and its length shipped with the part.
    pad = (-len(positions)) % 4
    blob = positions + b"\x00" * pad + indices
    return {"vertices": len(out), "triangles": len(triangles),
            "blob": blob, "pos_bytes": len(positions) + pad, "lo": lo, "hi": hi}


def build() -> dict:
    with open(os.path.join(ROOT, "models", "metadata", "export.json"), encoding="utf-8") as h:
        export = json.load(h)
    with open(os.path.join(ROOT, "models", "metadata", "materials.json"), encoding="utf-8") as h:
        materials = json.load(h)

    os.makedirs(DATA, exist_ok=True)
    check_vendor()

    blocks: dict[str, dict] = {}
    parts_payload = []
    total_tri = 0
    for part in unique_parts(export["parts"]):
        name = part["part"]
        if not part.get("facets"):
            continue
        obj = os.path.join(ROOT, "models", "meshes", f"{name}.obj")
        if not os.path.exists(obj):
            continue
        packed = pack_part(obj)
        if not packed["vertices"]:
            continue
        blocks[name] = packed
        total_tri += packed["triangles"]
        assign = materials["assignments"].get(name, {})
        parts_payload.append({
            "name": name,
            "label": part["label"],
            "body": part["body"],
            "rgb": assign.get("rgb", [0.7, 0.7, 0.7]),
            "texture": assign.get("texture"),
            "roughness": assign.get("roughness", 0.5),
            "metallic": assign.get("metallic", 0.0),
            "tint": assign.get("tint"),
            "remote": bool(assign.get("remote")),
            "source_bbox_mm": part.get("world_bbox_mm"),
            "lo": [round(v, 4) for v in packed["lo"]],
            "hi": [round(v, 4) for v in packed["hi"]],
            "vertices": packed["vertices"],
            "triangles": packed["triangles"],
            "pos_bytes": packed["pos_bytes"],
        })

    # All geometry in one buffer, with each part's block described separately so
    # the page can build one geometry per part without a request per file.
    geometry_blob = bytearray()
    for part in parts_payload:
        block = blocks[part["name"]]
        part["offset"] = len(geometry_blob)
        part["byteLength"] = len(block["blob"])
        geometry_blob += block["blob"]

    payload = {
        "model": "smartdrone2",
        "upAxis": export["up_axis"],
        "units": "mm",
        "bodies": export["bodies"],
        "parts": parts_payload,
        "palette": materials["palette"],
        "triangles": total_tri,
        "warnings": export["warnings"],
        "notes": export["notes"],
    }

    write_packed_data(DATA,payload,geometry_blob)
    return {"parts": len(parts_payload), "triangles": total_tri,
            "bodies": len(export["bodies"])}


def write_page() -> str:
    template = os.path.join(VIEWER, "index.html")
    with open(template, "r", encoding="utf-8") as handle:
        html = handle.read()
    target = os.path.join(VIEWER, "index.html")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(html)
    return target


def main() -> int:
    stats = build()
    page = write_page()
    print(f"viewer: {stats['bodies']} bodies, {stats['parts']} parts, "
          f"{stats['triangles']:,} triangles")
    print(f"wrote {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

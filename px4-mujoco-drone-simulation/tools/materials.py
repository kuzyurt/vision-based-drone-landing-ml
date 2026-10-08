"""Per-part material and colour assignment for smartdrone2.

The FreeCAD document stores no material data at all - it has no saved appearance
properties and no material mapping - so every entry here is authored.  Rows
marked ``inferred`` are proposals rather than measured facts, and they are all
in this one file so they can be changed in a single place.

The map covers **every** geometry object in the document.  A completeness check
at the bottom compares the keys against the parts that ``build_corrected.py`` exported
and fails loudly if anything is unassigned, because a part that silently falls
back to a default colour is exactly the kind of gap that is hard to notice in a
rendered scene.

Colours follow the specification given for this model:

* the **battery pack** is blue;
* the **SX1262** (the Xiao ESP32-S3 board) is black;
* the **y-axis camera** is grey and the **x-axis camera** a brighter grey;
* the camera **cover** is black;
* carbon-fibre parts carry a woven carbon texture.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- #
# Palette.  ``texture`` names a procedural texture built in web/inspection/textures.py;
# ``rgb`` is the flat colour used by the MuJoCo model and by the viewer's
# fallback, so the two never drift apart.
# --------------------------------------------------------------------------- #

MATERIALS = {
    "carbon_fibre_plate": {
        "rgb": (0.055, 0.058, 0.065), "texture": "carbon_weave",
        "roughness": 0.42, "metallic": 0.15,
        "density_gcm3": 1.55, "inferred": True,
        "note": "X500 class airframes are carbon plate; the source file states no material",
    },
    "carbon_fibre_tube": {
        "rgb": (0.045, 0.048, 0.055), "texture": "carbon_weave",
        "roughness": 0.38, "metallic": 0.15, "density_gcm3": 1.55,
        "note": "named CARBON-FIBER-TUBE in the model",
    },
    "aluminium": {
        "rgb": (0.72, 0.73, 0.75), "texture": "brushed_grey",
        "roughness": 0.28, "metallic": 0.90, "density_gcm3": 2.70, "inferred": True,
    },
    "aluminium_matte": {
        "rgb": (0.52, 0.53, 0.55), "texture": "brushed_grey",
        "roughness": 0.52, "metallic": 0.75, "density_gcm3": 2.70, "inferred": True,
    },
    "steel": {
        "rgb": (0.45, 0.46, 0.48), "texture": None,
        "roughness": 0.22, "metallic": 0.95, "density_gcm3": 7.85,
    },
    "stainless": {
        "rgb": (0.62, 0.63, 0.65), "texture": None,
        "roughness": 0.18, "metallic": 0.95, "density_gcm3": 7.80,
    },
    "nylon": {
        "rgb": (0.86, 0.85, 0.80), "texture": None,
        "roughness": 0.65, "metallic": 0.0, "density_gcm3": 1.14, "inferred": True,
    },
    "eva_foam": {
        "rgb": (0.09, 0.09, 0.10), "texture": None,
        "roughness": 0.90, "metallic": 0.0, "density_gcm3": 0.25, "inferred": True,
        "note": "JIAO-EVA: EVA foam gasket between frame plates",
    },
    "tpu": {
        "rgb": (0.16, 0.17, 0.19), "texture": None,
        "roughness": 0.82, "metallic": 0.0, "density_gcm3": 1.20,
        "note": "TP_1R5 is 1.5 mm TPU",
    },
    "copper": {
        "rgb": (0.72, 0.45, 0.20), "texture": None,
        "roughness": 0.25, "metallic": 0.95, "density_gcm3": 8.96,
    },
    "pcb": {
        "rgb": (0.045, 0.150, 0.085), "texture": None,
        "roughness": 0.60, "metallic": 0.0, "density_gcm3": 1.85, "inferred": True,
    },
    "electronics": {
        "rgb": (0.10, 0.11, 0.13), "texture": None,
        "roughness": 0.50, "metallic": 0.20, "density_gcm3": 2.20, "inferred": True,
    },
    # ---- specified by the owner of this model ----
    "battery_blue": {
        "rgb": (0.10, 0.28, 0.56), "texture": None,
        "roughness": 0.68, "metallic": 0.02, "density_gcm3": 2.10,
        "note": "blue colour stated in the part's own label",
    },
    "sx1262_black": {
        "rgb": (0.035, 0.035, 0.038), "texture": None,
        "roughness": 0.70, "metallic": 0.05, "density_gcm3": 2.20,
        "note": "Xiao ESP32-S3 board, specified black",
    },
    "camera_grey": {
        "rgb": (0.42, 0.43, 0.44), "texture": "grey_matte",
        "roughness": 0.48, "metallic": 0.35, "density_gcm3": 2.20,
        "note": "y-axis camera, specified grey",
    },
    "camera_grey_bright": {
        "rgb": (0.62, 0.63, 0.64), "texture": "grey_matte",
        "roughness": 0.44, "metallic": 0.35, "density_gcm3": 2.20,
        "note": "x-axis camera, specified a brighter grey",
    },
    "cover_black": {
        "rgb": (0.025, 0.025, 0.028), "texture": None,
        "roughness": 0.62, "metallic": 0.05, "density_gcm3": 1.20,
        "note": "camera cover, specified black; belongs to the y-axis camera",
    },
    "prop_black": {
        "rgb": (0.06, 0.06, 0.07), "texture": None,
        "roughness": 0.40, "metallic": 0.10, "density_gcm3": 1.55,
        "note": "10x4.5R propeller, one per body with its own tint",
    },
}

#: Per-propeller tints so four identical dark discs stay tellable apart.
PROP_TINTS = {
    "prop_1": (0.85, 0.28, 0.24),
    "prop_2": (0.28, 0.50, 0.90),
    "prop_3": (0.30, 0.78, 0.40),
    "prop_4": (0.92, 0.78, 0.25),
}

# --------------------------------------------------------------------------- #
# Part -> material.  Keys are FreeCAD object names.
# --------------------------------------------------------------------------- #

PART_MATERIAL = {
    # ---- frame ----
    "Solid": "carbon_fibre_plate",        # BOTTOM-PLATE-X500-V5
    "Solid001": "carbon_fibre_plate",     # TOP-PLATE-X500-V5
    "Solid028": "carbon_fibre_plate",     # PYLONS-X500
    "Solid031": "carbon_fibre_plate",     # PLATFORM-PLAT-X500
    "Solid005": "carbon_fibre_tube",      # CARBON-FIBER-TUBE
    "Solid026": "carbon_fibre_tube",      # CARBON-FIBER-TUBE300
    "Solid024": "aluminium",              # JIA-GUAN
    "Solid002": "aluminium",              # JIA-LIANJIE
    "Solid003": "steel",                  # GUAN-CHENG
    "Solid004": "aluminium",              # JIAO-LIANJIE
    "Solid007": "aluminium",              # MAO-JIAO
    "Solid006": "eva_foam",               # JIAO-EVA
    "Solid025": "aluminium",              # HUAN-GUIJIAO
    "Solid027": "aluminium",              # M25-6-CHEN-LIU
    "Solid039": "aluminium",              # M3-16-CHEN-LIU
    "Solid016": "tpu",                    # BAN-DJ-DIAN-F2

    # ---- fasteners ----
    "Solid008": "steel",                  # GB70-M3-25-DING
    "Solid009": "steel",                  # LM-M3-DING
    "Solid010": "steel",                  # GB70-M3-8-DING
    "Solid011": "steel",                  # GB70-M3-21-DING
    "Solid017": "steel",                  # GB70-M25-6
    "Solid018": "steel",                  # GB70-M3-38
    "Solid019": "steel",                  # GB70-M25-12
    "Solid020": "steel",                  # GB70-M25-10
    "Solid023": "steel",                  # GB70-M3-6
    "Solid047": "steel",                  # ZSLM-M3-DING
    "Solid048": "steel",                  # M3-10-PAN-DING
    "Solid021": "aluminium",              # ZSLM-M3-FALAN  (prop adapter)
    "Solid050": "aluminium",              # ZSLM-M25
    "Solid040": "aluminium",              # X500-TAO-XT60
    "Solid041": "nylon",                  # LM-M3-NILONG
    "Solid045": "nylon",                  # NILONGZHU-M3-5
    "Solid046": "nylon",                  # M3-14-PAN
    "Solid049": "nylon",                  # NILONGZHU-M25-5
    "Solid042": "copper",                 # TOU-XT60H-M-14AWG
    "Solid056": "tpu",                    # TP_1R5

    # ---- propulsion ----
    "Solid022": "aluminium",              # DJ-2216-KV880  (motor)
    "Solid051": "prop_black",             # 10x4.5R-front-right
    "Solid052": "prop_black",             # 10x4.5R-front-left
    "Solid053": "prop_black",             # 10x4.5R-back-left
    "Solid054": "prop_black",             # 10x4.5R-back-right

    # ---- avionics ----
    "Solid012": "aluminium",              # HMX5V-GUAN-DINGWEI
    "Solid013": "aluminium",              # HMX5V-ZUO-DJ-MUJU
    "Solid014": "aluminium",              # HMX5V-JIBI-JIA-MUJU
    "Solid015": "aluminium",              # HMX5V-DIGAI-DIANJIZUO-MUJU
    "Solid043": "pcb",                    # PCB-PM06
    "Solid044": "electronics",            # BM06B-WO
    "Solid032": "aluminium",              # GPS-ZHIJIA-ZUO
    "Solid033": "aluminium",              # GPS-ZHIJIA-ZHUANJIETOU
    "Solid034": "electronics",            # GAN-GPSV5-ZHIJIA
    "Solid035": "electronics",            # GPSV5-ZHIJIA-LUOMAO
    "Solid036": "electronics",            # GPSV5-ZHIJIA-TUOPAN
    "Solid037": "camera_grey",            # ZHIJIA-CAMERA-INTEL
    "Solid038": "camera_grey",            # GAI-GUANGLIU  (optical flow)

    # ---- cameras ----
    "CombinedShell": "camera_grey_bright",  # camera-x-axis  (parent stage)
    "Compound001": "camera_grey_bright",    # 7 solids at z=69.2, x-axis group
    "Body002": "aluminium",                 # camera-halte-platte
    "Shell003": "camera_grey",               # camera-y-axis   (child stage)
    "Body004": "cover_black",                # black cover, welded to the y camera

    # ---- battery ----
    "Body005": "battery_blue",             # Lumenier 4S Amprius pack

    # ---- the SX1262 ----
    # FreeCAD renames this object on load, adding _v3_ to the declared name.
    "xiao_esp32s3_v3_with_pins": "sx1262_black",

    # ---- electronics ----
    "Solid058": "electronics",             # BGA1253
    "Solid059": "electronics",             # XPWR
    "Solid060": "electronics",             # BDGAR6S1
    "Solid062": "electronics",             # TS-B017_1
    "Solid063": "electronics",             # TS-B017_2
    "Solid064": "electronics",             # TS-B017_3
    "Solid065": "electronics",             # TS-B017_4
    "Solid066": "electronics",             # TS-B017_5
    "Solid067": "electronics",             # TS-B017_6
    "Solid068": "stainless",               # USB_A_00
    "Solid072": "electronics",             # WI-FI
    "Solid073": "electronics",             # BM04B-SURS-TF
    "Solid074": "stainless",               # TYPE_C_24PSMT
    "Solid075": "stainless",               # FH34SRJ-40S
    "Solid076": "stainless",               # FH34SRJ-30S
    "Solid077": "aluminium",               # ECT818000500
    "Solid078": "electronics",             # BGA169_INAND
    "Solid079": "electronics",             # BGA200

    # ---- unnamed solids, assigned from what they measure ----
    # Solid055  82 x 56 x 1.2 mm plate at the top-plate height: a deck
    "Solid055": "pcb",
    # Solid057   9.2 x 6.8 x 2.8 mm: a small board-level part
    "Solid057": "electronics",
    # Solid061   2.7 x 3.5 x 0.9 mm: tiny, an SMD component
    "Solid061": "electronics",
    # Solid069  18.8 x 5.6 x 12.5 mm, 1266 faces: a fine connector/shell
    "Solid069": "electronics",
    "Solid070": "electronics",
    "Solid071": "electronics",

    # ---- empty compounds in the source: no geometry, kept for completeness ----
    "Compound": "electronics",
    "Compound002": "pcb",
    "Compound003": "pcb",
    "Compound004": "pcb",                  # _231
    "Compound005": "pcb",                  # E2-XIN
}


#: Some links instance an App::LinkGroup rather than a solid, so there is no
#: single source geometry to inherit from.  These are the named sub-assemblies
#: that actually occur, keyed by their FreeCAD object name.
LINK_GROUP_MATERIAL = {
    "LinkGroup": "carbon_fibre_plate",   # HMX5V-ARM-V1_ASM   - arms
    "LinkGroup001": "aluminium",         # HANGER-ZHU_ASM
    "LinkGroup002": "aluminium",         # HANGER_ASM
    "LinkGroup009": "electronics",       # DMIC_3526_1       - digital mic
    "LinkGroup010": "electronics",       # TS-B017_ASM       - sensors
    "LinkGroup014": "electronics",       # 00-C16-STACKING_ASM
}

#: One lookup table over both maps, so resolving a part never has to care which
#: kind of object it points at.
MATERIAL_OF = {**PART_MATERIAL, **LINK_GROUP_MATERIAL}


def material_key(part) -> str | None:
    """The map key for one exported part, or None when nothing resolves."""
    name = part.get("source_object", part["part"])
    if part["type"] != "App::Link":
        return name if name in MATERIAL_OF else None
    target = part.get("target")
    if target in MATERIAL_OF:
        return target
    return None


def build() -> dict:
    """Emit the material map, checking that every exported part is covered."""
    with open(os.path.join(ROOT, "models", "metadata", "export.json"), encoding="utf-8") as h:
        export = json.load(h)

    missing = []
    keys = {}
    for part in export["parts"]:
        key = material_key(part)
        if key is None:
            missing.append(f"{part['part']} ({part['label']})")
        else:
            keys[part["part"]] = key

    if missing:
        raise SystemExit(
            "unassigned parts - every part must have a material:\n  "
            + "\n  ".join(missing))

    used = set()
    for part in export["parts"]:
        used.add(part.get("target") or part.get("source_object") or part["part"])
    unused = sorted(set(PART_MATERIAL) - used)

    assignments = {}
    for part in export["parts"]:
        name = part["part"]
        material = MATERIALS[MATERIAL_OF[keys[name]]]
        assignments[name] = {
            "label": part["label"],
            "body": part["body"],
            "material": MATERIAL_OF[keys[name]],
            "rgb": list(material["rgb"]),
            "texture": material["texture"],
            "roughness": material["roughness"],
            "metallic": material["metallic"],
            "density_gcm3": material["density_gcm3"],
            "tint": PROP_TINTS.get(part["body"]),
            "remote": part.get("remote", False),
        }

    palette = {
        key: {"rgb": list(value["rgb"]), "texture": value["texture"],
              "roughness": value["roughness"], "metallic": value["metallic"],
              "density_gcm3": value["density_gcm3"],
              "inferred": value.get("inferred", False),
              "note": value.get("note", "")}
        for key, value in MATERIALS.items()
    }

    return {"palette": palette, "prop_tints": PROP_TINTS,
            "assignments": assignments, "unused_keys": unused}


def main() -> int:
    payload = build()
    target = os.path.join(ROOT, "models", "metadata", "materials.json")
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    assigned = payload["assignments"]
    textured = sum(1 for a in assigned.values() if a["texture"])
    print(f"materials: {len(assigned)} parts assigned, "
          f"{len(payload['palette'])} materials, {textured} textured")
    print(f"wrote {target}")
    if payload["unused_keys"]:
        print(f"note: keys not present in the export: "
              f"{', '.join(payload['unused_keys'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

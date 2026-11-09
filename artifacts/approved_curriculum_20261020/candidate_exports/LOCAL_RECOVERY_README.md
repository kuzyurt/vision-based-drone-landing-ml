# Local recovery, experimental V39

The new RGB verifier best/latest, original R15 bundle, frozen hybrid controller,
calibration, source manifest, training resume state and known-development restore
fixture are saved locally. They are **experimental, not qualified or installed**.
The VM may disappear without deleting these laptop copies.

`experimental_v39/LOCAL_VERIFIED.json` verifies every archive member.
`experimental_v39/package/LOCAL_RESTORE_CHECK.json` verifies full CPU loading and
inference on16 actual development RGB/telemetry frames. The original Linux
`marker_kernel.so` is retained unchanged. For this laptop a separate Windows DLL
was compiled from the exact same preserved C++/header using installed MinGW.
`native_windows/BUILD_RECEIPT.json` records source/compiler/flags/DLL hashes.
`native_windows/LOCAL_WINDOWS_RESTORE_VERIFIED.json` records12identity frames and
maximum fixed-input action difference4.26e-5 versus VM, tolerance1e-4. This short
replay does not establish flight reliability, browser parity or hardware safety.

Run from repository root:

    python artifacts/approved_curriculum_20261020/restore_windows_v39.py

The isolated restore_dependencies folder supplies h5py3.16; torch/numpy/OpenCV/
scipy come from the laptop Python environment. No production/Tidewater file was
changed. The versioned ZIP remains the untouched Linux recovery package; the
Windows loader selects only the separately compiled matching native library.

Native physical purpose flights are still running at this checkpoint. Read the
later final report before selecting any model. Older rejected checkpoints remain
in immutable backup history and must not be mistaken for qualified replacements.

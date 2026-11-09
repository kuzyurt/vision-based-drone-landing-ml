# Experimental V39 recovery package

Not qualified for production and not installed into Tidewater.
Active runtime: sources/target_learning/expert_adapter_v39.py; original R15
pose and b432 spatial head; new RGB verifier recognizer_best.pt.
The latest resume checkpoint is separate and is not necessarily selected.
Use Python with torch, numpy, OpenCV and scipy. Run python restore_check.py
for an offline CPU loading/input/finite-action check. No rendering or aircraft
commands occur. Fixtures are known MuJoCo development data, not a fresh test.
All files are hash-bound by MANIFEST.json. Native purpose flight outcomes are
still pending at export time. Preserve the final report before any use.

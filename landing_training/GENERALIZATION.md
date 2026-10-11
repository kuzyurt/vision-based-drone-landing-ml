# Frozen-policy visual generalization

This experiment evaluates the selected marker-policy bundle without training, changing weights, or tuning after test outcomes. It adds only an evaluation renderer and runner. Original boat CAD, boat materials, collision geometry, physics, telemetry, PX4, supervisor and landing criteria remain unchanged. Existing recordings, approvals and checkpoints are retained.

The policy is the previously selected `outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json` (SHA-256 8531f4ed7da54d899e40e573b0ed672893da85b2e01137676c70ef5bd057a07f); pose weights SHA-256 795825dec351fc894c9f95b6f9a44120c6f2e12f20c13ceda4e05d237443d42e.

Three unused test scenarios were declared before any outcomes were inspected: test_0489_forward (rock, calm, 1.63 m distance, 5.47 m height); test_0079_forward (island, 15.05 m, 3.67 m/s mean wind, 6.75 cm waves); test_0239_reverse (beach, 37.95 m, reverse, 3.21 m/s mean wind, 8.95 cm waves). Selection used parameters, not teacher success labels. Every condition uses the exact same scenario, seeds, delays and flight budget.

Eight visual conditions each use those three scenarios, for 24 flights: original appearance, green ocean, white ocean, light fog, dense fog, procedural clouds with overcast lighting, rain, and combined green water/fog/clouds/rain. Fog has full linear obscuration at 45 m, 12 m or 25 m respectively. Rain uses 90 or 140 moving camera-space streaks per image; these counts are not calibrated precipitation rates. Clouds are a procedural sky texture with changed diffuse lighting. The experiment does not add rain aerodynamics, wet-surface friction or a calibrated real-weather model.

The changed image reaches the policy before the existing image delay and brightness/blur pipeline. Saved policy_rgb frames contain the exact final RGB passed to the frozen policy. The original-appearance renderer is checked for pixel equality against the original renderer. Native graphics fog distances, boat material invariance and the physics model arrays are checked explicitly. The original approved review establishes the base simulation; it does not claim qualification of these new visual conditions. New outputs have separate visual-extension hashes and are never marked training eligible.

Run on the VM, using a fresh output path:

```bash
export MUJOCO_GL=egl
export LANDING_REUSE_APPROVED_RUNTIME=1
landing_training/.venv/bin/python -B -m landing_training.evaluate_generalization \\
  --bundle landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json \\
  --review landing_training/outputs/diverse_review_20261010T010226Z_93857/bundle \\
  --manifest landing_training/datasets/expert/manifest.json \\
  --output landing_training/outputs/new_generalization \\
  --workers 4 --instance-base 210
```

For one policy-controlled video, add `--names test_0489_forward --conditions combined --video --workers 1` and use another fresh output and PX4 slot. Render only on the VM.

The full matrix plan and results are in `outputs/generalization_20261011/matrix_v1/plan.json` and `report.json`; native traces, camera snapshots and terminal outcomes are retained under each condition. Baseline failures remain part of the report. Three scenarios per condition give an exploratory generalization screen, not a statistical reliability qualification.

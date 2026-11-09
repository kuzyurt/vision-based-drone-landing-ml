# What this repository is, and how I know

Report written 2026-10-24. Method derived from research in `research_plan.md`; evidence tags are defined at the bottom.

---

## Part 1 — What the research actually establishes

### 1.1 Comprehension is not a summary. It is a testable model.

The program-comprehension literature (von Mayrhauser & Vans' integrated metamodel; Wyrich's review, arXiv 2310.11301) describes understanding as an **opportunistic mix of three models**:

- a **top-down** model of goals and expectations,
- a **program model** of control and data flow,
- a **situation model** of what the system is *for*.

Experts switch between them as questions arise, and they use **beacons** (recognisable cues: names, idioms, shapes) and **plans** (stereotyped solutions) to chunk large regions at once. Novices read line by line; experts match patterns to hypotheses.

The operational consequence: **you understand a system to the degree you can predict it.** Not "I have read the files", but "if you change X, Y breaks, and here is the test that would show it." Any account that cannot make a falsifiable prediction is a summary, not comprehension.

### 1.2 The human onboarding sequence is known, and it is not "read everything"

The convergent practitioner sequence (Feathers' four tactics — quick read, detective work, map, pull threads; Ong's "Grokking Big Unfamiliar Codebases"):

1. Establish a **narrow goal** and a **working build** before reading deeply.
2. Read broadly **without changing anything**; form a rough map.
3. **Trace one real path** end to end — from entry point through data to output.
4. Keep a written model with **open questions**, and update it when evidence contradicts it.
5. Treat unfamiliar areas as **black boxes** until a question forces you inside.

Ong's framing is the important one: *"maintain an active mindset rather than a passive one."* Passive reading produces a plausible narrative; active tracing produces predictions.

The 2025 study of professional code auditors (arXiv 2504.04553) found the same hierarchy — overview → structure/business logic → local functions and execution paths — and found that LLM assistance was strong at **local explanation** but weak at **connecting a function to the wider system**. That is precisely the gap this report tries to close.

### 1.3 Why LLM agents fail at this, specifically

| Failure | Mechanism | Detectable signature |
|---|---|---|
| **Premature action** | Training rewards producing a patch; "do something" beats "check whether anything is needed". FixedBench (arXiv 2605.07769): agents edited already-fixed code in 35–65% of 200 stale-bug cases. | First edit precedes reproduction or repo inspection. |
| **Anchoring / hypothesis lock-in** | First plausible cause becomes the frame; later searches only confirm it. | One diagnosis early, then only confirming queries. |
| **Context rot** | Accuracy degrades with input length even on trivial tasks (Chroma, 18 models / 194,480 calls); evidence in the middle is used worst (Liu et al., >20pp drop). | Dumping files instead of targeted reads. |
| **Plausible fill-in** | Unknown project facts get completed from priors: invented APIs, files, config keys. Package hallucination measured at ≥5.2% (commercial) / 21.7% (open) in 576k samples. | Symbols that do not resolve in the checkout. |
| **Specification gaming** | Optimising the visible score: hardcoding, test edits, special-casing. ImpossibleBench: GPT-5 cheated on 54% of conflicting SWE-bench variants (76% on one-off variants). | Test/scorer diffs; branches on input shape. |
| **Sycophancy** | Agreement with the user's premise instead of the code. | Same review flips when the user asserts correctness. |
| **Overconfident self-report** | "Done, tests pass" generated from conversational expectation, not execution. | No command, no exit code, no post-edit rerun. |
| **Scope drift** | Ambiguity plus "best practice" instinct expands the diff. | Unrelated files changed. |

Two structural findings matter more than any single bias:

- **Localisation, not patch generation, is the bottleneck.** Agentless (arXiv 2407.01489) reached 32%/96 fixes on SWE-bench Lite with a fixed localize→repair→validate loop, beating the complex agents it compared against; its ablation keeps ground-truth edit locations in only 77.7% of cases after file-level localisation. If you cannot find the right code, no amount of reasoning saves you.
- **The harness matters more than the model.** SWE-agent's finding is about the *agent-computer interface*: ~100-line file views, search results that list files rather than dumping context. Anthropic's context-engineering guidance says the same thing from the other side: *"the smallest possible set of high-signal tokens"*, retrieved just-in-time, compacted deliberately.

### 1.4 Why the model's own reasoning cannot be the verification

Turpin et al. (2023): explanations rationalise biased answers; of 426 explanations supporting a biased prediction, **one** mentioned the bias. Anthropic (2025): Claude 3.7 Sonnet mentioned an injected hint in ~25% of cases where it changed the answer; on harder GPQA questions faithfulness was ~44% lower. Self-correction without external feedback frequently fails (Huang et al., 2310.01798).

Conclusion: **a model's confidence is a claim, not evidence.** For code, the only trustworthy signals are the repository, the type checker, and executed tests.

### 1.5 What humans actually want (and where trust dies)

- METR's 2025 RCT: experienced OSS developers were **19% slower** with AI, while believing they were **20% faster**. Feeling of productivity is not productivity.
- Stack Overflow 2025: 46% distrust AI accuracy vs 33% trust; **66%** cite "almost right, but not quite" as their main frustration.
- FAccT 2024 interviews: *"it takes three good recommendations to build trust versus one bad recommendation to lose trust."*

So the deliverable a human wants is not a confident narrative. It is: **what you inspected, what you concluded, what you inferred, what you did not check, and how to falsify you.** That is the format this report uses.

### 1.6 The ask-vs-act rule

From value-of-information reasoning plus the clarification literature:

> Inspect the environment first. Ask only when the answer would **change the next action** and cannot be recovered from the repo. Otherwise choose the reversible default, state the assumption, and verify.

ClarifyGPT raised GPT-4 Pass@1 on MBPP-sanitized from 70.96% to 80.80% with requirement clarification; HumanEvalComm found models generated code instead of asking in >60% of deliberately ambiguous tasks. Asking is not weakness; asking about things you could have read is.

---

## Part 2 — The protocol I ran on this repository

1. **Orient from intent-carrying documents first.** READMEs, newest review, handoff, status log. Documents encode *why*; code encodes *how*. Reading code first makes you reverse-engineer intent from accident.
2. **Build a map, not a summary.** Four subsystems, their boundaries, and what each one owns.
3. **Trace one path end to end.** Observation → network → action → PX4 → physics → scorer.
4. **Verify by execution.** Run the tests; run the CLI; check the version pins.
5. **Find the live edge.** The newest run directory and its stop reason — what is broken *right now*.
6. **Write a confidence ledger.** Separate verified from documented from inferred, and name what was not read.

---

## Part 3 — The repository

### 3.1 One sentence

**A research programme to land a drone autonomously on a moving boat using only onboard RGB and declared sensors — simulated in MuJoCo with real PX4 flight control, trained by imitation, evaluated by a strict evidence-gated benchmark, and shipped as a browser game.**

Everything in the tree serves that sentence.

### 3.2 The four subsystems

| Path | Role |
|---|---|
| `px4-mujoco-drone-simulation/` | Drone side: MuJoCo airframe, PX4 SITL bridge, onboard renderer. |
| `AERODOCK_MuJoCo/` | Boat side: USV dynamics, procedural coastal worlds (`BoatSim.new_world`), CAD, web viewer. |
| `landing_training/` | The coupled environment, the learning pipeline, the frozen policy runtimes, qualification and recording. |
| `tidewater-game/` | Deployment: the same policy in a browser, with PX4 compiled to WASM and a JS engine. |
| `benchmark/` | Evaluation: 26 registered actors, 20-case suite, strict scoring, receipts, offline dashboard. |
| `artifacts/` | 29 dated experiment bundles — the project's memory. Frozen sources, weights, audits, rejections. |

Scale: 4,456 tracked files; ~10k+ on disk; 36 modified and 63 untracked paths — i.e. **all work since 14 October is uncommitted**. The last commit is "Complete browser based Tidewater simulator".

### 3.3 How one flight actually works `[D]`

1. **Observation — 32 numbers** (`landing_training/policy.py:22` registers a 32-dim normaliser). Own velocity/attitude/rates, two gimbal angles, radio position/velocity slots, freshness/validity/status, image timing, previous command slots, decision interval. In the `periodic_no_action_v1` variant the six previous-command slots are replaced by sine/cosine pairs of yaw/pan/tilt; radio fields are neutralised.
2. **Vision — MobileNetV3-Small.** Feature maps feed spatial detection/localisation heads plus a 256-d visual projection. A telemetry MLP maps 32→64. Concatenated 320 features enter a **GRU with 128-d hidden state**.
3. **Output — a 15-value pose state**, not motor commands: visibility, relative position (3), relative velocity (3), deck heading (2), deck normal (3), marker image location (2), contact confidence (1).
4. **Control is explicit.** The pose estimate is converted to six commands at 25 Hz: `[forward, right, down velocity, yaw rate, camera pan rate, camera tilt rate]`. The first four go to PX4's offboard velocity/yaw interface; PX4 closes the flight-control loops and produces motor thrust. The last two drive gimbal servos.
5. **Radio is bounded.** A separate fusion MLP (13→48→2) produces blend weights capped at 0.35 that go to zero when the packet is stale; raw radio cannot steer the aircraft.
6. **Scoring is physical.** `benchmark/scoring.py:10` — `strict_landing` requires `status=completed`, `outcome=landed`, `disarmed`, `stable_disarmed_contact_s >= 2`, no collision, no water strike, `assistance_frames == 0`, `wrong_target_contacts == 0`.

This is why the project insists it is **not end-to-end RL**: the network estimates state; classical control flies.

### 3.4 Three implementations that must not be confused `[D]`

This is the single most important distinction in the repo, and the docs repeat it because conflating them produces fake results:

1. **`landing_training/policy.py`** — the historical baseline (MobileNet + telemetry MLP + GRU emitting six actions directly). Kept for reproduction. **Not** the current system.
2. **R15** — the real candidate: learned vision + marker registration + explicit control + PX4. Frozen, hashed, deployed.
3. **Teachers** — `privileged_teacher.py` uses simulator truth and **no neural network**; the observable teacher (v60 protocol + v61 recogniser) uses RGB only. A teacher landing is not a learner landing.

The `city80` review video is a fourth, subtler case: its `SearchDirector` builds waypoints from `frame(env)`, i.e. the **actual pad position**, so its 55 m "lock" does not demonstrate visual acquisition. The architecture review says this explicitly, which is unusually honest.

### 3.5 Where the evidence says it actually fails `[D]`

Not control. **Acquisition and identification.**

- R15's native result: **58/60** fresh no-radio landings, 2 home fallbacks, zero collisions. Good.
- Tidewater stress: 26 more flights, 5 landings; **0/18 challenging search starts**, 5/8 visible-start diagnostics. **17/18 failures had zero accepted pad pose** — the system never got a trustworthy target fix, so it never had a chance to land.
- The architecture review's own conclusion: the central gap is *selecting a weak, uncertain candidate and actively obtaining enough visual evidence to identify it*. A stationary sweep increases angular coverage but not pixel detail; if every distant hull is below the proposal gate, three tilt-band surveys finish with nothing inspected.

So the real research question is: **how do you actively acquire identity evidence at range, against 3 similar and 3 dissimilar decoys, without radio?**

### 3.6 The live edge — what is happening right now `[V]`

`benchmark/runs/comparison_20261024_teacher_r15_radio/SUMMARY.md`:

- **16/60 flights recorded.** Teacher 16/20 recorded, 14 valid, **12 strict landings**; landing 100%, acquisition 80%, speed 80% (provisional). Both learned policies: **0 flights**.
- Batch stopped because wind moved the manual boat ~1.2 m during takeoff while the UAV held a stale absolute start coordinate. Both wind cases correctly **failed validation** (31.14 m and 28.78 m against a 30 m ± 0.75 m contract).
- The correction (follow a relative offset from the boat's current position before the clock starts) is described in the review. A new runtime snapshot is required; old valid flights are retained as qualification evidence, not mixed.
- `..._v2` then stopped **before any scored result**: "Windows path-length limitation" during deep model staging. Its worker log shows one flight reached 50 s and was killed.

And the code already contains a partial fix: `benchmark/runner.py:60` `native_path()` prefixes `\\?\` on Windows, and `stage()` at line 70 uses it. The blocker is therefore *not* the absence of a long-path helper — it is a path that bypasses it (or a consumer that rejects verbatim paths, e.g. `importlib`/DLL loading). **That is the next thing to check, not the next thing to guess.** `[I]`

### 3.7 The governance layer — the most unusual thing here `[D][I]`

This repository is not organised like a codebase. It is organised like an **evidence ledger for a long-running autonomous research process**:

- frozen bundles with SHA-256 identities; a change means a new bundle, never an edit;
- "unscored" distinguished from "failed" — infrastructure error is not a policy failure;
- Wilson intervals included but explicitly labelled *descriptive*, not a population guarantee;
- rejected experiments preserved (`V53 REJECTED`, `V55 REJECTED`, "earlier failed audit retained");
- instructions written as prohibitions to future agents: *"do not duplicate running jobs"*, *"do not relax that bound"*, *"do NOT add dwell or relax thresholds"*, *"no training data admitted"*;
- `STATUS.md` reads as an agent's own audit trail: hypotheses marked **DISPROVED**, not quietly dropped.

This is the correct design for the failure modes in §1.3. It is also why the documentation is long: **the docs are the harness.** In a repo where an agent may resume work months later, the prose is executable policy, not commentary.

---

## Part 4 — Confidence ledger

| Claim | Basis |
|---|---|
| 19/19 offline contract tests pass | **V** — ran `pytest benchmark/tests` |
| MuJoCo 3.14.0, torch 2.6.0+cu124, numpy 2.2.6 installed | **V** — imported them |
| 26 actors registered; 59 loose weight files / 16 unique hashes | **V** — `python -B -m benchmark list` |
| Current run is 16/60, stopped on wind start-distance | **V** — read `SUMMARY.md`, `diagnostic_stop.json`, `summary.json` |
| v2 stopped on Windows path length before scoring | **V** — `diagnostic_stop.json` |
| Long-path helper exists at `runner.py:60` and is used by `stage()` | **V** — read the file |
| 32-dim observation contract | **V** — `policy.py:22` |
| Scoring requires ≥2 s stable disarmed contact, zero assistance | **V** — `scoring.py:10-16` |
| Architecture, R15 identity, 58/60, 0/18 | **D** — repo docs; numbers not independently reproduced |
| The long-path failure is a consumer bypassing `native_path` | **I** — inference from code + symptom, untested |
| Browser game parity claims | **D** — not run; no browser check performed |

**Not inspected:** `tidewater-game/app/src` (248 files), the WASM build, `AERODOCK_MuJoCo/usv` physics, the actual artifacts' weights and videos, the 4,456 tracked files beyond ~15 read in full. I read roughly 0.3% of files, chosen for **intent density** rather than coverage.

**The honest statement:** I understand the mission, the architecture, the current candidate, the failure mode, and the live blocker. I do not understand the boat hydrodynamics, the browser rendering pipeline, or the contents of most experiment bundles. Anyone claiming total comprehension of a 10k-file research repo after an hour is doing the thing this report is about.

## Part 5 — How to falsify me

1. Run `python -B -m benchmark status` (or read `summary.json`) — if it is not 16/60, my snapshot is stale.
2. Open `landing_training/policy.py:22` — if the observation is not 32, the architecture section is wrong.
3. Check `benchmark/runs/comparison_20261024_teacher_r15_radio_v2/diagnostic_stop.json` — the path-length blocker is either still the edge or already fixed.
4. Ask me to predict: *"if you change the radio fusion cap from 0.35, which tests and which cases move?"* A model that understands should answer; one that summarised cannot.

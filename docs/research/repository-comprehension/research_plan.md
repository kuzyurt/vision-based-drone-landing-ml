# Research Plan: How should an LLM agent actually understand a repository?

## Main question
What does genuine comprehension of an unfamiliar codebase consist of, how do the best human engineers achieve it, where do LLM agents systematically fail at it, and what procedure maximises the probability that an agent's claims about a repo are *true* rather than *plausible*?

## Subtopic 1 — Human program comprehension
- Empirical cognitive science of program comprehension (integrated metamodel, beacons, plans, bottom-up vs top-down vs opportunistic).
- Practitioner tactics from people who routinely onboard onto huge codebases (Michael Feathers, Jeremy Ong, Julia Evans, "software archaeology").
- What "understanding" operationally means: predictive power, not summary.
- Expected output: a definition of comprehension + the tactics that produce it.

## Subtopic 2 — LLM agents navigating repos
- Context engineering for coding agents; agentic grep/read loops vs. embedding retrieval vs. whole-repo stuffing.
- Long-context degradation ("context rot", lost-in-the-middle), why more context is not better.
- Evidence on what actually determines success on SWE-bench-like tasks (localization vs. patch generation; Agentless result).
- Repo-level comprehension benchmarks (RepoQA, CodeRAG-Bench, SWE-bench Verified critiques).
- Expected output: what the agent harness must do, and what it must not do.

## Subtopic 3 — Failure modes and biases of LLM agents
- Premature action / action bias; hypothesis lock-in / anchoring; confirmation bias in follow-up searches.
- Hallucinated APIs, invented files, confident false claims about code.
- Specification gaming, test tampering, reward hacking, overclaiming success.
- Sycophancy and scope drift.
- Empirical failure taxonomies from agent trajectory studies.
- Expected output: a named list of failure modes with detection heuristics.

## Subtopic 4 — Task interpretation and ambiguity
- Underspecification, the XY problem, requirement elicitation.
- Research on when models should ask vs. proceed; cost of a wrong guess vs. cost of a question.
- "Literal compliance vs. intended outcome" failure.
- Expected output: a decision rule for acting vs. asking.

## Subtopic 5 — Human factors / what people actually want
- Trust calibration, automation bias, verification burden, review bottleneck.
- Productivity evidence: does AI assistance help, and where does the time go?
- What developers report wanting from coding agents (and what erodes trust).
- Expected output: the deliverable format a human actually finds useful.

## Subtopic 6 — Epistemics of the model itself
- Chain-of-thought faithfulness; whether stated reasoning reflects actual computation.
- Calibration and abstention; knowing what you don't know.
- "Illusion of thinking" debate and its rebuttals.
- Expected output: rules for honest self-reporting of confidence and coverage.

## Synthesis
Two artifacts:
1. A written method (the procedure + the epistemics behind it).
2. An executed application of that method to the actual repository, with every claim anchored to a path/line/command, an explicit coverage accounting, and an explicit list of what remains unknown.

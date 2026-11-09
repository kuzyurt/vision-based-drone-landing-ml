# Third-party code

Pinned external checkouts belong here, not inside a package source tree.

Current situation: PX4-Autopilot is vendored at
`landing_training/.vendor/PX4-Autopilot/` as a nested git repository. It is
excluded from the main index and must not be edited as project source.

Future options, in order of preference:

1. A git submodule pinned to the exact PX4 commit.
2. A setup script that fetches the pinned commit into this directory.
3. An environment variable pointing at an external checkout.

Do not copy PX4 into a wheel or commit its build output.

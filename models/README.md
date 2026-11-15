# Models

Weights are content-addressed: one file per SHA-256.

| What | Where |
|---|---|
| Weights used by the benchmark | [`benchmark/policies/weights/`](../benchmark/policies/weights/) |
| Policy → weights mapping | [`benchmark/policies/inventory.json`](../benchmark/policies/inventory.json) |
| Index of the previous benchmark | [`registry.json`](registry.json) (paths refer to the tree before 11 November) |

A run references a hash and never copies a weight into its own folder. Add a
new weight only together with its inventory entry and a verified SHA-256.

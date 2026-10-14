# Browser runtime source notices

PX4 flight modules are compiled from revision
`6ea3539157ca358c70a515878b77077af7d4611d` under BSD-3-Clause.
MuJoCo 3.14.0 is used under Apache-2.0 through its official WebAssembly bindings.
BrowserNoise translates the PCG64 and Ziggurat routines from NumPy 2.2.6 under
BSD-3-Clause. Source licenses accompany the browser distribution.

Full licenses and copyright notices are distributed in
[`app/public/licenses`](../app/public/licenses/) and copied to `dist/licenses/`.
[`landing/wasm/provenance.json`](../app/public/landing/wasm/provenance.json) records
the pinned sources and the rebuilt runtime artifact hashes.

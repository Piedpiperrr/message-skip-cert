# Official C2C runtime (`rosetta`) - third-party code

This release vendors the `rosetta` package from the official Cache-to-Cache (C2C)
reference implementation, unmodified, so that the C2C arm of the pipeline can be
run and audited.

| field | value |
|---|---|
| source project | https://github.com/thu-nics/C2C |
| commit | `113c3a9b2538cbf096a0477e1ec99ae2a2e0d12a` |
| license | Apache License 2.0 (full text in `LICENSE` beside this file) |
| modified by us? | no - the vendored files are byte-identical to that commit |

**This code is NOT covered by the repository's MIT `LICENSE`.** It remains under
Apache-2.0 and keeps its own copyright.

Vendored copies in this repository (identical content, both with the licence beside them):

- `code/pipeline/native_action_runtime/runtime_source/rosetta/` - the copy the pipeline imports
- `code/analysis/sealed_arc_test/delivery/runtime_source_snapshot/P2_10_20260911T122423Z/runtime_source/rosetta/`
  - the snapshot frozen for the sealed ARC test, kept so that run is auditable

Only the subset of the package the pipeline needs is included; the upstream project
has further files that are not redistributed here.

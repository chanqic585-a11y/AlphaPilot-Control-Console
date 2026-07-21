# V55.1 Adaptive Learning Safe-Checkpoint Plan

## Objective

Insert the V55 adaptive-learning addendum after the independently committed V55 Demo runtime hardening without changing the approved TOP200 Release's order semantics.

## Frozen checkpoint

- V55 implementation commit: `af3560e2944592019e461056ba12d3c0aac548d0`
- Exact Demo approval already exists, so it is preserved and never amended.
- Demo runtime is not armed in the current process.
- Strategy order, partial fill, unknown order, and non-zero position counts are zero.
- Quant and Console worktrees were clean before this insertion.

## Implementation boundary

1. Extend the existing Quant Factor Registry with production metadata rather than creating a competing registry.
2. Add one shared `AdaptiveLearningCore` with thin Demo and Live adapters.
3. Bind the current approved Release only to an observer sidecar. The sidecar cannot rank, veto, size, create, cancel, or modify orders.
4. Persist point-in-time feature snapshots, observer decisions, and only real reconciled closed Demo/Live learning samples.
5. Exclude engineering smoke, fixtures, and virtual shadow outcomes from learning samples.
6. Require a successor Model Policy Hash, Release Hash, and exact human approval before any rank, veto, or meta-label mode can affect decisions.
7. Keep Live disabled. `AdaptiveLearningLiveReadinessGate` must reject `none` and observer-only modes and fail closed on missing, stale, mismatched, or drifted model evidence.
8. Generate truthful evidence. Unexecuted Factor Bench, Qlib, training, drift, rollback, and Live inference work is marked `status=not_run` rather than represented as passed.

## Validation

- Targeted adaptive-learning tests.
- Full Console and Quant test suites.
- `compileall`, config validation, safety scans, and `git diff --check`.
- Artifact hash verification and credential-field scan.
- Separate Quant and Console commits, tags, and pushes.

## Explicit non-actions

- Do not ARM Demo.
- Do not create a Demo or Live strategy order.
- Do not enable Live or Withdraw.
- Do not mutate the approved TOP200 Release, Risk Overlay, or exact approval record.
- Do not auto-promote or auto-approve a model.

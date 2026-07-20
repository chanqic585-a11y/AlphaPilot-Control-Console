# V47 Demo Runtime Truth Audit Design

## Decision

Generate a read-only truth audit from the existing Demo release contracts and runtime stores. The audit explains credential source state, private-read evidence state, legacy release classification, release-to-instrument compatibility, scan-funnel conservation, and runtime blockers without changing immutable contracts or runtime state.

## Legacy releases

The ten historical `experimental_override` contracts are projected as `legacy_experimental_override`:

- execution eligible: false
- strategy qualification eligible: false
- forward evidence eligible: false
- live promotion eligible: false

The projection is an external sidecar. Contract bytes and hashes remain unchanged.

## Credential semantics

The audit distinguishes `process_environment`, `windows_credential_manager`, and `missing`. It emits metadata only. It never writes, logs, or exports credential values and never bootstraps credentials merely to complete an audit.

## Funnel

The runtime funnel is reconstructed from stored checkpoint and heartbeat events. Counts are conserved across loaded, scheduled, evaluated, matched, attempted, accepted, and terminal stages. Missing evidence is reported as unavailable rather than inferred.

## Safety

- Read-only SQLite access.
- No API call, order, cancel, ARM, or release write.
- No Withdraw integration.
- No live execution changes.

# Athanor — Architecture Decision Records

## ADR-001: OpenRouter as Single LLM Gateway

**Status**: Accepted
**Date**: 2026-04

**Context**: Need access to multiple LLM providers (Anthropic, OpenAI, Google, Meta, Mistral) without managing separate API keys and accounts for each.

**Decision**: Use OpenRouter as the single API gateway for all LLM access.

**Consequences**:
- (+) Single API key, single billing, single dashboard
- (+) OpenAI-compatible API works with all tools (OpenWebUI, Roo Code, HA)
- (+) Easy model switching without infrastructure changes
- (-) 5.5% fee on token credits
- (-) Dependency on a third-party SaaS (no self-hosted option)
- (-) Prompts transit through OpenRouter servers (privacy consideration)

---

## ADR-002: Cloud Run over GKE

**Status**: Accepted
**Date**: 2026-04

**Context**: Need a container runtime on GCP with true scale-to-zero for cost optimization.

**Decision**: Use Cloud Run (not GKE) for all containerized services.

**Consequences**:
- (+) True scale-to-zero: €0 cost when idle
- (+) Simpler operations: no cluster management
- (+) Built-in HTTPS, auto-scaling, revision management
- (-) Limited to HTTP workloads (no persistent background jobs)
- (-) Cold start latency (15-30s for OpenWebUI)
- (-) GCS FUSE for SQLite has concurrency limitations

---

## ADR-003: SQLite + GCS FUSE for MVP, Cloud SQL for Scale

**Status**: Accepted
**Date**: 2026-04

**Context**: OpenWebUI needs persistent storage. Cloud SQL PostgreSQL always-on costs ~€8+/month even idle.

**Decision**: Start with SQLite on GCS FUSE (free), migrate to Cloud SQL PostgreSQL when concurrent users cause issues.

**Consequences**:
- (+) Zero database cost for MVP
- (+) Simple setup, no extra Terraform module
- (-) Risk of data corruption with concurrent writes
- (-) Migration work needed later
- Trigger for migration: any data corruption or >2 concurrent active users
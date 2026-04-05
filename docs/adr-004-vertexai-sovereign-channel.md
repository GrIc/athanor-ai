# ADR-004: VertexAI as Sovereign Channel via API Proxy

**Status**: Accepted
**Date**: 2026-04-05

## Context

All LLM traffic currently flows through OpenRouter, meaning every prompt leaves GCP and transits through a third-party SaaS. For sensitive data (financial, health, personal family data), this violates our EU sovereignty principle.

VertexAI provides Google's Gemini models directly within GCP, keeping data within the Google Cloud boundary (europe-west9).

## Problem

The VertexAI OpenAI-compatible endpoint (`/v1beta1/projects/.../endpoints/openapi`) requires **Google OAuth2 authentication**, not a simple API key. OpenWebUI sends `Authorization: Bearer <key>` in OpenAI format, but VertexAI validates against Google OAuth2 tokens.

## Decision

Deploy a lightweight **VertexAI Proxy** on Cloud Run that:
1. Receives OpenAI-compatible requests from OpenWebUI with a simple API key
2. Authenticates to VertexAI using the Cloud Run service account (automatic OAuth2)
3. Forwards requests to the VertexAI endpoint

OpenWebUI connects to the proxy as a second "Connection" in the admin panel.

## Consequences

### Pros
- (+) Sensitive prompts never leave GCP (EU sovereign)
- (+) No additional cost at rest — proxy scales to zero
- (+) Gemini models available alongside Claude/GPT via OpenRouter
- (+) Clean separation: proxy handles auth, OpenWebUI handles UI
- (+) Proxy is reusable for Roo Code, CLI, and other tools

### Cons
- (-) VertexAI costs are separate from OpenRouter billing (two bills to track)
- (-) Additional Cloud Run service (~€0.50/month at light usage)
- (-) User must select the right model/connection in OpenWebUI

## Cost Impact

| Component | Idle | Light | Moderate |
|-----------|------|-------|----------|
| VertexAI proxy | €0 | €0.50 | €1 |
| VertexAI tokens | €0 | €2 | €10 |
| OpenRouter tokens | €0 | €5 | €20 |
| **Total** | **€0** | **~€7.50** | **~€31** |

## Security Review

- VertexAI data stays within `europe-west9` (Paris) — EU sovereign
- No data leaves GCP for VertexAI requests
- IAM: Cloud Run service account needs `roles/aiplatform.user`
- Proxy API key stored in GCP Secret Manager
- OpenWebUI authenticates to proxy via API key, proxy authenticates to VertexAI via service account

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    OpenWebUI                         │
│                                                      │
│  Chat 1 (sensitive) ──► VertexAI Proxy Connection   │
│    Model: gemini-2.0-flash                           │
│                                                      │
│  Chat 2 (general) ──► OpenRouter Connection          │
│    Model: claude-3.5-sonnet                          │
└──────────┬──────────────────────┬────────────────────┘
           │                      │
           ▼                      ▼
    ┌──────────────┐      ┌──────────────┐
    │ VertexAI     │      │  OpenRouter  │
    │  Proxy       │      │  (SaaS)      │
    │  Cloud Run   │      │              │
    │  (OAuth2)    │      │              │
    └──────┬───────┘      └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  VertexAI    │
    │  (europe-w9) │
    │  Gemini      │
    └──────────────┘
    Data stays in GCP
```

## Implementation

1. Enable `aiplatform.googleapis.com` API in [`infra/apis.tf`](infra/apis.tf:2)
2. Grant `roles/aiplatform.user` to Cloud Run service account in [`infra/iam.tf`](infra/iam.tf:1)
3. Deploy VertexAI Proxy Cloud Run service ([`infra/cloud-run.tf`](infra/cloud-run.tf:100))
4. Deploy proxy Docker image ([`docker/vertexai-proxy/`](docker/vertexai-proxy/app.py:1))
5. Configure VertexAI Proxy connection in OpenWebUI admin panel

## Rollback

- Remove VertexAI Proxy connection in OpenWebUI admin panel
- `terraform destroy` the proxy service
- Remove `aiplatform.user` IAM role
- Remove `aiplatform.googleapis.com` from enabled APIs

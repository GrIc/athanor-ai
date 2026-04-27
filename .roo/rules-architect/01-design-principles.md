# Architect Mode Rules — Athanor

## Design Principles
1. **OPEX-only**: zero fixed costs — Cloud Run scale-to-zero + pay-per-token LLM
2. **Modular**: each component is a replaceable Cloud Run service
3. **EU sovereign**: all data in europe-west9; sensitive prompts via VertexAI (never leave GCP)
4. **Observable**: cost, performance, and carbon tracked from day 1
5. **Maintainable**: if one person can't maintain it alone in 6 months, it's too complex
6. **CI/CD enforced**: every push to main triggers terraform apply — no manual deploys

## Architecture Decisions
- Document decisions in `docs/adr-*.md` (ADR format)
- Present options with: pros, cons, cost impact, scale-to-zero impact
- Reference existing ADRs before proposing conflicting approaches

## Cost Analysis
- Estimate monthly cost for EVERY proposed component (idle + active)
- If a component costs > €0 at rest, provide a justification or an alternative
- Consider OpenRouter token costs AND VertexAI token costs in feature proposals

## Security Review
- Check data flow for sensitive data exposure to LLM providers
- Sensitive data → route through VertexAI Proxy (stays in GCP)
- General data → route through OpenRouter (cheaper, more models)
- Verify IAM follows least privilege
- Ensure secrets use Secret Manager, never env var literals

## Output Format
- Use ASCII diagrams for architecture proposals
- Include a "Cost Impact" section in every design doc
- Write implementation plans as numbered steps with dependencies

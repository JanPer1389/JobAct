# ADR-0006: LiteLLM proxy in front of OpenRouter (a gateway in front of a gateway)

## Status

Accepted, implemented (Milestone 1).

## Context

PAPERCUT specifies LiteLLM as the application's single LLM gateway, for its own routing,
fallback, per-call cost accounting, and observability. Separately, this session chose
OpenRouter as the actual model provider behind LiteLLM. Put together, that is a gateway in
front of a gateway: OpenRouter already does model routing, provider fallback, and cost
accounting on its own — LiteLLM adds a second layer of exactly those things on top.

## Decision

Keep LiteLLM exactly as PAPERCUT specifies, with OpenRouter configured as its provider
(`backend/litellm_config.yaml`: `model_name: report-drafter` → `openrouter/anthropic/
claude-sonnet-4.5`, plus a registered-but-unused `report-drafter-fallback` alias — see
[`ai.md`](../architecture/ai.md) for why it isn't wired up yet). The application only ever
knows the LiteLLM model alias `report-drafter`; it never sees an OpenRouter key or model
string directly (`OPENROUTER_API_KEY` is consumed by the `litellm` container alone).

**The trade-off, made explicit rather than hidden:** this is deliberately paying for a second
failure surface and a second set of timeouts (`litellm_config.yaml`'s `request_timeout: 45`
must stay below the calling activity's own timeout budget, or retries stack badly across both
layers) in exchange for one property — swapping OpenRouter for a Russian LLM provider at
launch (a real, not hypothetical, need given PAPERCUT's Russian-launch/data-residency
constraints) becomes a `litellm_config.yaml` edit, not an application code change, because the
application already only speaks LiteLLM aliases. If OpenRouter were called directly, that same
swap would mean re-plumbing whatever OpenRouter-specific request/response shape the
application had absorbed.

**The AI-safety invariant this ADR does not touch:** regardless of which model or provider
answers behind LiteLLM, `Report.mark_ready_for_signature()` refuses to let an unconfirmed
AI-proposed amount reach a signed document (see [`ai.md`](../architecture/ai.md) and
[`erd.md`](../architecture/erd.md)). That invariant lives in the domain layer, not in either
gateway, precisely so it survives a provider swap made under this ADR unmodified.

## Consequences

- Provider swap is config-only, as designed — the justification for the extra hop.
- Two timeout budgets to keep coherent (`litellm_config.yaml` vs. the workflow activity's own
  handling) — misconfiguring this stacks retries badly; see the plan's Risks section.
- LiteLLM's own spend log and the `workflow_steps.output` cost capture (from LiteLLM's
  response headers) are the two places cost is visible; OpenRouter's own dashboard is a third,
  informational-only view that the application does not read from.

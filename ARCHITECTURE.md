# Vuln Triage & Remediation Console — Architecture

## What this is
This service is the **seam** between two things that don't speak the same language:

- **security scanners** (they emit thousands of raw, noisy, duplicated findings)
- **a human triager** (who can only act on a small, prioritized, explained list)

The console's whole job is to turn the first into the second, and then to
**prove the loop closed** — that a finding an operator asked to fix is actually
gone on the next scan. That proof is the product.

## The loop (this is the spine)
1. **Ingest** a repo (GitHub API) at a pinned commit — scans are only meaningful
   against an exact tree.
2. **Scan** it (async, via a queue) — a scanner adapter normalizes any tool's
   output into ONE finding shape.
3. **Model** findings in Postgres — severity, location, evidence, status, and a
   **fingerprint** that identifies "the same weakness" across scans.
4. **Triage** with an LLM — explain each finding in plain English, prioritize it,
   draft a remediation. Grounded strictly in the finding's own evidence.
5. **Fix** — the operator works the prioritized list; every status change is an
   append-only audit event (who, when, why).
6. **Re-run & prove** — a fresh scan is diffed against the prior one BY
   FINGERPRINT: fixed (was there, now gone), regressed (was fixed, back),
   new (never seen). The diff is the evidence the fix landed.
7. **Observe** — spans + metrics across the whole pipeline so a slow or failing
   stage is visible, not a mystery.

## Why the LLM sits in the MIDDLE, not the ends
The scanner decides WHAT is wrong (deterministic, auditable). The human decides
WHAT TO DO (accountable). The LLM sits between them doing the toil neither is
good at: reading a raw finding and its evidence, saying it in English, ranking
it, and drafting a fix. It never invents findings and never closes them — it
accelerates a human who still owns the decision.

## The contract the React console renders
- `POST /repos` / `POST /scans`        — ingest a repo, enqueue a scan
- `GET  /findings`                     — the triage queue: filter, sort, paginate
- `GET  /findings/{id}`                — detail: evidence, LLM triage, history
- `POST /findings/{id}/status`         — advance triage (append-only)
- `GET  /scans/{id}/diff`              — the prove-it's-fixed re-run diff
- `GET  /metrics/summary`              — the header: open by severity, MTTR

Storage can change underneath (more workers, a sharded findings table) without
the console changing. The contract is the stable thing.

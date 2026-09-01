# Codebase Vulnerability Triage & Remediation Console

An advanced, full-stack security-ops capstone that mirrors OpenAI's Cybersecurity Products team. You ingest a code repo, run a scanner to produce raw findings, and model them in Postgres with severity, location, evidence, status, and a fingerprint that deduplicates the same weakness across scans. You run scans asynchronously through a Redis-backed queue and worker so the API never blocks on a long scan, then add an LLM-assisted triage stage that explains each finding in plain English, prioritizes it against exploitability and reachability, and drafts a concrete remediation — always grounded in the finding's own evidence, never invented. You drive a fix workflow with an append-only evidence trail (who changed what status, when, why), then build the payoff: a re-run that diffs a fresh scan against the prior one by fingerprint and PROVES which findings are fixed, which regressed, and which are new. You instrument the whole pipeline with OpenTelemetry-style spans and metrics, and sketch a React + TypeScript operator console on top of the contract. The reference implementation runs on plain Python (FastAPI) + Postgres + Redis so the security reasoning stays front and center.

## Stack
- React
- TypeScript
- Python
- PostgreSQL
- Redis
- queue
- GitHub API

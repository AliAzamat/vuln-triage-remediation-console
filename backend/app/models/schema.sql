-- A repo we ingested, pinned to an exact commit. Scans are only meaningful
-- against a specific tree, so the commit is part of the identity.
CREATE TABLE IF NOT EXISTS repos (
    id           UUID PRIMARY KEY,
    owner        TEXT        NOT NULL,
    name         TEXT        NOT NULL,
    commit_sha   TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner, name, commit_sha)
);

-- One row per scan run. status walks queued -> running -> done/failed.
-- prior_scan_id links a re-run to the scan it should be diffed against.
CREATE TABLE IF NOT EXISTS scans (
    id             UUID PRIMARY KEY,
    repo_id        UUID        NOT NULL REFERENCES repos (id) ON DELETE CASCADE,
    scanner        TEXT        NOT NULL,            -- 'semgrep' | 'bandit' | ...
    status         TEXT        NOT NULL DEFAULT 'queued',
    prior_scan_id  UUID        REFERENCES scans (id),
    error          TEXT,
    started_at     TIMESTAMPTZ,
    finished_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The core object. A finding is a specific weakness at a specific location,
-- discovered by a specific scan. The fingerprint is its cross-scan identity.
CREATE TABLE IF NOT EXISTS findings (
    id             UUID PRIMARY KEY,
    scan_id        UUID        NOT NULL REFERENCES scans (id) ON DELETE CASCADE,
    repo_id        UUID        NOT NULL REFERENCES repos (id) ON DELETE CASCADE,
    -- Stable dedup identity: same weakness across scans -> same fingerprint.
    fingerprint    TEXT        NOT NULL,
    rule_id        TEXT        NOT NULL,            -- e.g. 'python.sqli'
    severity       SMALLINT    NOT NULL,            -- 0 info .. 4 critical
    file_path      TEXT        NOT NULL,
    start_line     INTEGER     NOT NULL,
    end_line       INTEGER     NOT NULL,
    message        TEXT        NOT NULL,            -- the scanner's raw message
    -- Structured evidence: the code snippet, the matched sink, cwe, etc.
    -- This is what the LLM triages and what a human reads. Never invented.
    evidence       JSONB       NOT NULL DEFAULT '{}',
    -- LLM triage output lands here (explanation, priority, draft fix). Nullable
    -- until triage runs; the finding is real without it.
    triage         JSONB,
    -- Current status is DERIVED from finding_events, cached here for fast lists.
    status         TEXT        NOT NULL DEFAULT 'open',  -- open|triaged|fixing|fixed|wontfix|regressed
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Within one scan a fingerprint appears at most once (the scan already
    -- de-dupes internally); across scans the fingerprint repeats on purpose.
    UNIQUE (scan_id, fingerprint)
);

-- APPEND-ONLY audit. Every status change on a finding is an immutable event:
-- who moved it, from what to what, when, and why. We NEVER update or delete.
CREATE TABLE IF NOT EXISTS finding_events (
    id             UUID PRIMARY KEY,
    fingerprint    TEXT        NOT NULL,            -- ties events across re-scans
    repo_id        UUID        NOT NULL REFERENCES repos (id) ON DELETE CASCADE,
    finding_id     UUID        REFERENCES findings (id) ON DELETE SET NULL,
    from_status    TEXT,
    to_status      TEXT        NOT NULL,
    actor          TEXT        NOT NULL,            -- operator identity
    reason         TEXT        NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lists filter by repo + severity and sort by severity; this index backs that.
CREATE INDEX IF NOT EXISTS ix_findings_repo_sev ON findings (repo_id, severity DESC);
-- The re-run diff and the event history both look up by fingerprint.
CREATE INDEX IF NOT EXISTS ix_findings_scan_fp   ON findings (scan_id, fingerprint);
CREATE INDEX IF NOT EXISTS ix_events_fp_created  ON finding_events (fingerprint, created_at DESC);

// The typed client. These types ARE the contract the backend froze — the console
// is just a view over them. Change the backend's storage or add workers freely;
// as long as these shapes hold, this file and every component below are untouched.
export type Severity = 0 | 1 | 2 | 3 | 4;
export type FindingStatus =
  | "open" | "triaged" | "fixing" | "fixed" | "wontfix" | "regressed";

export interface Triage {
  explanation: string;
  priority: "p0" | "p1" | "p2" | "p3" | "needs_human";
  exploitability: "high" | "medium" | "low" | "unknown";
  remediation: string;
  reasoning: string;
}

export interface FindingDetail {
  id: string;
  rule_id: string;
  severity: Severity;
  location: string;
  evidence: Record<string, unknown>;
  triage: Triage | null;     // null until triage runs; the UI shows a "triaging…" state
  status: FindingStatus;
  history: Array<{ from_status: string | null; to_status: string; actor: string; reason: string; created_at: string }>;
}

export interface ScanDiff {
  fixed: string[];
  regressed: string[];
  new: string[];
  persistent: string[];
  counts: { fixed: number; regressed: number; new: number; persistent: number };
}

const BASE = import.meta.env.VITE_BACKEND ?? "";

export async function getFinding(id: string): Promise<FindingDetail> {
  const r = await fetch(`${BASE}/findings/${id}`);
  if (!r.ok) throw new Error(`finding ${id}: ${r.status}`);
  return r.json();
}

export async function changeStatus(
  id: string, to_status: FindingStatus, actor: string, reason: string,
): Promise<void> {
  const r = await fetch(`${BASE}/findings/${id}/status`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ to_status, actor, reason }),
  });
  if (!r.ok) throw new Error(`status change failed: ${r.status}`);
}

export async function getScanDiff(scanId: string): Promise<ScanDiff> {
  const r = await fetch(`${BASE}/scans/${scanId}/diff`);
  if (!r.ok) throw new Error(`diff ${scanId}: ${r.status}`);
  return r.json();
}

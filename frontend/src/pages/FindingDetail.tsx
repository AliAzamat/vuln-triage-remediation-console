// The detail pane: evidence, the LLM's triage draft, the human status controls,
// and the immutable history — the three surfaces (scanner / LLM / human) in one view.
import { useEffect, useState } from "react";
import { getFinding, changeStatus, type FindingDetail as Detail } from "../lib/api";

const SEV_LABEL = ["info", "low", "medium", "high", "critical"];

export function FindingDetail({ id, actor }: { id: string; actor: string }) {
  const [f, setF] = useState<Detail | null>(null);

  useEffect(() => { getFinding(id).then(setF); }, [id]);
  if (!f) return <div className="detail loading">Loading finding…</div>;

  async function move(to: Detail["status"]) {
    await changeStatus(id, to, actor, "");
    setF(await getFinding(id));     // refetch so the immutable history shows the new event
  }

  return (
    <div className="detail">
      <header>
        <span className={`sev sev-${f.severity}`}>{SEV_LABEL[f.severity]}</span>
        <code>{f.rule_id}</code>
        <span className="loc">{f.location}</span>
        <span className={`status status-${f.status}`}>{f.status}</span>
      </header>

      {/* The scanner's evidence — raw, never invented. */}
      <section className="evidence">
        <h3>Evidence</h3>
        <pre>{String((f.evidence as Record<string, unknown>).snippet ?? "")}</pre>
      </section>

      {/* The LLM's triage draft. Absent until triage runs; a human still decides. */}
      <section className="triage">
        <h3>Triage (assisted)</h3>
        {f.triage ? (
          <>
            <p className="explain">{f.triage.explanation}</p>
            <div className="priority">
              priority <b>{f.triage.priority}</b> · exploitability {f.triage.exploitability}
            </div>
            <pre className="fix">{f.triage.remediation}</pre>
          </>
        ) : <p className="pending">Triaging…</p>}
      </section>

      {/* Human controls — note: no "mark fixed" button. Fixed is proven, not clicked. */}
      <section className="controls">
        <button onClick={() => move("fixing")}>Start fixing</button>
        <button onClick={() => move("wontfix")}>Won't fix</button>
      </section>

      {/* The append-only audit trail, newest first. */}
      <section className="history">
        <h3>History</h3>
        <ul>
          {f.history.map((e, i) => (
            <li key={i}>
              <b>{e.to_status}</b> by {e.actor}
              {e.reason && <> — {e.reason}</>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

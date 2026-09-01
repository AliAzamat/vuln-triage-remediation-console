// The prove-it's-fixed view: run the diff and show fixed / regressed / new counts.
// This screen is the reason the whole system exists — a human-readable proof.
import { useEffect, useState } from "react";
import { getScanDiff, type ScanDiff } from "../lib/api";

export function RerunProof({ scanId }: { scanId: string }) {
  const [diff, setDiff] = useState<ScanDiff | null>(null);
  useEffect(() => { getScanDiff(scanId).then(setDiff); }, [scanId]);
  if (!diff) return <div>Computing re-run diff…</div>;

  return (
    <div className="rerun">
      <h2>Re-run proof</h2>
      <div className="tiles">
        <div className="tile good">{diff.counts.fixed} <span>proven fixed</span></div>
        <div className="tile bad">{diff.counts.regressed} <span>regressed</span></div>
        <div className="tile warn">{diff.counts.new} <span>new</span></div>
        <div className="tile">{diff.counts.persistent} <span>still open</span></div>
      </div>
      {diff.regressed.length > 0 && (
        <p className="alert">
          {diff.regressed.length} previously-fixed findings came back — these need eyes first.
        </p>
      )}
    </div>
  );
}

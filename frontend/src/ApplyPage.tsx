import { useState } from 'react';
import { runAutofill, type RunAutofillResult } from './services/resumeAPI';

const DEFAULT_JOB_URL =
  'https://mackaysposito.applytojob.com/apply/jobs/details/NmmaOEHCRw';

function ApplyPage() {
  const [jobUrl, setJobUrl] = useState(DEFAULT_JOB_URL);
  const [headless, setHeadless] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [result, setResult] = useState<RunAutofillResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!jobUrl.trim()) return;
    setStatus('running');
    setError(null);
    setResult(null);
    try {
      const res = await runAutofill(jobUrl.trim(), headless);
      setResult(res);
      setStatus(res.success ? 'success' : 'error');
      if (!res.success && res.error) setError(res.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      setStatus('error');
    }
  };

  return (
    <div className="apply-page">
      <aside className="apply-sidebar">
        <h2 className="sidebar-title">Run autofill</h2>
        <p className="sidebar-hint">
          Use the profile you saved. A new browser window will open, go to the job page, click Apply, and fill the form.
        </p>
        <div className="sidebar-field">
          <label htmlFor="job-url">Job application URL</label>
          <input
            id="job-url"
            type="url"
            value={jobUrl}
            onChange={(e) => setJobUrl(e.target.value)}
            placeholder="https://..."
            disabled={status === 'running'}
          />
        </div>
        <div className="sidebar-field checkbox-field">
          <label>
            <input
              type="checkbox"
              checked={headless}
              onChange={(e) => setHeadless(e.target.checked)}
              disabled={status === 'running'}
            />
            Run in background (no browser window)
          </label>
        </div>
        <button
          type="button"
          className="sidebar-button"
          onClick={handleRun}
          disabled={status === 'running' || !jobUrl.trim()}
        >
          {status === 'running' ? 'Running…' : 'Start autofill'}
        </button>
        {status === 'running' && (
          <p className="sidebar-status running">Opening browser and filling form…</p>
        )}
        {status === 'success' && result && (
          <div className="sidebar-result success">
            <p>Done. Pages: {result.pages_processed ?? '—'}, Fields filled: {result.fields_filled ?? '—'}</p>
            {result.error && <p className="result-error">{result.error}</p>}
          </div>
        )}
        {status === 'error' && (
          <div className="sidebar-result error">
            {error && <p>{error}</p>}
            {result?.error && <p>{result.error}</p>}
          </div>
        )}
      </aside>
      <main className="apply-main">
        <div className="apply-instructions">
          <h1>Apply with autofill</h1>
          <p>
            Enter the job application URL in the sidebar and click <strong>Start autofill</strong>.
            A new browser window will open and use your saved profile to fill the form.
          </p>
          <p>
            Leave &quot;Run in background&quot; unchecked to see the browser. Make sure you have saved your profile (Candidate Details) first.
          </p>
        </div>
      </main>
      <style>{`
        .apply-page {
          display: flex;
          min-height: 100vh;
          background: #f5f5f5;
        }
        .apply-sidebar {
          width: 320px;
          min-width: 320px;
          padding: 1.5rem;
          background: #1a1a2e;
          color: #eee;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .sidebar-title {
          margin: 0 0 0.25rem 0;
          font-size: 1.25rem;
        }
        .sidebar-hint {
          margin: 0;
          font-size: 0.875rem;
          color: #aaa;
        }
        .sidebar-field {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .sidebar-field label {
          font-size: 0.8rem;
          font-weight: 500;
          color: #ccc;
        }
        .sidebar-field input[type="url"],
        .sidebar-field input[type="text"] {
          padding: 0.5rem 0.75rem;
          border: 1px solid #333;
          border-radius: 6px;
          background: #0f0f1a;
          color: #eee;
          font-size: 0.9rem;
        }
        .sidebar-field input:focus {
          outline: none;
          border-color: #646cff;
        }
        .checkbox-field label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
        }
        .sidebar-button {
          padding: 0.75rem 1.25rem;
          font-size: 1rem;
          font-weight: 600;
          color: white;
          background: #646cff;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          margin-top: 0.5rem;
        }
        .sidebar-button:hover:not(:disabled) {
          background: #535bf2;
        }
        .sidebar-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .sidebar-status.running {
          color: #fbbf24;
          font-size: 0.9rem;
        }
        .sidebar-result {
          font-size: 0.9rem;
          padding: 0.75rem;
          border-radius: 6px;
        }
        .sidebar-result.success {
          background: rgba(34, 197, 94, 0.2);
          color: #86efac;
        }
        .sidebar-result.error {
          background: rgba(239, 68, 68, 0.2);
          color: #fca5a5;
        }
        .result-error {
          margin: 0.5rem 0 0 0;
        }
        .apply-main {
          flex: 1;
          padding: 2rem;
          display: flex;
          align-items: flex-start;
          justify-content: center;
        }
        .apply-instructions {
          max-width: 480px;
        }
        .apply-instructions h1 {
          margin: 0 0 1rem 0;
          color: #1a1a2e;
        }
        .apply-instructions p {
          margin: 0 0 0.75rem 0;
          color: #444;
          line-height: 1.5;
        }
      `}</style>
    </div>
  );
}

export default ApplyPage;

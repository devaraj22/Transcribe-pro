import React, { useEffect, useMemo, useState } from 'react';
import { AudioRecorder } from '../forms/AudioRecorder';
import { FileUploader } from '../forms/FileUploader';
import { LanguageSelector } from '../forms/LanguageSelector';
import { TranscriptEditor } from '../TranscriptEditor';
import { ProgressBar } from '../ui/ProgressBar';
import { ApiClient } from '../../services/apiClient';
import { useJobPolling } from '../../hooks/useJobPolling';
import { HistoryItem } from '../../types';

export const QuickCaptureView: React.FC = () => {
  const [languageMode, setLanguageMode] = useState('automatic');
  const [jobId, setJobId] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [jobResult, setJobResult] = useState<{ full_text?: string; segments?: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const { status: pollStatus, progress, data: pollData, error: pollError } = useJobPolling(
    jobId,
    Boolean(jobId) && processing
  );

  const isQueued = pollStatus === 'queued' || Boolean(processing && jobId && pollStatus === 'idle');

  const currentStatusText = useMemo(() => {
    if (error) return 'Processing failed';
    if (processing && jobId) {
      if (pollStatus === 'complete') return 'Quick Capture completed';
      if (pollStatus === 'error') return 'Processing error';
      return 'Processing your recording';
    }
    return 'Ready to capture a short voice note';
  }, [error, jobId, pollStatus, processing]);

  const loadHistory = async () => {
    try {
      const logs = await ApiClient.fetchHistory();
      setHistory(logs);
    } catch (err) {
      console.error('Unable to fetch history', err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (!jobId || !processing) {
      return;
    }

    if (pollStatus === 'complete' && pollData) {
      setJobResult({
        full_text: pollData.full_text,
        segments: pollData.segments,
      });
      setProcessing(false);
      setError(null);
      setJobId(null);
      loadHistory();
    }

    if (pollStatus === 'error') {
      setError(pollError || 'Background job failed while processing the recording.');
      setProcessing(false);
      setJobId(null);
    }

    if (pollError) {
      setError(pollError);
      setProcessing(false);
      setJobId(null);
    }
  }, [jobId, pollStatus, pollData, processing, pollError]);

  const processFile = async (file: File) => {
    setError(null);
    setJobResult(null);
    setProcessing(true);

    try {
      const response = await ApiClient.processMedia(file, languageMode);
      setJobId(response.job_id);

      if (response.status === 'complete') {
        setJobResult({ full_text: response.full_text, segments: response.segments });
        setProcessing(false);
        setJobId(null);
        loadHistory();
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Short capture processing failed. Please try again.');
      setProcessing(false);
      setJobId(null);
    }
  };

  const handleDownloadTxt = () => {
    if (!jobResult?.full_text) {
      return;
    }

    const blob = new Blob([jobResult.full_text], { type: 'text/plain;charset=utf-8' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = 'voicescribe-quick-capture.txt';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  };

  const shareToWhatsApp = () => {
    if (!jobResult?.full_text) return;
    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(jobResult.full_text)}`;
    window.open(whatsappUrl, '_blank');
  };

  return (
    <div className="workspace-shell">
      <div className="workspace-main">
        <section className="hero-card">
          <div className="hero-copy">
            <div className="eyebrow">Live Workspace</div>
            <h2>Quick Capture Workspace</h2>
            <p>Record short audio notes or upload small media files for rapid transcription with a polished, modern workflow.</p>
          </div>
          <div className="hero-badge">{processing ? 'Processing' : 'Ready'}</div>
        </section>

        <section className="panel-card">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Capture & process</h3>
              <p className="panel-subtitle">Capture a clip, choose language mode, and submit for quick transcription.</p>
            </div>
            <LanguageSelector value={languageMode} onChange={setLanguageMode} />
          </div>

          <div className="control-stack">
            <AudioRecorder onRecordedFile={processFile} />
            <FileUploader onFileSelected={processFile} />
          </div>
        </section>

        <section className="panel-card">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Status</h3>
              <p className="panel-subtitle">{currentStatusText}</p>
            </div>
            <div className="status-pill-inline">{processing ? 'Working…' : 'Idle'}</div>
          </div>

          {(processing || isQueued) && <ProgressBar progress={progress || 10} label="Short capture in progress" />}

          {error && <div style={{ color: '#f87171', fontWeight: 700, marginTop: '12px' }}>{error}</div>}

          {jobResult?.full_text && (
            <div className="action-row" style={{ marginTop: '16px' }}>
              <button className="action-btn primary" onClick={shareToWhatsApp}>
                Share to WhatsApp
              </button>
              <button className="action-btn" onClick={handleDownloadTxt}>
                Download .txt
              </button>
            </div>
          )}
        </section>
      </div>

      <div className="workspace-side">
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Recent History</h3>
              <p className="panel-subtitle">Your latest quick capture sessions.</p>
            </div>
          </div>

          <div className="history-list">
            {history.length === 0 ? (
              <p className="empty-state">No recent quick capture sessions yet.</p>
            ) : (
              history.map((item) => (
                <div key={item.job_id} className="history-item">
                  <div className="top-line">
                    <span style={{ fontWeight: 700, color: '#f8fafc' }}>{item.title}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{item.status}</span>
                  </div>
                  <div className="meta-line">
                    <span>{item.timestamp}</span>
                    <span>{item.job_id.slice(0, 8)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel-card transcript-shell">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Transcript Viewer</h3>
              <p className="panel-subtitle">Live output for the selected result.</p>
            </div>
          </div>
          <TranscriptEditor fullText={jobResult?.full_text} segments={jobResult?.segments} loading={processing && isQueued} />
        </section>
      </div>
    </div>
  );
};

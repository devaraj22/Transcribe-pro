import React, { useEffect, useMemo, useState } from 'react';
import { AudioRecorder } from '../forms/AudioRecorder';
import { FileUploader } from '../forms/FileUploader';
import { LanguageSelector } from '../forms/LanguageSelector';
import { TranscriptEditor } from '../TranscriptEditor';
import { ProgressBar } from '../ui/ProgressBar';
import { ApiClient } from '../../services/apiclient';
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
      setError('Background job failed while processing the recording.');
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
      setError('Short capture processing failed. Please try again.');
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
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-main)' }}>Quick Capture Workspace</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', lineHeight: 1.5 }}>
            Record short audio notes or upload small media files for rapid transcription. The same unified VoiceScribe engine powers your quick notes.
          </p>
        </div>

        <div style={{ display: 'grid', gap: '24px' }}>
          <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Capture & process</h3>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
                  Capture a clip, choose language mode, and submit for quick transcription.
                </p>
              </div>
              <LanguageSelector value={languageMode} onChange={setLanguageMode} />
            </div>

            <div style={{ display: 'grid', gap: '20px' }}>
              <AudioRecorder onRecordedFile={processFile} />
              <FileUploader onFileSelected={processFile} />
            </div>
          </div>

          <div style={{ display: 'grid', gap: '16px', padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Status</h3>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>{currentStatusText}</p>
              </div>
              <div style={{ color: processing ? 'var(--accent)' : 'var(--text-muted)', fontWeight: 700 }}>{processing ? 'Working…' : 'Idle'}</div>
            </div>

            {(processing || isQueued) && <ProgressBar progress={progress || 10} label="Short capture in progress" />}

            {error && <div style={{ color: '#dc2626', fontWeight: 600 }}>{error}</div>}

            {jobResult?.full_text && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <button
                  onClick={shareToWhatsApp}
                  style={{ padding: '12px 18px', borderRadius: '12px', border: 'none', backgroundColor: 'var(--accent)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
                >
                  Share to WhatsApp
                </button>
                <button
                  onClick={handleDownloadTxt}
                  style={{ padding: '12px 18px', borderRadius: '12px', border: '1px solid var(--border-color)', backgroundColor: 'transparent', color: 'var(--text-main)', fontWeight: 700, cursor: 'pointer' }}
                >
                  Download .txt
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
        <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Recent Quick Capture History</h3>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'grid', gap: '14px' }}>
            {history.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No recent quick capture sessions yet.</p>
            ) : (
              history.map((item) => (
                <div
                  key={item.job_id}
                  style={{
                    padding: '14px',
                    borderRadius: '14px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{item.title}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{item.status}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    <span>{item.timestamp}</span>
                    <span>{item.job_id.slice(0, 8)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ flex: 1, padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)', overflowY: 'auto' }}>
          <TranscriptEditor fullText={jobResult?.full_text} segments={jobResult?.segments} loading={processing && isQueued} />
        </div>
      </div>
    </div>
  );
};

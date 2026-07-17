import React, { useEffect, useState } from 'react';
import { LanguageSelector } from '../forms/LanguageSelector';
import { FileUploader } from '../forms/FileUploader';
import { TranscriptEditor } from '../TranscriptEditor';
import { VectorChatWidget } from '../VectorChatWidget';
import { ProgressBar } from '../ui/ProgressBar';
import { ApiClient } from '../../services/apiClient';
import { useJobPolling } from '../../hooks/useJobPolling';

export const MeetingModeView: React.FC = () => {
  const [languageMode, setLanguageMode] = useState('automatic');
  const [jobId, setJobId] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [jobResult, setJobResult] = useState<{ full_text?: string; segments?: any[] } | null>(null);
  const [summary, setSummary] = useState<string>('');
  const [actionItems, setActionItems] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const { status: pollStatus, progress, data: pollData, error: pollError } = useJobPolling(
    jobId,
    Boolean(jobId) && processing
  );

  useEffect(() => {
    if (!jobId || !processing) return;

    if (pollStatus === 'complete' && pollData) {
      setJobResult({
        full_text: pollData.full_text,
        segments: pollData.segments,
      });
      setProcessing(false);
      setError(null);
    }

    if (pollStatus === 'error') {
      setError('Meeting processing failed. Please try again or upload a smaller file.');
      setProcessing(false);
      setJobId(null);
    }

    if (pollError) {
      setError(String(pollError));
      setProcessing(false);
      setJobId(null);
    }
  }, [jobId, pollStatus, pollData, pollError, processing]);

  useEffect(() => {
    if (!jobResult?.full_text) {
      return;
    }

    const enrich = async () => {
      try {
        const [summaryResponse, actionsResponse] = await Promise.all([
          ApiClient.summarizeText(jobResult.full_text || ''),
          ApiClient.extractActionItems(jobResult.full_text || ''),
        ]);
        setSummary(summaryResponse.summary || 'No summary available.');
        setActionItems(actionsResponse.action_items || []);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        console.error('Enhancement fetch failed', err);
        
        // Display error to user
        if (errorMessage.includes('503') || errorMessage.includes('Ollama')) {
          setError('AI enhancement unavailable: Please ensure Ollama is running on localhost:11434 with qwen3:8b model.');
        } else {
          setError(`Enhancement failed: ${errorMessage}`);
        }
        
        // Still show placeholder text
        setSummary('Unable to generate summary. Please check if Ollama service is running.');
        setActionItems([]);
      }
    };

    enrich();
  }, [jobResult]);

  const processFile = async (file: File) => {
    setError(null);
    setJobResult(null);
    setSummary('');
    setActionItems([]);
    setProcessing(true);

    try {
      const response = await ApiClient.processMedia(file, languageMode);
      setJobId(response.job_id);

      if (response.status === 'complete') {
        setJobResult({ full_text: response.full_text, segments: response.segments });
        setProcessing(false);
      }
    } catch (err) {
      console.error(err);
      setError('Meeting mode upload failed. Please try again.');
      setProcessing(false);
      setJobId(null);
    }
  };

  const downloadReport = async () => {
    if (!jobResult?.full_text) return;
    setReportLoading(true);

    try {
      const reportBlob = await ApiClient.downloadReport({
        title: 'VoiceScribe Meeting Report',
        summary,
        action_items: actionItems,
        full_text: jobResult.full_text,
      });

      const anchor = document.createElement('a');
      anchor.href = URL.createObjectURL(reportBlob);
      anchor.download = 'voicescribe_meeting_report.pdf';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
    } catch (err) {
      console.error('Report generation error', err);
      setError('Unable to generate PDF report at this time.');
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      <div>
        <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-main)' }}>Meeting Mode Workspace</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '15px', lineHeight: 1.5 }}>
          Deep analysis workspace for longer recordings and videos. After processing, review speaker-labeled transcripts, summaries, action items, and use RAG-powered chat.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Upload meeting media</h3>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
                  Upload audio or video and let VoiceScribe run the unified meeting pipeline.
                </p>
              </div>
              <LanguageSelector value={languageMode} onChange={setLanguageMode} />
            </div>

            <FileUploader
              acceptedTypes="audio/mp3, audio/wav, audio/m4a, video/mp4, video/webm, video/quicktime"
              label="Upload meeting audio or video"
              helpText="Supports audio and video containers for meeting transcription."
              onFileSelected={processFile}
            />
          </div>

          <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '18px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Meeting insights</h3>
                <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
                  After processing, VoiceScribe generates a structured summary and action item list for follow-up.
                </p>
              </div>
              <button
                onClick={downloadReport}
                disabled={!jobResult?.full_text || reportLoading}
                style={{
                  padding: '12px 18px',
                  borderRadius: '12px',
                  border: 'none',
                  backgroundColor: !jobResult?.full_text || reportLoading ? 'var(--text-muted)' : 'var(--accent)',
                  color: '#fff',
                  fontWeight: 700,
                  cursor: !jobResult?.full_text || reportLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {reportLoading ? 'Generating...' : 'Download Report'}
              </button>
            </div>

            <div style={{ display: 'grid', gap: '16px' }}>
              <div style={{ padding: '18px', borderRadius: '16px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-color)' }}>
                <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-main)', fontWeight: 700 }}>Summary</h4>
                <p style={{ marginTop: '10px', color: 'var(--text-muted)', fontSize: '14px' }}>
                  {summary || 'Summary will appear here once the meeting transcript is available.'}
                </p>
              </div>

              <div style={{ padding: '18px', borderRadius: '16px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-color)' }}>
                <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-main)', fontWeight: 700 }}>Action Items</h4>
                {actionItems.length > 0 ? (
                  <ul style={{ marginTop: '10px', color: 'var(--text-main)', fontSize: '14px', lineHeight: 1.75 }}>
                    {actionItems.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ marginTop: '10px', color: 'var(--text-muted)', fontSize: '14px' }}>
                    Action items are extracted automatically once your transcript is ready.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
          <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--text-main)' }}>Transcript & diarization</h3>
              <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{processing ? 'Processing…' : 'Ready'}</span>
            </div>
            {processing && <ProgressBar progress={progress || 20} label="Meeting processing in progress" />}
            {error && <div style={{ color: '#dc2626', fontWeight: 600, marginTop: '12px' }}>{error}</div>}
            <TranscriptEditor fullText={jobResult?.full_text} segments={jobResult?.segments} loading={processing} />
          </div>

          <div style={{ padding: '28px', border: '1px solid var(--border-color)', borderRadius: '18px', backgroundColor: 'var(--bg-surface)', minHeight: '420px' }}>
            <VectorChatWidget jobId={jobResult?.full_text ? jobId : null} />
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { TranscriptSegment } from '../types';

interface TranscriptEditorProps {
  fullText?: string;
  segments?: TranscriptSegment[];
  loading?: boolean;
}

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({ fullText, segments, loading = false }) => {
  if (loading) {
    return (
      <div style={{ padding: '24px', borderRadius: '16px', backgroundColor: 'var(--bg-surface)', flex: 1 }}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Transcript</h3>
        <p style={{ marginTop: '12px', color: 'var(--text-muted)' }}>
          Processing the file and preparing speaker-labeled text. Please wait for the final transcript.
        </p>
      </div>
    );
  }

  if (!fullText && (!segments || segments.length === 0)) {
    return (
      <div style={{ padding: '24px', borderRadius: '16px', backgroundColor: 'var(--bg-surface)', flex: 1 }}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Transcript Viewer</h3>
        <p style={{ marginTop: '12px', color: 'var(--text-muted)' }}>
          Upload a meeting audio/video file to generate a transcript, speaker diarization, and an AI-enhanced report.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Living Transcript</h3>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {segments && segments.length > 0 ? (
          segments.map((segment, index) => (
            <div key={index} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
              <div style={{ minWidth: '68px', color: 'var(--accent)', fontSize: '13px', fontWeight: 700 }}>
                {segment.start != null && segment.end != null
                  ? `${Math.floor(segment.start / 60)}:${String(segment.start % 60).padStart(2, '0')}`
                  : '00:00'}
              </div>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.75, color: 'var(--text-main)' }}>
                  <strong>{segment.speaker ? `${segment.speaker}: ` : ''}</strong>
                  {segment.text}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div style={{ padding: '18px', borderRadius: '16px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'inherit', color: 'var(--text-main)', lineHeight: 1.65 }}>
              {fullText}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

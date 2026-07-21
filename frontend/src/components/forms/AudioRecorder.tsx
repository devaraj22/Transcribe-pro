import React from 'react';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';

interface AudioRecorderProps {
  onRecordedFile: (file: File) => void;
}

export const AudioRecorder: React.FC<AudioRecorderProps> = ({ onRecordedFile }) => {
  const {
    isRecording,
    audioUrl,
    recordedFile,
    duration,
    error,
    startRecording,
    stopRecording,
    resetRecorder,
  } = useAudioRecorder();

  const handleUpload = () => {
    if (recordedFile) {
      onRecordedFile(recordedFile);
      resetRecorder();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '20px' }}>Voice Note Recorder</h3>
          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
            
          </p>
        </div>
        <button
          onClick={isRecording ? stopRecording : startRecording}
          style={{
            width: '72px',
            height: '72px',
            borderRadius: '50%',
            border: 'none',
            backgroundColor: isRecording ? '#fee2e2' : 'var(--accent-light)',
            color: isRecording ? '#dc2626' : 'var(--accent)',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            transition: 'all 0.25s ease',
            display: 'grid',
            placeItems: 'center',
          }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" x2="12" y1="19" y2="22" />
          </svg>
        </button>
      </div>

      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <div
          style={{
            flex: 1,
            padding: '20px',
            borderRadius: '16px',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <div style={{ marginBottom: '', display: '', alignItems: 'center', gap: '' }}>
           
            {isRecording && <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>• {duration}s</span>}
          </div>
         
        </div>

        {audioUrl && (
          <audio controls src={audioUrl} style={{ minWidth: '230px', width: '100%' }} />
        )}
      </div>

      {recordedFile && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          <button
            type="button"
            onClick={handleUpload}
            style={{
              padding: '12px 22px',
              borderRadius: '12px',
              border: 'none',
              backgroundColor: 'var(--accent)',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Submit Recording
          </button>
          <button
            type="button"
            onClick={resetRecorder}
            style={{
              padding: '12px 22px',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'transparent',
              color: 'var(--text-main)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Discard
          </button>
        </div>
      )}

      {error && <p style={{ color: '#dc2626', fontSize: '13px' }}>{error}</p>}
    </div>
  );
};

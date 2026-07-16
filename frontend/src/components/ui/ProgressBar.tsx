import React from 'react';

interface ProgressBarProps {
  progress: number;
  label?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, label }) => {
  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {label && <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{label}</span>}
      <div style={{ width: '100%', height: '12px', borderRadius: '999px', backgroundColor: 'var(--border-color)', overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(100, Math.max(0, progress))}%`,
            height: '100%',
            backgroundColor: 'var(--accent)',
            transition: 'width 0.25s ease',
          }}
        />
      </div>
    </div>
  );
};

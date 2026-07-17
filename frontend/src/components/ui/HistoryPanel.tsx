import React, { useEffect, useState } from 'react';
import { X, Clock } from 'lucide-react';
import { ApiClient } from '../../services/apiClient';
import { HistoryItem } from '../../types';

interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectJob: (jobId: string) => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ isOpen, onClose, onSelectJob }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const logs = await ApiClient.fetchHistory();
        setHistory(logs);
      } catch (err) {
        setError('Unable to load history.');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '340px',
      height: '100vh',
      backgroundColor: 'var(--bg-surface)',
      borderLeft: '1px solid var(--border-color)',
      padding: '24px',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '-10px 0 25px rgba(0,0,0,0.08)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600' }}>
          <Clock size={18} color="var(--accent)" />
          <span>Job History Logs</span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
          <X size={20} />
        </button>
      </div>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Loading recent jobs...</p>}
      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {!loading && history.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
          No historical log instances stored in memory cache yet. (Capped to 5 instances)
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
        {history.map((item) => (
          <button
            key={item.job_id}
            onClick={() => onSelectJob(item.job_id)}
            style={{
              textAlign: 'left',
              width: '100%',
              padding: '14px',
              borderRadius: '14px',
              backgroundColor: 'var(--bg-main)',
              border: '1px solid var(--border-color)',
              cursor: 'pointer',
              color: 'var(--text-main)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 700 }}>{item.title}</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{item.status}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>
              <span>{item.timestamp}</span>
              <span>{item.job_id.slice(0, 8)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

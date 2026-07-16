import React from 'react';

// Dummy data to show how the table will look
const mockJobs = [
  { id: 'JOB-9021', name: 'Q3_Earnings_Call.mp3', date: 'Oct 24, 2023', duration: '45:21', status: 'Completed' },
  { id: 'JOB-9022', name: 'Product_Sync_Weekly.wav', date: 'Oct 25, 2023', duration: '12:05', status: 'Completed' },
  { id: 'JOB-9023', name: 'Interview_Candidate_A.m4a', date: 'Oct 25, 2023', duration: '--:--', status: 'Processing' },
  { id: 'JOB-9024', name: 'Corrupted_Audio_File.mp3', date: 'Oct 26, 2023', duration: '00:00', status: 'Failed' }
];

export const JobHistoryView: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      <div>
        <h2 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Processing Logs</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '15px', lineHeight: '1.5' }}>
          Track the status of your transcription and vector indexing jobs.
        </p>
      </div>

      <div style={{ 
        backgroundColor: 'var(--bg-surface)', 
        border: '1px solid var(--border-color)', 
        borderRadius: '12px', 
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead style={{ backgroundColor: 'var(--bg-main)', borderBottom: '1px solid var(--border-color)' }}>
            <tr>
              <th style={{ padding: '16px 24px', fontSize: '13px', color: 'var(--text-muted)', fontWeight: '600' }}>Job ID</th>
              <th style={{ padding: '16px 24px', fontSize: '13px', color: 'var(--text-muted)', fontWeight: '600' }}>File Name</th>
              <th style={{ padding: '16px 24px', fontSize: '13px', color: 'var(--text-muted)', fontWeight: '600' }}>Date</th>
              <th style={{ padding: '16px 24px', fontSize: '13px', color: 'var(--text-muted)', fontWeight: '600' }}>Duration</th>
              <th style={{ padding: '16px 24px', fontSize: '13px', color: 'var(--text-muted)', fontWeight: '600' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {mockJobs.map((job, index) => (
              <tr key={job.id} style={{ borderBottom: index !== mockJobs.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                <td style={{ padding: '16px 24px', fontSize: '14px', color: 'var(--text-main)', fontWeight: '500' }}>{job.id}</td>
                <td style={{ padding: '16px 24px', fontSize: '14px', color: 'var(--accent)', fontWeight: '500', cursor: 'pointer' }}>{job.name}</td>
                <td style={{ padding: '16px 24px', fontSize: '14px', color: 'var(--text-main)' }}>{job.date}</td>
                <td style={{ padding: '16px 24px', fontSize: '14px', color: 'var(--text-main)' }}>{job.duration}</td>
                <td style={{ padding: '16px 24px' }}>
                  <span style={{
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: job.status === 'Completed' ? '#d1fae5' : job.status === 'Processing' ? '#fef3c7' : '#fee2e2',
                    color: job.status === 'Completed' ? '#059669' : job.status === 'Processing' ? '#d97706' : '#dc2626'
                  }}>
                    {job.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
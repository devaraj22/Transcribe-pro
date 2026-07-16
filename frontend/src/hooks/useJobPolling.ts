import { useEffect, useState } from 'react';
import { ApiClient } from '../services/apiclient';

export function useJobPolling(
  jobId: string | null,
  enabled: boolean,
  intervalMs = 1500
) {
  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId || !enabled) {
      return;
    }

    let cancelled = false;
    let intervalHandle: number;

    const poll = async () => {
      try {
        const response = await ApiClient.checkJobStatus(jobId);
        if (cancelled) return;

        setStatus(response.status || 'unknown');
        setProgress(response.progress ?? 0);
        setData(response.data ?? null);

        if (response.status === 'complete' || response.status === 'error') {
          window.clearInterval(intervalHandle);
        }
      } catch (err) {
        if (cancelled) return;
        setError(String(err));
        window.clearInterval(intervalHandle);
      }
    };

    poll();
    intervalHandle = window.setInterval(poll, intervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(intervalHandle);
    };
  }, [enabled, intervalMs, jobId]);

  return { status, progress, data, error };
}

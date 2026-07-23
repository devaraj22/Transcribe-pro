import { useEffect, useState } from 'react';
import { ApiClient } from '../services/apiClient';

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
      setStatus('idle');
      setProgress(0);
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;
    let intervalHandle: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const response = await ApiClient.checkJobStatus(jobId);
        if (cancelled) return;

        setStatus(response.status || 'unknown');
        setProgress(response.progress ?? 0);

        if (response.data) {
          setData(response.data);
        }

        if (response.status === 'error') {
          setError(response.error || 'Processing failed');
          if (intervalHandle) clearInterval(intervalHandle);
        } else if (response.status === 'complete') {
          if (intervalHandle) clearInterval(intervalHandle);
        }
      } catch (err: any) {
        if (cancelled) return;
        setError(err.message || String(err));
        setStatus('error');
        if (intervalHandle) clearInterval(intervalHandle);
      }
    };

    poll();
    intervalHandle = setInterval(poll, intervalMs);

    return () => {
      cancelled = true;
      if (intervalHandle) clearInterval(intervalHandle);
    };
  }, [enabled, intervalMs, jobId]);

  return { status, progress, data, error };
}
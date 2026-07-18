/**
 * apiClient.ts
 * ============
 * Centralised HTTP client for the VoiceScribe AI backend.
 *
 * All methods throw on non-2xx responses so callers can catch and surface
 * errors in the UI. The base URL is read from the VITE_API_BASE_URL env var
 * so it works in both dev (localhost:8000) and production.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

export const ApiClient = {
  // ─────────────────────────────────────────────────────────────────────────
  // Processing
  // ─────────────────────────────────────────────────────────────────────────

  async processMedia(file: File, languageMode: string = 'automatic'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language_mode', languageMode);

    const response = await fetch(`${API_BASE_URL}/process/`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Processing failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  async checkJobStatus(jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/process/${jobId}`);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Status check failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // Subtitle download
  // ─────────────────────────────────────────────────────────────────────────

  downloadSubtitle(jobId: string, fmt: 'ass' | 'srt' = 'ass'): void {
    /** Triggers a browser download for the subtitle file. No async needed. */
    const url = `${API_BASE_URL}/process/${jobId}/subtitle.${fmt}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${jobId}.${fmt}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  },

  // ─────────────────────────────────────────────────────────────────────────
  // GPU / model management
  // ─────────────────────────────────────────────────────────────────────────

  async flushModels(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/process/flush`, { method: 'POST' });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Flush failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // RAG / Vector Q&A
  // ─────────────────────────────────────────────────────────────────────────

  async checkRagIndexStatus(jobId: string): Promise<{ indexed: boolean; job_id: string }> {
    const response = await fetch(`${API_BASE_URL}/rag/status/${jobId}`);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`RAG status check failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  async queryVectorDB(question: string, jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/rag/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, job_id: jobId }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Vector query failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // History
  // ─────────────────────────────────────────────────────────────────────────

  async fetchHistory(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/history/`);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`History fetch failed (${response.status}): ${text}`);
    }
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // AI Enhancement (Ollama)
  // ─────────────────────────────────────────────────────────────────────────

  async summarizeText(text: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/enhance/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const textBody = await response.text();
      throw new Error(`Summary failed (${response.status}): ${textBody}`);
    }
    return response.json();
  },

  async extractActionItems(text: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/enhance/action-items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const textBody = await response.text();
      throw new Error(`Action items failed (${response.status}): ${textBody}`);
    }
    return response.json();
  },

  // ─────────────────────────────────────────────────────────────────────────
  // PDF Report
  // ─────────────────────────────────────────────────────────────────────────

  async downloadReport(payload: {
    title?: string;
    summary?: string;
    action_items?: string[];
    full_text: string;
  }): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/report/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const textBody = await response.text();
      throw new Error(`PDF download failed (${response.status}): ${textBody}`);
    }
    return response.blob();
  },
};
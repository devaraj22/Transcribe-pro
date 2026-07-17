// Define the base URL for your backend. The Vite env var lets the UI match the
// backend port without hard-coding a single localhost URL in the source tree.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');

export const ApiClient = {
  async processMedia(file: File, languageMode: string = 'automatic'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language_mode', languageMode);

    try {
      const response = await fetch(`${API_BASE_URL}/process/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Processing failed with status ${response.status}: ${text}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Process error in ApiClient:', error);
      throw error;
    }
  },

  async checkJobStatus(jobId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/process/${jobId}`);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Status check failed with status ${response.status}: ${text}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Job status error in ApiClient:', error);
      throw error;
    }
  },

  async queryVectorDB(question: string, jobId: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/rag/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question, job_id: jobId }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Vector query failed with status: ${response.status}: ${text}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Query error in ApiClient:', error);
      throw error;
    }
  },

  async fetchHistory(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/history/`);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`History fetch failed with status ${response.status}: ${text}`);
      }
      return await response.json();
    } catch (error) {
      console.error('History fetch error in ApiClient:', error);
      throw error;
    }
  },

  async summarizeText(text: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/enhance/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        const textBody = await response.text();
        throw new Error(`Summary failed with status ${response.status}: ${textBody}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Summary error in ApiClient:', error);
      throw error;
    }
  },

  async extractActionItems(text: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/enhance/action-items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        const textBody = await response.text();
        throw new Error(`Action items failed with status ${response.status}: ${textBody}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Action items error in ApiClient:', error);
      throw error;
    }
  },

  async downloadReport(payload: { title?: string; summary?: string; action_items?: string[]; full_text: string }) {
    try {
      const response = await fetch(`${API_BASE_URL}/report/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const textBody = await response.text();
        throw new Error(`PDF download failed with status ${response.status}: ${textBody}`);
      }

      const blob = await response.blob();
      return blob;
    } catch (error) {
      console.error('Download report error in ApiClient:', error);
      throw error;
    }
  },
};
// ==========================================
// Word-level timing (for karaoke highlighting)
// ==========================================
export interface WordTiming {
  word: string;
  start: number;
  end: number;
  score?: number;
}

// ==========================================
// Core transcript types
// ==========================================
export interface TranscriptSegment {
  speaker?: string;
  start?: number;
  end?: number;
  language?: string;
  text: string;
  /** Word-level timing entries — present when WhisperX alignment is used */
  words?: WordTiming[];
}

export interface ProcessResponse {
  job_id: string;
  status: string;
  message: string;
  full_text?: string;
  segments?: Array<TranscriptSegment>;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  data?: {
    full_text?: string;
    segments?: Array<TranscriptSegment>;
  };
}

export interface HistoryItem {
  job_id: string;
  title: string;
  status: string;
  timestamp: string;
}

export interface RAGResponse {
  answer: string;
  sources: string[];
}

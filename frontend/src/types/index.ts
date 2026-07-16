export interface HistoryItem {
  job_id: string;
  title: string;
  status: string;
  timestamp: string;
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

export interface TranscriptSegment {
  speaker?: string;
  start?: number;
  end?: number;
  text: string;
}

export interface RAGResponse {
  answer: string;
  sources: string[];
}

import React, { useState, useEffect, useRef } from 'react';
import { ApiClient } from '../services/apiClient';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'ai';
  sources?: string[];
  isError?: boolean;
}

interface VectorChatWidgetProps {
  /** job_id returned by the backend after successful processing */
  jobId: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export const VectorChatWidget: React.FC<VectorChatWidgetProps> = ({ jobId }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: 'Hello! Ask me anything about the transcript once processing is complete.',
      sender: 'ai',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Track whether the FAISS index is ready for this job
  const [indexReady, setIndexReady] = useState(false);
  const [indexChecking, setIndexChecking] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Auto-scroll to newest message ─────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Poll /rag/status/{jobId} until the index is ready ────────────────────
  useEffect(() => {
    if (!jobId) {
      setIndexReady(false);
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    // Reset when jobId changes
    setIndexReady(false);
    setIndexChecking(true);

    const checkIndex = async () => {
      try {
        const status = await ApiClient.checkRagIndexStatus(jobId);
        if (status.indexed) {
          setIndexReady(true);
          setIndexChecking(false);
          if (pollRef.current) clearInterval(pollRef.current);
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              text: '✅ Transcript index is ready. What would you like to know?',
              sender: 'ai',
            },
          ]);
        }
      } catch {
        // Backend may not be ready yet — keep polling silently
      }
    };

    checkIndex(); // Immediate check
    pollRef.current = setInterval(checkIndex, 3000); // Then every 3 s

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  // ── Send a question ────────────────────────────────────────────────────────
  const handleSend = async () => {
    const question = inputValue.trim();
    if (!question || !jobId || !indexReady) return;

    setInputValue('');
    const userMsg: Message = { id: Date.now(), text: question, sender: 'user' };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await ApiClient.queryVectorDB(question, jobId);
      const aiText = response.answer || 'I could not find a relevant answer in the transcript.';
      const sources: string[] = response.sources || [];

      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, text: aiText, sender: 'ai', sources },
      ]);
    } catch (error: any) {
      const errText =
        error?.message?.includes('404')
          ? 'The transcript index is not available yet. Please wait a moment and try again.'
          : 'Unable to reach the RAG engine. Please check that the backend is running.';
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, text: errText, sender: 'ai', isError: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) handleSend();
  };

  // ── Status badge ───────────────────────────────────────────────────────────
  const statusLabel = !jobId
    ? 'No transcript loaded'
    : indexReady
    ? '✅ Index ready'
    : indexChecking
    ? '⏳ Building index…'
    : 'Waiting…';

  const inputDisabled = !jobId || !indexReady || isLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '0' }}>
      {/* Header */}
      <div
        style={{
          marginBottom: '16px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ fontSize: '18px', color: 'var(--text-main)', fontWeight: 700, margin: 0 }}>
            Transcript Q&A
          </h3>
          <span
            style={{
              fontSize: '12px',
              color: indexReady ? '#34d399' : 'var(--text-muted)',
              fontWeight: 600,
              padding: '3px 10px',
              borderRadius: '999px',
              backgroundColor: indexReady ? 'rgba(52,211,153,0.1)' : 'var(--bg-main)',
              border: `1px solid ${indexReady ? 'rgba(52,211,153,0.3)' : 'var(--border-color)'}`,
            }}
          >
            {statusLabel}
          </span>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
          {jobId
            ? indexReady
              ? 'Ask questions grounded in the processed transcript.'
              : 'The FAISS index is being built — this usually takes a few seconds.'
            : 'Upload and process a recording to enable grounded Q&A.'}
        </p>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          paddingRight: '4px',
          marginBottom: '16px',
          minHeight: 0,
        }}
      >
        {messages.map((msg) => (
          <div key={msg.id}>
            <div
              style={{
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                backgroundColor: msg.isError
                  ? 'rgba(239,68,68,0.08)'
                  : msg.sender === 'user'
                  ? 'var(--bg-main)'
                  : 'var(--accent-light, rgba(99,102,241,0.08))',
                padding: '12px 16px',
                borderRadius:
                  msg.sender === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                border: msg.isError
                  ? '1px solid rgba(239,68,68,0.3)'
                  : msg.sender === 'user'
                  ? '1px solid var(--border-color)'
                  : 'none',
                maxWidth: '92%',
                display: 'inline-block',
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontSize: '14px',
                  color: msg.isError
                    ? '#f87171'
                    : msg.sender === 'user'
                    ? 'var(--text-main)'
                    : 'var(--accent, #6366f1)',
                  lineHeight: 1.65,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {msg.text}
              </p>
            </div>

            {/* Source citations */}
            {msg.sources && msg.sources.length > 0 && (
              <details
                style={{
                  marginTop: '6px',
                  marginLeft: '4px',
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <summary style={{ userSelect: 'none' }}>
                  📎 {msg.sources.length} source excerpt{msg.sources.length > 1 ? 's' : ''}
                </summary>
                <div
                  style={{
                    marginTop: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  {msg.sources.slice(0, 3).map((src, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-color)',
                        fontSize: '12px',
                        lineHeight: 1.55,
                        color: 'var(--text-main)',
                      }}
                    >
                      {src.length > 250 ? src.slice(0, 250) + '…' : src}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}

        {isLoading && (
          <div
            style={{
              alignSelf: 'flex-start',
              backgroundColor: 'var(--accent-light, rgba(99,102,241,0.08))',
              padding: '12px 16px',
              borderRadius: '14px',
              maxWidth: '85%',
            }}
          >
            <p
              style={{
                margin: 0,
                fontSize: '14px',
                color: 'var(--accent, #6366f1)',
                fontStyle: 'italic',
              }}
            >
              Searching transcript and generating answer…
            </p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            inputDisabled
              ? indexChecking
                ? 'Building index…'
                : 'Waiting for transcript…'
              : 'Ask a question about the transcript…'
          }
          disabled={inputDisabled}
          style={{
            flex: 1,
            padding: '12px 14px',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            outline: 'none',
            fontSize: '14px',
            backgroundColor: inputDisabled ? 'var(--bg-main)' : '#fff',
            color: 'var(--text-main)',
            transition: 'border-color 0.15s',
          }}
          onFocus={(e) => {
            if (!inputDisabled) e.currentTarget.style.borderColor = 'var(--accent, #6366f1)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-color)';
          }}
        />
        <button
          onClick={handleSend}
          disabled={inputDisabled || !inputValue.trim()}
          style={{
            padding: '12px 20px',
            borderRadius: '12px',
            border: 'none',
            backgroundColor:
              inputDisabled || !inputValue.trim() ? 'var(--text-muted)' : 'var(--accent, #6366f1)',
            color: '#fff',
            fontWeight: 700,
            cursor: inputDisabled || !inputValue.trim() ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.15s',
            whiteSpace: 'nowrap',
          }}
        >
          Ask
        </button>
      </div>
    </div>
  );
};

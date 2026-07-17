import React, { useState } from 'react';
import { ApiClient } from '../services/apiClient';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'ai';
}

interface VectorChatWidgetProps {
  jobId: string | null;
}

export const VectorChatWidget: React.FC<VectorChatWidgetProps> = ({ jobId }) => {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: 'Hello! I am ready to answer questions once the meeting transcript is available.', sender: 'ai' },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!inputValue.trim() || !jobId) {
      return;
    }

    const userText = inputValue.trim();
    setInputValue('');
    const userMsg: Message = { id: Date.now(), text: userText, sender: 'user' };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await ApiClient.queryVectorDB(userText, jobId);
      const aiText = response.answer || response.message || 'I could not find an answer in the transcript.';
      const aiMsg: Message = { id: Date.now() + 1, text: aiText, sender: 'ai' };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      const errorMsg: Message = {
        id: Date.now() + 1,
        text: 'Unable to reach the RAG engine. Please make sure processing is complete and try again.',
        sender: 'ai',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
        <h3 style={{ fontSize: '18px', color: 'var(--text-main)', fontWeight: '700' }}>Vector Q&A</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
          {jobId ? 'Ask questions grounded in the processed transcript.' : 'Upload a meeting recording to enable vector-based Q&A.'}
        </p>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px', paddingRight: '8px', marginBottom: '16px' }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: msg.sender === 'user' ? 'var(--bg-main)' : 'var(--accent-light)',
              padding: '14px 16px',
              borderRadius: msg.sender === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              border: msg.sender === 'user' ? '1px solid var(--border-color)' : 'none',
              maxWidth: '90%',
            }}
          >
            <p style={{ margin: 0, fontSize: '14px', color: msg.sender === 'user' ? 'var(--text-main)' : 'var(--accent)', lineHeight: 1.6 }}>
              {msg.text}
            </p>
          </div>
        ))}

        {isLoading && (
          <div style={{ alignSelf: 'flex-start', backgroundColor: 'var(--accent-light)', padding: '12px 16px', borderRadius: '14px', maxWidth: '85%' }}>
            <p style={{ margin: 0, fontSize: '14px', color: 'var(--accent)', fontStyle: 'italic' }}>Querying the transcript...</p>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={jobId ? 'Type your question...' : 'Waiting for transcript...' }
          disabled={!jobId || isLoading}
          style={{
            flex: 1,
            padding: '12px',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            outline: 'none',
            fontSize: '14px',
            backgroundColor: !jobId ? 'var(--bg-main)' : '#ffffff',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!jobId || isLoading || !inputValue.trim()}
          style={{
            padding: '12px 20px',
            borderRadius: '12px',
            border: 'none',
            backgroundColor: !jobId || !inputValue.trim() ? 'var(--text-muted)' : 'var(--accent)',
            color: 'white',
            fontWeight: 600,
            cursor: !jobId || !inputValue.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
};

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { TranscriptSegment, WordTiming } from '../types';

// ─────────────────────────────────────────────────────────────────────────────
// Speaker colour palette  (distinct, accessible, dark-mode safe)
// ─────────────────────────────────────────────────────────────────────────────
const SPEAKER_PALETTE: Record<string, string> = {};
const PALETTE_COLOURS = [
  '#60a5fa', // blue-400
  '#f472b6', // pink-400
  '#34d399', // emerald-400
  '#fbbf24', // amber-400
  '#a78bfa', // violet-400
  '#fb923c', // orange-400
  '#22d3ee', // cyan-400
  '#e879f9', // fuchsia-400
];

function getSpeakerColour(speaker: string): string {
  if (!SPEAKER_PALETTE[speaker]) {
    const idx = Object.keys(SPEAKER_PALETTE).length % PALETTE_COLOURS.length;
    SPEAKER_PALETTE[speaker] = PALETTE_COLOURS[idx];
  }
  return SPEAKER_PALETTE[speaker];
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Word-level highlighting sub-component
// ─────────────────────────────────────────────────────────────────────────────
interface WordDisplayProps {
  words: WordTiming[];
  /** Current audio playback position in seconds (undefined = no audio attached) */
  currentTime?: number;
  colour: string;
}

const WordDisplay: React.FC<WordDisplayProps> = ({ words, currentTime, colour }) => {
  if (!words || words.length === 0) return null;

  return (
    <span style={{ display: 'inline' }}>
      {words.map((w, idx) => {
        const isActive =
          currentTime !== undefined &&
          currentTime >= w.start &&
          currentTime < w.end;
        return (
          <span
            key={idx}
            title={`${formatTimestamp(w.start)} – ${formatTimestamp(w.end)}`}
            style={{
              display: 'inline',
              padding: '1px 2px',
              borderRadius: '3px',
              transition: 'background-color 0.15s ease',
              backgroundColor: isActive ? `${colour}44` : 'transparent',
              color: isActive ? colour : 'inherit',
              fontWeight: isActive ? 700 : 'inherit',
            }}
          >
            {w.word}{' '}
          </span>
        );
      })}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────
interface TranscriptEditorProps {
  fullText?: string;
  segments?: TranscriptSegment[];
  loading?: boolean;
  jobId?: string;
  /** Current audio playback position in seconds (for word highlighting) */
  currentTime?: number;
}

const containerStyle: React.CSSProperties = {
  padding: '24px',
  borderRadius: '16px',
  backgroundColor: 'var(--bg-surface)',
  flex: 1,
};

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({
  fullText,
  segments,
  loading = false,
  jobId,
  currentTime,
}) => {
  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={containerStyle}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Transcript</h3>
        <p style={{ marginTop: '12px', color: 'var(--text-muted)' }}>
          Processing audio and preparing speaker-labelled transcript. Please wait…
        </p>
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  if (!fullText && (!segments || segments.length === 0)) {
    return (
      <div style={containerStyle}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Transcript Viewer</h3>
        <p style={{ marginTop: '12px', color: 'var(--text-muted)' }}>
          Upload an audio or video file to generate a transcript with speaker labels and word-level
          timing.
        </p>
      </div>
    );
  }

  // ── Subtitle download helper ───────────────────────────────────────────────
  const downloadSubtitle = (fmt: 'ass' | 'srt') => {
    if (!jobId) return;
    const url = `/api/v1/process/${jobId}/subtitle.${fmt}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${jobId}.${fmt}`;
    a.click();
  };

  // ── Rendered ───────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', flex: 1 }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '18px' }}>Living Transcript</h3>

        {/* Subtitle download buttons */}
        {jobId && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <SubtitleDownloadButton fmt="ass" onClick={() => downloadSubtitle('ass')} />
            <SubtitleDownloadButton fmt="srt" onClick={() => downloadSubtitle('srt')} />
          </div>
        )}
      </div>

      {/* Segments */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          paddingRight: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {segments && segments.length > 0 ? (
          segments.map((segment, index) => {
            const speakerColour = segment.speaker ? getSpeakerColour(segment.speaker) : '#94a3b8';
            const hasWords = segment.words && segment.words.length > 0;

            return (
              <div
                key={index}
                style={{
                  display: 'flex',
                  gap: '14px',
                  alignItems: 'flex-start',
                  padding: '12px 14px',
                  borderRadius: '12px',
                  backgroundColor: 'var(--bg-elevated, rgba(255,255,255,0.04))',
                  borderLeft: `3px solid ${speakerColour}`,
                  transition: 'border-color 0.2s ease',
                }}
              >
                {/* Timestamp */}
                <div
                  style={{
                    minWidth: '52px',
                    color: 'var(--accent)',
                    fontSize: '12px',
                    fontWeight: 700,
                    fontVariantNumeric: 'tabular-nums',
                    paddingTop: '2px',
                  }}
                >
                  {segment.start != null ? formatTimestamp(segment.start) : '0:00'}
                </div>

                {/* Content */}
                <div style={{ flex: 1 }}>
                  {/* Speaker badge */}
                  {segment.speaker && (
                    <div
                      style={{
                        display: 'inline-block',
                        marginBottom: '6px',
                        padding: '2px 10px',
                        borderRadius: '999px',
                        backgroundColor: `${speakerColour}22`,
                        color: speakerColour,
                        fontSize: '12px',
                        fontWeight: 700,
                        letterSpacing: '0.03em',
                      }}
                    >
                      {segment.speaker}
                    </div>
                  )}

                  {/* Text with optional word-level highlighting */}
                  <p
                    style={{
                      margin: 0,
                      fontSize: '14px',
                      lineHeight: 1.85,
                      color: 'var(--text-main)',
                    }}
                  >
                    {hasWords ? (
                      <WordDisplay
                        words={segment.words!}
                        currentTime={currentTime}
                        colour={speakerColour}
                      />
                    ) : (
                      segment.text
                    )}
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          /* Fallback: plain full text */
          <div
            style={{
              padding: '18px',
              borderRadius: '16px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
            }}
          >
            <pre
              style={{
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: 'inherit',
                color: 'var(--text-main)',
                lineHeight: 1.65,
              }}
            >
              {fullText}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Subtitle download button (inline — avoids a separate file import)
// ─────────────────────────────────────────────────────────────────────────────
interface SubtitleDownloadButtonProps {
  fmt: 'ass' | 'srt';
  onClick: () => void;
}

const SubtitleDownloadButton: React.FC<SubtitleDownloadButtonProps> = ({ fmt, onClick }) => (
  <button
    onClick={onClick}
    title={`Download ${fmt.toUpperCase()} subtitle file`}
    style={{
      padding: '6px 14px',
      borderRadius: '8px',
      border: '1px solid var(--border-color)',
      backgroundColor: 'transparent',
      color: 'var(--text-muted)',
      fontSize: '12px',
      fontWeight: 600,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      transition: 'all 0.15s ease',
    }}
    onMouseEnter={(e) => {
      (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)';
      (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-color)';
      (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
    }}
  >
    ⬇ .{fmt.toUpperCase()}
  </button>
);

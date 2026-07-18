import React from 'react';

// ─────────────────────────────────────────────────────────────────────────────
// Language Selector
// ─────────────────────────────────────────────────────────────────────────────
interface LanguageSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const LANGUAGE_OPTIONS = [
  { label: 'Automatic language detection', value: 'automatic' },
  { label: 'Arabic (ar)', value: 'ar' },
  { label: 'Chinese (zh)', value: 'zh' },
  { label: 'Dutch (nl)', value: 'nl' },
  { label: 'English (en)', value: 'en' },
  { label: 'French (fr)', value: 'fr' },
  { label: 'German (de)', value: 'de' },
  { label: 'Hindi (hi)', value: 'hi' },
  { label: 'Italian (it)', value: 'it' },
  { label: 'Japanese (ja)', value: 'ja' },
  { label: 'Korean (ko)', value: 'ko' },
  { label: 'Polish (pl)', value: 'pl' },
  { label: 'Portuguese (pt)', value: 'pt' },
  { label: 'Russian (ru)', value: 'ru' },
  { label: 'Spanish (es)', value: 'es' },
  { label: 'Turkish (tr)', value: 'tr' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({ value, onChange }) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
    <span style={{ color: 'var(--text-main)', fontWeight: 600, fontSize: '14px' }}>Language</span>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={selectStyle}
    >
      {LANGUAGE_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </label>
);

// ─────────────────────────────────────────────────────────────────────────────
// VAD Method Selector
// ─────────────────────────────────────────────────────────────────────────────
interface VadSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const VAD_OPTIONS = [
  { label: 'Pyannote VAD (default, best accuracy)', value: 'pyannote' },
  { label: 'Silero VAD (faster, no HF token)', value: 'silero' },
  { label: 'None (no voice activity filtering)', value: 'none' },
];

export const VadSelector: React.FC<VadSelectorProps> = ({ value, onChange }) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
    <span style={{ color: 'var(--text-main)', fontWeight: 600, fontSize: '14px' }}>
      VAD Method
    </span>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={selectStyle}
    >
      {VAD_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
      Voice Activity Detection filters non-speech audio before transcription.
    </span>
  </label>
);

// ─────────────────────────────────────────────────────────────────────────────
// Shared styles
// ─────────────────────────────────────────────────────────────────────────────
const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: '10px',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-surface, #ffffff)',
  color: 'var(--text-main)',
  fontSize: '14px',
  outline: 'none',
  appearance: 'none',
  cursor: 'pointer',
};

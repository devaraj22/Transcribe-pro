import React from 'react';

interface LanguageSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const LANGUAGE_OPTIONS = [
  { label: 'Automatic language detection', value: 'automatic' },
  { label: 'English', value: 'english' },
  { label: 'Spanish', value: 'spanish' },
  { label: 'French', value: 'french' },
  { label: 'German', value: 'german' },
  { label: 'Portuguese', value: 'portuguese' },
  { label: 'Chinese', value: 'chinese' },
  { label: 'Hindi', value: 'hindi' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({ value, onChange }) => {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
      <span style={{ color: 'var(--text-main)', fontWeight: 600, fontSize: '14px' }}>Language Mode</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={{
          width: '100%',
          padding: '12px 14px',
          borderRadius: '10px',
          border: '1px solid var(--border-color)',
          backgroundColor: '#ffffff',
          color: 'var(--text-main)',
          fontSize: '14px',
          outline: 'none',
          appearance: 'none',
        }}
      >
        {LANGUAGE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
};

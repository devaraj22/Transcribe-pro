import React, { useState, useRef } from 'react';

interface FileUploaderProps {
  acceptedTypes?: string;
  label?: string;
  helpText?: string;
  onFileSelected: (file: File) => void;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
  acceptedTypes = 'audio/mp3, audio/wav, audio/m4a, video/mp4, video/webm, video/quicktime',
  label = 'Upload audio or video file',
  helpText = 'Supports MP3, WAV, M4A, MP4, WEBM, MOV (Max 500MB)',
  onFileSelected,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    setSelectedFile(file);
    setUploadStatus('uploading');
    onFileSelected(file);
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '16px',
        width: '100%',
        minHeight: '320px',
        padding: '28px',
        border: `2px dashed ${isDragging ? 'var(--accent)' : 'var(--border-color)'}`,
        borderRadius: '18px',
        backgroundColor: 'var(--bg-main)',
        transition: 'border-color 0.2s ease, transform 0.2s ease',
        transform: isDragging ? 'translateY(-2px)' : 'translateY(0)',
      }}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept={acceptedTypes}
        style={{ display: 'none' }}
      />

      <div style={{ textAlign: 'center' }}>
        <h3 style={{ color: 'var(--text-main)', margin: '0 0 8px 0', fontSize: '20px', fontWeight: 700 }}>{label}</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0 }}>{helpText}</p>
      </div>

      <div style={{ color: isDragging ? 'var(--accent)' : 'var(--text-muted)' }}>
        <svg width="50" height="50" fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" x2="12" y1="3" y2="15"></line>
        </svg>
      </div>

      {selectedFile && (
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: 0, fontWeight: 600 }}>{selectedFile.name}</p>
        </div>
      )}

      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        style={{
          padding: '12px 26px',
          borderRadius: '10px',
          border: 'none',
          backgroundColor: 'var(--accent)',
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: 600,
          cursor: 'pointer',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        Browse files
      </button>

      {uploadStatus === 'uploading' && <p style={{ color: 'var(--accent)', fontSize: '13px' }}>Preparing upload...</p>}
    </div>
  );
};

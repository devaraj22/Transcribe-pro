import { useEffect, useRef, useState } from 'react';

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = async () => {
    setError(null);
    setRecordedBlob(null);
    setAudioUrl(null);
    setDuration(0);

    // 1. Secure-context check
    if (!window.isSecureContext) {
      setError(
        `Microphone blocked: this page is not a secure context (${window.location.protocol}//${window.location.host}). Open the site over https:// or localhost.`
      );
      return;
    }

    // 2. API existence check
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Microphone API unavailable in this browser/context.');
      return;
    }

    try {
      // Explicit constraints to prevent silent/inaudible recordings on standard mics
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mediaRecorderRef.current = recorder;

      // Add listeners BEFORE starting the recorder
      recorder.addEventListener('dataavailable', (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      });

      recorder.addEventListener('stop', () => {
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        setRecordedBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
      });

      // Start recorder with a 250ms timeslice to ensure continuous data flushing
      recorder.start(250);
      setIsRecording(true);

      timerRef.current = window.setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('getUserMedia failed:', err);
      const name = err instanceof Error ? err.name : 'UnknownError';
      const message = err instanceof Error ? err.message : String(err);
      setError(`Unable to access microphone (${name}): ${message}`);
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current) return;
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const resetRecorder = () => {
    setIsRecording(false);
    setRecordedBlob(null);
    setAudioUrl(null);
    setDuration(0);
    setError(null);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const recordedFile = recordedBlob
    ? new File([recordedBlob], `voice_capture_${Date.now()}.webm`, { type: recordedBlob.type || 'audio/webm' })
    : null;

  return {
    isRecording,
    audioUrl,
    recordedFile,
    duration,
    error,
    startRecording,
    stopRecording,
    resetRecorder,
  };
}